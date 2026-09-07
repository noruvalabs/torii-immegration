"""Account registration, sign-in, email verification, password reset, and profile (US-20)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError

from torii_api.auth.deps import CurrentUserDep, SessionDep, SettingsDep
from torii_api.auth.email import (
    build_password_reset_email_body,
    build_verification_email_body,
    send_email,
)
from torii_api.auth.security import (
    create_access_token,
    generate_token,
    hash_password,
    hash_token,
    verify_password,
)
from torii_api.db.models import CreditTransaction, User, UserRole

router = APIRouter(prefix="/v1/auth", tags=["auth"])


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
    token: str | None = None
    code: str | None = None
    redirect_uri: str | None = None
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


# ── Registration ──────────────────────────────────────────────────────────────


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterIn, session: SessionDep, settings: SettingsDep) -> TokenOut:
    """Create an applicant account, send a verification email, return a bearer token."""
    email = _normalize_email(payload.email)

    # Generate verification token (raw in email, hashed in DB)
    raw_verification_token = generate_token()
    verification_token_hash = hash_token(raw_verification_token)

    user = User(
        email=email,
        username=payload.username,
        password_hash=hash_password(payload.password),
        role=UserRole.APPLICANT,
        email_verified=False,
        email_verification_token=verification_token_hash,
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

    # Send verification email (best-effort — never blocks registration)
    verification_url = f"{settings.app_base_url}/verify-email?token={raw_verification_token}"
    send_email(
        to_email=email,
        subject="Verify your Torii email address",
        html_body=build_verification_email_body(
            username=payload.username,
            verification_url=verification_url,
            base_url=settings.app_base_url,
        ),
        settings=settings,
    )

    token = create_access_token(user_id=user.id, role=user.role, settings=settings)
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

    email = payload.email.strip().lower() if payload.email else None
    name = payload.name
    avatar_url = payload.avatar_url

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
        except Exception:
            pass

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
        except Exception:
            pass

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google authentication failed: email address not received from provider.",
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


@router.get("/verify-email", response_model=MessageOut)
async def verify_email(session: SessionDep, token: str = Query(...)) -> MessageOut:
    """Verify an email address via the token sent to the user's inbox."""
    token_hash = hash_token(token)
    user = await session.scalar(select(User).where(User.email_verification_token == token_hash))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token",
        )
    if user.email_verified:
        return MessageOut(detail="Email is already verified")

    user.email_verified = True
    user.email_verification_token = None
    await session.flush()
    return MessageOut(detail="Email verified successfully")


@router.post("/resend-verification", response_model=MessageOut)
async def resend_verification(
    payload: ForgotPasswordIn, session: SessionDep, settings: SettingsDep
) -> MessageOut:
    """Resend the email-verification link. Always returns 200 to prevent enumeration."""
    email = _normalize_email(payload.email)
    user = await session.scalar(select(User).where(User.email == email))

    if user is not None and not user.email_verified:
        raw_token = generate_token()
        user.email_verification_token = hash_token(raw_token)
        await session.flush()

        verification_url = f"{settings.app_base_url}/verify-email?token={raw_token}"
        send_email(
            to_email=email,
            subject="Verify your Torii email address",
            html_body=build_verification_email_body(
                username=user.username,
                verification_url=verification_url,
                base_url=settings.app_base_url,
            ),
            settings=settings,
        )

    return MessageOut(detail="If that email is registered and unverified, a link has been sent")


# ── Forgot / reset password ──────────────────────────────────────────────────


@router.post("/forgot-password", response_model=MessageOut)
async def forgot_password(
    payload: ForgotPasswordIn, session: SessionDep, settings: SettingsDep
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

        reset_url = f"{settings.app_base_url}/reset-password?token={raw_token}"
        send_email(
            to_email=email,
            subject="Reset your Torii password",
            html_body=build_password_reset_email_body(
                username=user.username,
                reset_url=reset_url,
                base_url=settings.app_base_url,
            ),
            settings=settings,
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
