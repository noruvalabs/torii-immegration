"""Jurisdictions — admin CRUD + public listing (US-01, US-29).

Public ``GET`` endpoints list live jurisdictions / visa categories / actions for the
applicant onboarding flow (US-01).  Admin endpoints (prefixed ``/admin``) let staff
create, update, and toggle live status on jurisdictions, visa categories, and actions
(US-29).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from torii_api.auth.deps import CurrentUserDep, require_roles
from torii_api.db.models import CaseAction, Jurisdiction, UserRole, VisaCategory
from torii_api.db.session import get_session

router = APIRouter(prefix="/v1/jurisdictions", tags=["jurisdictions"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]
AdminDep = Annotated[CurrentUserDep, Depends(require_roles(UserRole.ADMIN))]


# ── Schemas ───────────────────────────────────────────────────────────────────


class JurisdictionIn(BaseModel):
    code: str = Field(min_length=2, max_length=8, examples=["JP"])
    name: str = Field(min_length=1, max_length=128, examples=["Japan"])
    is_live: bool = False


class JurisdictionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    is_live: bool | None = None


class JurisdictionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    is_live: bool


class VisaCategoryIn(BaseModel):
    code: str = Field(min_length=1, max_length=32, examples=["work"])
    name: str = Field(min_length=1, max_length=128, examples=["Work Visa"])
    is_live: bool = False


class VisaCategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    is_live: bool | None = None


class VisaCategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    jurisdiction_id: int
    code: str
    name: str
    is_live: bool


class CaseActionIn(BaseModel):
    code: str = Field(min_length=1, max_length=32, examples=["renewal"])
    name: str = Field(min_length=1, max_length=128, examples=["Renewal"])
    is_live: bool = False


class CaseActionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    is_live: bool | None = None


class CaseActionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    jurisdiction_id: int
    code: str
    name: str
    is_live: bool


# ── Public read endpoints ─────────────────────────────────────────────────────


@router.get("", response_model=list[JurisdictionOut])
async def list_jurisdictions(
    session: SessionDep,
    live_only: bool = False,
) -> list[Jurisdiction]:
    """List jurisdictions; ``live_only=true`` returns just the ones offered to applicants."""
    stmt = select(Jurisdiction).order_by(Jurisdiction.code)
    if live_only:
        stmt = stmt.where(Jurisdiction.is_live.is_(True))
    result = await session.execute(stmt)
    return list(result.scalars().all())


# ── Admin: jurisdictions CRUD ─────────────────────────────────────────────────


@router.post("", response_model=JurisdictionOut, status_code=status.HTTP_201_CREATED)
async def create_jurisdiction(
    payload: JurisdictionIn,
    session: SessionDep,
    _admin: AdminDep,
) -> Jurisdiction:
    """Create a jurisdiction (admin only)."""
    jurisdiction = Jurisdiction(
        code=payload.code.upper(), name=payload.name, is_live=payload.is_live
    )
    session.add(jurisdiction)
    try:
        await session.flush()
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"jurisdiction '{payload.code.upper()}' already exists",
        ) from exc
    await session.refresh(jurisdiction)
    return jurisdiction


@router.patch("/{jurisdiction_id}", response_model=JurisdictionOut)
async def update_jurisdiction(
    jurisdiction_id: int,
    payload: JurisdictionUpdate,
    session: SessionDep,
    _admin: AdminDep,
) -> Jurisdiction:
    """Update a jurisdiction's name or live status (admin only)."""
    jurisdiction = await session.get(Jurisdiction, jurisdiction_id)
    if jurisdiction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="jurisdiction not found",
        )
    if payload.name is not None:
        jurisdiction.name = payload.name
    if payload.is_live is not None:
        jurisdiction.is_live = payload.is_live
    await session.flush()
    await session.refresh(jurisdiction)
    return jurisdiction


@router.delete("/{jurisdiction_id}")
async def delete_jurisdiction(
    jurisdiction_id: int,
    session: SessionDep,
    _admin: AdminDep,
):
    """Delete a jurisdiction (admin only). Fails if it has associated cases."""
    jurisdiction = await session.get(Jurisdiction, jurisdiction_id)
    if jurisdiction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="jurisdiction not found",
        )
    await session.delete(jurisdiction)
    try:
        await session.flush()
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="cannot delete jurisdiction with associated records",
        ) from exc


# ── Admin: visa categories CRUD ───────────────────────────────────────────────


@router.get(
    "/{jurisdiction_id}/visa-categories",
    response_model=list[VisaCategoryOut],
)
async def list_visa_categories(
    jurisdiction_id: int,
    session: SessionDep,
    live_only: bool = False,
) -> list[VisaCategory]:
    """List visa categories for a jurisdiction."""
    jurisdiction = await session.get(Jurisdiction, jurisdiction_id)
    if jurisdiction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="jurisdiction not found",
        )
    stmt = (
        select(VisaCategory)
        .where(VisaCategory.jurisdiction_id == jurisdiction_id)
        .order_by(VisaCategory.code)
    )
    if live_only:
        stmt = stmt.where(VisaCategory.is_live.is_(True))
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.post(
    "/{jurisdiction_id}/visa-categories",
    response_model=VisaCategoryOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_visa_category(
    jurisdiction_id: int,
    payload: VisaCategoryIn,
    session: SessionDep,
    _admin: AdminDep,
) -> VisaCategory:
    """Create a visa category under a jurisdiction (admin only)."""
    jurisdiction = await session.get(Jurisdiction, jurisdiction_id)
    if jurisdiction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="jurisdiction not found",
        )
    vc = VisaCategory(
        jurisdiction_id=jurisdiction_id,
        code=payload.code.lower(),
        name=payload.name,
        is_live=payload.is_live,
    )
    session.add(vc)
    try:
        await session.flush()
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"visa category '{payload.code}' already exists in this jurisdiction",
        ) from exc
    await session.refresh(vc)
    return vc


@router.patch(
    "/{jurisdiction_id}/visa-categories/{category_id}",
    response_model=VisaCategoryOut,
)
async def update_visa_category(
    jurisdiction_id: int,
    category_id: int,
    payload: VisaCategoryUpdate,
    session: SessionDep,
    _admin: AdminDep,
) -> VisaCategory:
    """Update a visa category's name or live status (admin only)."""
    vc = await session.get(VisaCategory, category_id)
    if vc is None or vc.jurisdiction_id != jurisdiction_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="visa category not found",
        )
    if payload.name is not None:
        vc.name = payload.name
    if payload.is_live is not None:
        vc.is_live = payload.is_live
    await session.flush()
    await session.refresh(vc)
    return vc


@router.delete(
    "/{jurisdiction_id}/visa-categories/{category_id}",
)
async def delete_visa_category(
    jurisdiction_id: int,
    category_id: int,
    session: SessionDep,
    _admin: AdminDep,
):
    """Delete a visa category (admin only)."""
    vc = await session.get(VisaCategory, category_id)
    if vc is None or vc.jurisdiction_id != jurisdiction_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="visa category not found",
        )
    await session.delete(vc)
    try:
        await session.flush()
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="cannot delete visa category with associated cases",
        ) from exc


# ── Admin: case actions CRUD ──────────────────────────────────────────────────


@router.get(
    "/{jurisdiction_id}/case-actions",
    response_model=list[CaseActionOut],
)
async def list_case_actions(
    jurisdiction_id: int,
    session: SessionDep,
    live_only: bool = False,
) -> list[CaseAction]:
    """List case actions for a jurisdiction."""
    jurisdiction = await session.get(Jurisdiction, jurisdiction_id)
    if jurisdiction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="jurisdiction not found",
        )
    stmt = (
        select(CaseAction)
        .where(CaseAction.jurisdiction_id == jurisdiction_id)
        .order_by(CaseAction.code)
    )
    if live_only:
        stmt = stmt.where(CaseAction.is_live.is_(True))
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.post(
    "/{jurisdiction_id}/case-actions",
    response_model=CaseActionOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_case_action(
    jurisdiction_id: int,
    payload: CaseActionIn,
    session: SessionDep,
    _admin: AdminDep,
) -> CaseAction:
    """Create a case action under a jurisdiction (admin only)."""
    jurisdiction = await session.get(Jurisdiction, jurisdiction_id)
    if jurisdiction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="jurisdiction not found",
        )
    ca = CaseAction(
        jurisdiction_id=jurisdiction_id,
        code=payload.code.lower(),
        name=payload.name,
        is_live=payload.is_live,
    )
    session.add(ca)
    try:
        await session.flush()
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"case action '{payload.code}' already exists in this jurisdiction",
        ) from exc
    await session.refresh(ca)
    return ca


@router.patch(
    "/{jurisdiction_id}/case-actions/{action_id}",
    response_model=CaseActionOut,
)
async def update_case_action(
    jurisdiction_id: int,
    action_id: int,
    payload: CaseActionUpdate,
    session: SessionDep,
    _admin: AdminDep,
) -> CaseAction:
    """Update a case action's name or live status (admin only)."""
    ca = await session.get(CaseAction, action_id)
    if ca is None or ca.jurisdiction_id != jurisdiction_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="case action not found",
        )
    if payload.name is not None:
        ca.name = payload.name
    if payload.is_live is not None:
        ca.is_live = payload.is_live
    await session.flush()
    await session.refresh(ca)
    return ca


@router.delete(
    "/{jurisdiction_id}/case-actions/{action_id}",
)
async def delete_case_action(
    jurisdiction_id: int,
    action_id: int,
    session: SessionDep,
    _admin: AdminDep,
):
    """Delete a case action (admin only)."""
    ca = await session.get(CaseAction, action_id)
    if ca is None or ca.jurisdiction_id != jurisdiction_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="case action not found",
        )
    await session.delete(ca)
    try:
        await session.flush()
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="cannot delete case action with associated cases",
        ) from exc
