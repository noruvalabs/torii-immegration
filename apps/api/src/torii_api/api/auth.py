"""Account registration, sign-in, email verification, password reset, and profile (US-20)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlparse

import structlog
from fastapi import APIRouter, HTTPException, Query, Request, UploadFile, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from torii_api.auth.deps import CurrentUserDep, SessionDep, SettingsDep
from torii_api.auth.email import (
    build_password_reset_email_body,
    build_password_reset_email_text,
    build_verification_email_body,
    build_verification_email_text,
)
from torii_api.auth.security import (
    create_access_token,
    generate_token,
    hash_password,
    hash_token,
    verify_password,
)
from torii_api.config import Settings
from torii_api.db.models import CreditTransaction, OutboxEvent, User, UserRole

router = APIRouter(prefix="/v1/auth", tags=["auth"])

log = structlog.get_logger()


def _enqueue_email(
    session: AsyncSession,
    *,
    to_email: str,
    subject: str,
    html_body: str,
    text_body: str | None = None,
    raw_token: str | None = None,
) -> None:
    """Queue an email into the transactional outbox to be dispatched asynchronously."""
    payload: dict[str, Any] = {
        "to_email": to_email,
        "subject": subject,
        "html_body": html_body,
        "text_body": text_body,
    }
    if raw_token is not None:
        payload["token"] = raw_token
    session.add(OutboxEvent(topic="email.send", payload=payload))


# ── Request / response schemas ────────────────────────────────────────────────


class RegisterIn(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=128)
    username: str | None = Field(default=None, min_length=3, max_length=64)


class LoginIn(BaseModel):
    email_or_username: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=128)


class AuthConfigOut(BaseModel):
    google_client_id: str | None = None
    google_auth_enabled: bool = False


class GoogleAuthIn(BaseModel):
    """Input for POST /v1/auth/google.

    Exactly one credential is required: `code` (authorization code flow, what the web app
    sends) or `token` (a Google access/ID token). Everything else is advisory.
    """

    token: str | None = None
    code: str | None = None
    redirect_uri: str | None = None
    # IGNORED for identity, deliberately. The endpoint derives the account's email only from
    # a Google-verified response; accepting it here once allowed anyone to sign in as any
    # user by posting their address. Kept on the schema so old clients that still send it get
    # a normal response rather than a validation error -- the value is simply never read.
    email: str | None = None
    name: str | None = None
    avatar_url: str | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    username: str | None = None
    role: str
    is_active: bool
    email_verified: bool
    # Profile fields
    full_name: str | None = None
    nationality: str | None = None
    passport_number: str | None = None
    passport_expiry: str | None = None
    date_of_birth: str | None = None
    current_country: str | None = None
    avatar_url: str | None = None
    profile_complete: bool = False


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class ForgotPasswordIn(BaseModel):
    email: str = Field(min_length=3, max_length=320)


class ResetPasswordIn(BaseModel):
    token: str = Field(min_length=1)
    password: str = Field(min_length=8, max_length=128)


class MessageOut(BaseModel):
    detail: str


class VerifyEmailOut(BaseModel):
    detail: str
    access_token: str | None = None
    user: UserOut | None = None


class ChangePasswordIn(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class ProfileUpdateIn(BaseModel):
    full_name: str | None = Field(default=None, max_length=200)
    nationality: str | None = Field(default=None, max_length=100)
    passport_number: str | None = Field(default=None, max_length=32)
    passport_expiry: str | None = Field(default=None, max_length=32)
    date_of_birth: str | None = Field(default=None, max_length=32)
    current_country: str | None = Field(default=None, max_length=100)

    @field_validator("*", mode="before")
    @classmethod
    def empty_str_to_none(cls, v: object) -> object:
        if isinstance(v, str) and not v.strip():
            return None
        return v


# ── Helpers ───────────────────────────────────────────────────────────────────


def _normalize_email(email: str) -> str:
    return email.strip().lower()


async def _find_user_by_email_or_username(session: SessionDep, identifier: str) -> User | None:
    """Look up a user by email (normalized) or username (case-insensitive)."""
    identifier = identifier.strip()
    email = _normalize_email(identifier)
    return await session.scalar(
        select(User).where(or_(User.email == email, User.username == identifier))
    )


# ── Helpers ───────────────────────────────────────────────────────────────────


def _resolve_app_base_url(request: Request, settings: Settings) -> str:
    """Resolve public frontend base URL from incoming request headers or fallback settings."""
    origin = request.headers.get("origin")
    if origin and origin.startswith(("http://", "https://")):
        return origin.rstrip("/")

    referer = request.headers.get("referer")
    if referer and referer.startswith(("http://", "https://")):
        p = urlparse(referer)
        return f"{p.scheme}://{p.netloc}".rstrip("/")

    host = request.headers.get("x-forwarded-host") or request.headers.get("host")
    if host:
        proto = request.headers.get("x-forwarded-proto") or (
            "https" if "noruvalabs" in host or "torii" in host else "http"
        )
        return f"{proto}://{host}".rstrip("/")

    return settings.app_base_url.rstrip("/")


# ── Registration ──────────────────────────────────────────────────────────────


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterIn,
    session: SessionDep,
    settings: SettingsDep,
    request: Request,
) -> TokenOut:
    """Create an applicant account or re-send verification for an unverified account."""
    email = _normalize_email(payload.email)

    # Check for an existing account
    existing_user = await session.scalar(select(User).where(User.email == email))
    if existing_user is not None:
        if existing_user.email_verified:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists. Please sign in or reset your password.",
            )

        # Existing account is unverified (user re-signed up because token expired or lost)
        # Update credentials with new password, refresh verification token and expiration
        existing_user.password_hash = hash_password(payload.password)
        if payload.username:
            conflict_username = await session.scalar(
                select(User).where(User.username == payload.username, User.id != existing_user.id)
            )
            if conflict_username is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="This username is already taken",
                )
            existing_user.username = payload.username

        raw_verification_token = generate_token()
        existing_user.email_verification_token = hash_token(raw_verification_token)
        existing_user.email_verification_expires = datetime.now(UTC) + timedelta(
            minutes=settings.email_verification_token_expire_minutes
        )
        await session.flush()
        await session.refresh(existing_user)

        base_url = _resolve_app_base_url(request, settings)
        verification_url = f"{base_url}/verify-email?token={raw_verification_token}"
        _enqueue_email(
            session,
            to_email=email,
            subject="Verify your Torii email address",
            html_body=build_verification_email_body(
                username=existing_user.username,
                verification_url=verification_url,
                base_url=base_url,
            ),
            text_body=build_verification_email_text(
                username=existing_user.username,
                verification_url=verification_url,
            ),
            raw_token=raw_verification_token,
        )

        token = (
            ""
            if settings.require_email_verification
            else create_access_token(
                user_id=existing_user.id, role=existing_user.role, settings=settings
            )
        )
        return TokenOut(access_token=token, user=UserOut.model_validate(existing_user))

    # Check username uniqueness if provided
    if payload.username:
        u_conflict = await session.scalar(select(User).where(User.username == payload.username))
        if u_conflict is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This username is already taken",
            )

    # Generate verification token and expiration
    raw_verification_token = generate_token()
    verification_token_hash = hash_token(raw_verification_token)
    verification_expires = datetime.now(UTC) + timedelta(
        minutes=settings.email_verification_token_expire_minutes
    )

    user = User(
        email=email,
        username=payload.username,
        password_hash=hash_password(payload.password),
        role=UserRole.APPLICANT,
        email_verified=False,
        email_verification_token=verification_token_hash,
        email_verification_expires=verification_expires,
    )
    session.add(user)
    try:
        await session.flush()
    except IntegrityError as exc:
        detail = "An account with this email already exists"
        if "users_username" in str(exc):
            detail = "This username is already taken"
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
        ) from exc
    await session.refresh(user)

    # Record welcome credits transaction
    welcome_tx = CreditTransaction(
        user_id=user.id,
        amount=user.credit_balance,
        balance_after=user.credit_balance,
        feature="welcome_bonus",
        description="Welcome bonus: 3 free credits on signup",
    )
    session.add(welcome_tx)
    await session.flush()

    # Queue verification email in outbox (transactional, non-blocking)
    base_url = _resolve_app_base_url(request, settings)
    verification_url = f"{base_url}/verify-email?token={raw_verification_token}"
    _enqueue_email(
        session,
        to_email=email,
        subject="Verify your Torii email address",
        html_body=build_verification_email_body(
            username=payload.username,
            verification_url=verification_url,
            base_url=base_url,
        ),
        text_body=build_verification_email_text(
            username=payload.username,
            verification_url=verification_url,
        ),
        raw_token=raw_verification_token,
    )

    token = (
        ""
        if settings.require_email_verification
        else create_access_token(user_id=user.id, role=user.role, settings=settings)
    )
    return TokenOut(access_token=token, user=UserOut.model_validate(user))


# ── Login ─────────────────────────────────────────────────────────────────────


@router.post("/login", response_model=TokenOut)
async def login(payload: LoginIn, session: SessionDep, settings: SettingsDep) -> TokenOut:
    """Sign in with email/username and password; returns a bearer token."""
    user = await _find_user_by_email_or_username(session, payload.email_or_username)
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )
    if (
        settings.require_email_verification
        and not user.email_verified
        and user.role == UserRole.APPLICANT
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email address before signing in. Check your inbox for the verification link.",
        )
    token = create_access_token(user_id=user.id, role=user.role, settings=settings)
    return TokenOut(access_token=token, user=UserOut.model_validate(user))


@router.get("/config", response_model=AuthConfigOut)
async def get_auth_config(settings: SettingsDep) -> AuthConfigOut:
    """Return public authentication configuration."""
    client_id = settings.google_client_id.strip() if settings.google_client_id else ""
    return AuthConfigOut(
        google_client_id=client_id or None,
        google_auth_enabled=bool(client_id),
    )


@router.post("/google", response_model=TokenOut)
async def google_login(
    payload: GoogleAuthIn,
    session: SessionDep,
    settings: SettingsDep,
) -> TokenOut:
    """Sign in or register using Google Social Login."""
    import secrets

    import httpx

    # SECURITY: `email` is the identity this endpoint authenticates, so it may ONLY ever come
    # from a response Google itself signed. It starts as None and is assigned nowhere except
    # inside the verified branches below.
    #
    # It used to be seeded from `payload.email` -- the client's own JSON body. Because step 2
    # is guarded by `if not email`, supplying an email skipped every verification path, and
    # the request fell straight through to the user lookup and was issued a valid JWT. In
    # other words:
    #
    #   curl -X POST .../v1/auth/google -d '{"email":"admin@example.com"}'
    #
    # returned a working admin session to anyone who asked, with no Google token, no
    # authorization code, and no password. `name` and `avatar_url` stay client-supplied
    # because they are display-only and are overwritten by Google's values when present, but
    # identity never is.
    email: str | None = None
    name = payload.name
    avatar_url = payload.avatar_url

    # Why this endpoint tracks a failure reason at all: every Google call below can fail for
    # causes that need completely different responses from whoever is debugging -- the host
    # having no outbound network, the client secret being wrong, Google rejecting an expired
    # token, or the account genuinely exposing no email. All of them used to be swallowed by
    # `except Exception: pass` and reported as the single message "email address not received
    # from provider", which describes only the last of those.
    #
    # That masking cost real time: on 2026-09-13 container egress was down (ip_forward=0) and
    # the resulting ConnectError surfaced to users as a Google account problem, with nothing
    # in the logs. Never let these paths fail silently again.
    failure_reason: str | None = None

    if not payload.code and not payload.token:
        failure_reason = "no_credential"
        log.warning("auth.google.no_credential_supplied")

    if payload.code and not (settings.google_client_id and settings.google_client_secret):
        failure_reason = "server_not_configured"
        log.error(
            "auth.google.not_configured",
            has_client_id=bool(settings.google_client_id),
            has_client_secret=bool(settings.google_client_secret),
        )

    # 1. If an authorization code was provided, exchange it for tokens with Google
    if payload.code and settings.google_client_id and settings.google_client_secret:
        try:
            async with httpx.AsyncClient(timeout=10.0) as http_client:
                token_resp = await http_client.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "code": payload.code,
                        "client_id": settings.google_client_id,
                        "client_secret": settings.google_client_secret,
                        "redirect_uri": payload.redirect_uri
                        or f"{settings.app_base_url}/callback/google",
                        "grant_type": "authorization_code",
                    },
                )
                if token_resp.status_code == 200:
                    token_data = token_resp.json()
                    access_tok = token_data.get("access_token")
                    id_tok = token_data.get("id_token")
                    if access_tok:
                        u_resp = await http_client.get(
                            "https://www.googleapis.com/oauth2/v3/userinfo",
                            headers={"Authorization": f"Bearer {access_tok}"},
                        )
                        if u_resp.status_code == 200:
                            g_data = u_resp.json()
                            email = (g_data.get("email") or email or "").strip().lower() or None
                            name = g_data.get("name") or name
                            avatar_url = g_data.get("picture") or avatar_url
                    elif id_tok:
                        t_resp = await http_client.get(
                            f"https://oauth2.googleapis.com/tokeninfo?id_token={id_tok}"
                        )
                        if t_resp.status_code == 200:
                            g_data = t_resp.json()
                            email = (g_data.get("email") or email or "").strip().lower() or None
                            name = g_data.get("name") or name
                            avatar_url = g_data.get("picture") or avatar_url
                else:
                    # Google rejected the exchange. Its JSON error body is the single most
                    # useful thing here -- `redirect_uri_mismatch` and `invalid_client` both
                    # land on this branch and mean very different fixes.
                    failure_reason = "code_exchange_rejected"
                    log.error(
                        "auth.google.code_exchange_failed",
                        status_code=token_resp.status_code,
                        # Never the code or the secret; the error body carries neither.
                        google_error=token_resp.text[:300],
                    )
        except Exception as exc:
            failure_reason = "google_unreachable"
            log.exception(
                "auth.google.code_exchange_error",
                error_type=type(exc).__name__,
                error=str(exc),
            )

    # 2. If a direct access_token or id_token was provided, verify with Google
    if not email and payload.token:
        try:
            async with httpx.AsyncClient(timeout=10.0) as http_client:
                res = await http_client.get(
                    "https://www.googleapis.com/oauth2/v3/userinfo",
                    headers={"Authorization": f"Bearer {payload.token}"},
                )
                if res.status_code == 200:
                    g_data = res.json()
                    email = (g_data.get("email") or email or "").strip().lower() or None
                    name = g_data.get("name") or name
                    avatar_url = g_data.get("picture") or avatar_url
                else:
                    res_id = await http_client.get(
                        f"https://oauth2.googleapis.com/tokeninfo?id_token={payload.token}"
                    )
                    if res_id.status_code == 200:
                        g_data = res_id.json()
                        email = (g_data.get("email") or email or "").strip().lower() or None
                        name = g_data.get("name") or name
                        avatar_url = g_data.get("picture") or avatar_url
                    else:
                        failure_reason = "token_rejected"
                        log.error(
                            "auth.google.token_verification_failed",
                            userinfo_status=res.status_code,
                            tokeninfo_status=res_id.status_code,
                        )
        except Exception as exc:
            failure_reason = "google_unreachable"
            log.exception(
                "auth.google.token_verification_error",
                error_type=type(exc).__name__,
                error=str(exc),
            )

    if not email:
        # The message tells the user what to do; the reason tells us what broke. Both matter:
        # "try again" is useless advice when the real fault is server-side.
        detail = {
            "server_not_configured": (
                "Google sign-in is not configured on the server. Please contact support or "
                "sign in with your email and password."
            ),
            "google_unreachable": (
                "Could not reach Google to verify your sign-in. This is a problem on our "
                "side, not with your account. Please try again shortly."
            ),
            "code_exchange_rejected": (
                "Google rejected this sign-in attempt. Please try signing in again."
            ),
            "token_rejected": (
                "Your Google sign-in has expired or is no longer valid. Please try again."
            ),
            "no_credential": (
                "No Google credential was supplied. Please start the sign-in from the Google "
                "button."
            ),
        }.get(
            failure_reason or "",
            "Google authentication failed: no email address was returned for this account.",
        )
        log.warning("auth.google.login_failed", reason=failure_reason or "no_email_in_response")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY
            if failure_reason in {"google_unreachable", "server_not_configured"}
            else status.HTTP_400_BAD_REQUEST,
            detail=detail,
        )

    user = await _find_user_by_email_or_username(session, email)
    if user is None:
        base_username = email.split("@")[0]
        username = base_username
        suffix = 1
        while await _find_user_by_email_or_username(session, username):
            username = f"{base_username}{suffix}"
            suffix += 1

        random_pw = secrets.token_urlsafe(24)
        user = User(
            email=email,
            username=username,
            password_hash=hash_password(random_pw),
            role="applicant",
            is_active=True,
            email_verified=True,
            full_name=name or base_username.capitalize(),
            avatar_url=avatar_url,
        )
        session.add(user)
        await session.flush()
        await session.refresh(user)

        # Record welcome credits transaction
        welcome_tx = CreditTransaction(
            user_id=user.id,
            amount=user.credit_balance,
            balance_after=user.credit_balance,
            feature="welcome_bonus",
            description="Welcome bonus: 3 free credits on signup",
        )
        session.add(welcome_tx)
        await session.flush()
    else:
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")
        user.email_verified = True
        if avatar_url and not user.avatar_url:
            user.avatar_url = avatar_url
        if name and not user.full_name:
            user.full_name = name
        await session.flush()

    token = create_access_token(user_id=user.id, role=user.role, settings=settings)
    return TokenOut(access_token=token, user=UserOut.model_validate(user))


# ── Current user profile ──────────────────────────────────────────────────────


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUserDep) -> User:
    """Return the signed-in user's profile."""
    return user


@router.get("/profile", response_model=UserOut)
async def get_profile(user: CurrentUserDep) -> User:
    """Return the signed-in user's full profile including saved fields."""
    return user


@router.put("/profile", response_model=UserOut)
async def update_profile(
    payload: ProfileUpdateIn, user: CurrentUserDep, session: SessionDep
) -> User:
    """Update the signed-in user's profile fields."""
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if isinstance(value, str):
            value = value.strip() or None
        setattr(user, key, value)

    # Auto-mark profile as complete when required fields are filled
    required_fields = ["full_name", "nationality", "passport_number", "current_country"]
    user.profile_complete = all(bool(getattr(user, f, None)) for f in required_fields)

    await session.flush()
    return user


@router.post("/avatar", response_model=UserOut)
async def upload_avatar(
    file: UploadFile,
    user: CurrentUserDep,
    session: SessionDep,
) -> User:
    """Upload a profile avatar image."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image",
        )

    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image must be less than 5MB",
        )

    # TODO: In production, upload to S3/CDN and get URL
    # For now, store as data URL
    import base64

    b64 = base64.b64encode(content).decode("utf-8")
    data_url = f"data:{file.content_type};base64,{b64}"
    user.avatar_url = data_url

    await session.flush()
    return user


# ── Email verification ────────────────────────────────────────────────────────


@router.get("/verify-email", response_model=VerifyEmailOut)
async def verify_email(
    session: SessionDep,
    settings: SettingsDep,
    token: str = Query(...),
) -> VerifyEmailOut:
    """Verify an email address via the token sent to the user's inbox."""
    token_hash = hash_token(token)
    user = await session.scalar(select(User).where(User.email_verification_token == token_hash))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification link. If you already verified, please sign in. Otherwise, request a new link.",
        )

    if (
        user.email_verification_expires is not None
        and user.email_verification_expires < datetime.now(UTC)
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification link has expired. Please request a new verification email.",
        )

    user.email_verified = True
    user.email_verification_token = None
    user.email_verification_expires = None
    await session.flush()

    token = create_access_token(user_id=user.id, role=user.role, settings=settings)
    return VerifyEmailOut(
        detail="Email verified successfully",
        access_token=token,
        user=UserOut.model_validate(user),
    )


@router.post("/resend-verification", response_model=MessageOut)
async def resend_verification(
    payload: ForgotPasswordIn,
    session: SessionDep,
    settings: SettingsDep,
    request: Request,
) -> MessageOut:
    """Resend the email-verification link. Always returns 200 to prevent enumeration."""
    email = _normalize_email(payload.email)
    user = await session.scalar(select(User).where(User.email == email))

    if user is not None and not user.email_verified:
        raw_token = generate_token()
        user.email_verification_token = hash_token(raw_token)
        user.email_verification_expires = datetime.now(UTC) + timedelta(
            minutes=settings.email_verification_token_expire_minutes
        )
        await session.flush()

        base_url = _resolve_app_base_url(request, settings)
        verification_url = f"{base_url}/verify-email?token={raw_token}"
        _enqueue_email(
            session,
            to_email=email,
            subject="Verify your Torii email address",
            html_body=build_verification_email_body(
                username=user.username,
                verification_url=verification_url,
                base_url=base_url,
            ),
            text_body=build_verification_email_text(
                username=user.username,
                verification_url=verification_url,
            ),
            raw_token=raw_token,
        )

    return MessageOut(
        detail="If that email is registered and unverified, a verification link has been sent"
    )


# ── Forgot / reset password ──────────────────────────────────────────────────


@router.post("/forgot-password", response_model=MessageOut)
async def forgot_password(
    payload: ForgotPasswordIn,
    session: SessionDep,
    settings: SettingsDep,
    request: Request,
) -> MessageOut:
    """Send a password-reset email. Always returns 200 to prevent enumeration."""
    email = _normalize_email(payload.email)
    user = await session.scalar(select(User).where(User.email == email))

    if user is not None and user.is_active:
        raw_token = generate_token()
        user.password_reset_token = hash_token(raw_token)
        user.password_reset_expires = datetime.now(UTC) + timedelta(
            minutes=settings.password_reset_token_expire_minutes
        )
        await session.flush()

        base_url = _resolve_app_base_url(request, settings)
        reset_url = f"{base_url}/reset-password?token={raw_token}"
        _enqueue_email(
            session,
            to_email=email,
            subject="Reset your Torii password",
            html_body=build_password_reset_email_body(
                username=user.username,
                reset_url=reset_url,
                base_url=base_url,
            ),
            text_body=build_password_reset_email_text(
                username=user.username,
                reset_url=reset_url,
            ),
            raw_token=raw_token,
        )

    return MessageOut(detail="If that email is registered, a password-reset link has been sent")


@router.post("/reset-password", response_model=MessageOut)
async def reset_password(
    payload: ResetPasswordIn, session: SessionDep, settings: SettingsDep
) -> MessageOut:
    """Reset a password using the token from the email."""
    token_hash = hash_token(payload.token)
    user = await session.scalar(select(User).where(User.password_reset_token == token_hash))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    # Check expiry
    if user.password_reset_expires is None or user.password_reset_expires < datetime.now(UTC):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    user.password_hash = hash_password(payload.password)
    user.password_reset_token = None
    user.password_reset_expires = None
    await session.flush()
    return MessageOut(detail="Password has been reset successfully")


# ── Password change (authenticated) ──────────────────────────────────────────


@router.post("/change-password", response_model=MessageOut)
async def change_password(
    payload: ChangePasswordIn,
    user: CurrentUserDep,
    session: SessionDep,
) -> MessageOut:
    """Change the current signed-in user's password."""
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    if payload.current_password == payload.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from your current password",
        )
    user.password_hash = hash_password(payload.new_password)
    await session.flush()
    return MessageOut(detail="Password changed successfully")
