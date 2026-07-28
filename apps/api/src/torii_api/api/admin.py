"""Admin user management — list, change roles, deactivate (US-30).

Endpoints under ``/v1/admin`` let administrators manage staff, applicant
accounts, and view all cases.  All endpoints require the ``admin`` role.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from torii_api.auth.deps import CurrentUserDep, require_roles
from torii_api.db.models import Case, CaseEscalation, User, UserRole
from torii_api.db.session import get_session

router = APIRouter(prefix="/v1/admin", tags=["admin"])

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


class AdminCaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reference: str | None = None
    status: str
    locale: str | None = None
    user_id: int
    created_at: Any = None
    updated_at: Any = None
    applicant_email: str | None = None


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/users", response_model=list[UserOut])
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


@router.get("/users/count")
async def count_users(
    session: SessionDep,
    _admin: AdminDep,
) -> dict[str, int]:
    """Return user counts by role (admin only)."""
    result = await session.execute(
        select(User.role, func.count()).group_by(User.role)
    )
    return {row[0]: row[1] for row in result.all()}


@router.get("/users/{user_id}", response_model=UserOut)
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


@router.patch("/users/{user_id}/role", response_model=UserOut)
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


@router.patch("/users/{user_id}/active", response_model=UserOut)
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


# ── Admin case list ──────────────────────────────────────────────────────────


@router.get("/cases", response_model=list[AdminCaseOut])
async def admin_list_cases(
    session: SessionDep,
    _admin: AdminDep,
    status_filter: str | None = Query(default=None, alias="status"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[Case]:
    """List all cases across all users (admin only)."""
    stmt = select(Case).order_by(Case.created_at.desc()).offset(offset).limit(limit)
    if status_filter is not None:
        stmt = stmt.where(Case.status == status_filter)
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.get("/cases/count")
async def admin_count_cases(
    session: SessionDep,
    _admin: AdminDep,
) -> dict[str, int]:
    """Return case counts by status (admin only)."""
    result = await session.execute(
        select(Case.status, func.count()).group_by(Case.status)
    )
    return {row[0]: row[1] for row in result.all()}


@router.get("/cases/{case_id}", response_model=AdminCaseOut)
async def admin_get_case(
    case_id: int,
    session: SessionDep,
    _admin: AdminDep,
) -> Case:
    """Get a specific case by ID (admin only)."""
    case = await session.get(Case, case_id)
    if case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="case not found",
        )
    return case


# ── Admin escalation list ───────────────────────────────────────────────────


class EscalationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    case_id: int
    reason: str
    message: str
    status: str
    outcome: str | None = None
    created_at: Any = None


@router.get("/escalations", response_model=list[EscalationOut])
async def admin_list_escalations(
    session: SessionDep,
    _admin: AdminDep,
    status_filter: str | None = Query(default=None, alias="status"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[CaseEscalation]:
    """List all escalations across all cases (admin only)."""
    stmt = (
        select(CaseEscalation)
        .order_by(CaseEscalation.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    if status_filter is not None:
        stmt = stmt.where(CaseEscalation.status == status_filter)
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.get("/escalations/count")
async def admin_count_escalations(
    session: SessionDep,
    _admin: AdminDep,
) -> dict[str, int]:
    """Return escalation counts by status (admin only)."""
    result = await session.execute(
        select(CaseEscalation.status, func.count()).group_by(CaseEscalation.status)
    )
    return {row[0]: row[1] for row in result.all()}


@router.patch("/escalations/{escalation_id}", response_model=EscalationOut)
async def admin_update_escalation(
    escalation_id: int,
    payload: EscalationUpdate,
    session: SessionDep,
    _admin: AdminDep,
) -> CaseEscalation:
    """Update an escalation's status and outcome (admin only)."""
    escalation = await session.get(CaseEscalation, escalation_id)
    if escalation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="escalation not found",
        )
    escalation.status = payload.status
    escalation.outcome = payload.outcome
    await session.flush()
    await session.refresh(escalation)
    return escalation


class EscalationUpdate(BaseModel):
    status: str = Field(..., pattern="^(resolved|dismissed)$")
    outcome: str | None = None
