"""Account registration, sign-in, email verification, password reset, and profile (US-20)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
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
from torii_api.db.models import User, UserRole

router = APIRouter(prefix="/v1/auth", tags=["auth"])


# ── Request / response schemas ────────────────────────────────────────────────


class RegisterIn(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=128)
    username: str | None = Field(default=None, min_length=3, max_length=64)


class LoginIn(BaseModel):
    email_or_username: str = Field(min_length=1, max_length=320)
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    username: str | None = None
    role: str
    is_active: bool
    email_verified: bool


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


# ── Helpers ───────────────────────────────────────────────────────────────────


def _normalize_email(email: str) -> str:
    return email.strip().lower()


async def _find_user_by_email_or_username(
    session: SessionDep, identifier: str
) -> User | None:
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


# ── Current user profile ──────────────────────────────────────────────────────


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUserDep) -> User:
    """Return the signed-in user's profile."""
    return user


# ── Email verification ────────────────────────────────────────────────────────


@router.get("/verify-email", response_model=MessageOut)
async def verify_email(session: SessionDep, token: str = Query(...)) -> MessageOut:
    """Verify an email address via the token sent to the user's inbox."""
    token_hash = hash_token(token)
    user = await session.scalar(
        select(User).where(User.email_verification_token == token_hash)
    )
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

    return MessageOut(
        detail="If that email is registered, a password-reset link has been sent"
    )


@router.post("/reset-password", response_model=MessageOut)
async def reset_password(
    payload: ResetPasswordIn, session: SessionDep, settings: SettingsDep
) -> MessageOut:
    """Reset a password using the token from the email."""
    token_hash = hash_token(payload.token)
    user = await session.scalar(
        select(User).where(User.password_reset_token == token_hash)
    )
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
