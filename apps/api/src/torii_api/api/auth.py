"""Account registration, sign-in, and the current-user profile (US-20)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from torii_api.auth.deps import CurrentUserDep, SessionDep, SettingsDep
from torii_api.auth.security import create_access_token, hash_password, verify_password
from torii_api.db.models import User, UserRole

router = APIRouter(prefix="/v1/auth", tags=["auth"])


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    role: str
    is_active: bool


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


def _normalize_email(email: str) -> str:
    return email.strip().lower()


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterIn, session: SessionDep, settings: SettingsDep) -> TokenOut:
    """Create an applicant account and return a bearer token (US-20.1)."""
    email = _normalize_email(payload.email)
    user = User(
        email=email,
        password_hash=hash_password(payload.password),
        role=UserRole.APPLICANT,
    )
    session.add(user)
    try:
        await session.flush()
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        ) from exc
    await session.refresh(user)
    token = create_access_token(user_id=user.id, role=user.role, settings=settings)
    return TokenOut(access_token=token, user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenOut)
async def login(payload: LoginIn, session: SessionDep, settings: SettingsDep) -> TokenOut:
    """Sign in with email and password; returns a bearer token (US-20.1)."""
    email = _normalize_email(payload.email)
    user = await session.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )
    token = create_access_token(user_id=user.id, role=user.role, settings=settings)
    return TokenOut(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUserDep) -> User:
    """Return the signed-in user's profile (US-20.2)."""
    return user
