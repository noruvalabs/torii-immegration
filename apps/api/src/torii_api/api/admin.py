"""Admin user management — list, change roles, deactivate (US-30).

Endpoints under ``/v1/admin/users`` let administrators manage staff and applicant
accounts: list users, update roles, toggle active status.  All endpoints require
the ``admin`` role.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from torii_api.auth.deps import CurrentUserDep, require_roles
from torii_api.db.models import User, UserRole
from torii_api.db.session import get_session

router = APIRouter(prefix="/v1/admin/users", tags=["admin"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]
AdminDep = Annotated[CurrentUserDep, Depends(require_roles(UserRole.ADMIN))]


# ── Schemas ───────────────────────────────────────────────────────────────────


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    username: str | None = None
    role: str
    is_active: bool
    email_verified: bool


class UserRoleUpdate(BaseModel):
    role: str = Field(
        ...,
        pattern="^(applicant|ops|employer|admin)$",
        examples=["ops"],
    )


class UserActiveUpdate(BaseModel):
    is_active: bool


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("", response_model=list[UserOut])
async def list_users(
    session: SessionDep,
    _admin: AdminDep,
    role: str | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[User]:
    """List all users (admin only). Optionally filter by role."""
    stmt = select(User).order_by(User.id).offset(offset).limit(limit)
    if role is not None:
        stmt = stmt.where(User.role == role)
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.get("/count")
async def count_users(
    session: SessionDep,
    _admin: AdminDep,
) -> dict[str, int]:
    """Return user counts by role (admin only)."""
    result = await session.execute(
        select(User.role, func.count()).group_by(User.role)
    )
    return {row[0]: row[1] for row in result.all()}


@router.get("/{user_id}", response_model=UserOut)
async def get_user(
    user_id: int,
    session: SessionDep,
    _admin: AdminDep,
) -> User:
    """Get a specific user by ID (admin only)."""
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="user not found",
        )
    return user


@router.patch("/{user_id}/role", response_model=UserOut)
async def update_user_role(
    user_id: int,
    payload: UserRoleUpdate,
    session: SessionDep,
    _admin: AdminDep,
) -> User:
    """Change a user's role (admin only). Cannot change own role."""
    if user_id == _admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="cannot change your own role",
        )
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="user not found",
        )
    user.role = payload.role
    await session.flush()
    await session.refresh(user)
    return user


@router.patch("/{user_id}/active", response_model=UserOut)
async def toggle_user_active(
    user_id: int,
    payload: UserActiveUpdate,
    session: SessionDep,
    _admin: AdminDep,
) -> User:
    """Activate or deactivate a user (admin only). Cannot deactivate self."""
    if user_id == _admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="cannot deactivate yourself",
        )
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="user not found",
        )
    user.is_active = payload.is_active
    await session.flush()
    await session.refresh(user)
    return user
