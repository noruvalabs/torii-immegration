"""Cases — the core resource applicants and staff interact with.

US-01: Scoping a case to jurisdiction + visa category + action.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from torii_api.auth.deps import CurrentUserDep
from torii_api.db.models import Case, CaseAction, Jurisdiction, VisaCategory
from torii_api.db.session import get_session

router = APIRouter(prefix="/v1/cases", tags=["cases"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


# ── Request / response schemas ────────────────────────────────────────────────


class VisaCategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    jurisdiction_id: int
    code: str
    name: str
    is_live: bool


class CaseActionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    jurisdiction_id: int
    code: str
    name: str
    is_live: bool


class ScopeIn(BaseModel):
    jurisdiction_code: str = Field(min_length=2, max_length=8, examples=["JP"])
    visa_category_code: str = Field(min_length=1, max_length=32, examples=["work"])
    action_code: str = Field(min_length=1, max_length=32, examples=["renewal"])


class CaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reference: str
    jurisdiction_id: int
    visa_category_id: int | None = None
    case_action_id: int | None = None
    user_id: int | None = None
    status: str
    applicant_email: str | None = None


# ── Visa categories & actions ─────────────────────────────────────────────────


@router.get(
    "/visa-categories",
    response_model=list[VisaCategoryOut],
)
async def list_visa_categories(
    session: SessionDep,
    jurisdiction_code: str = Query(..., min_length=2, max_length=8),
    live_only: bool = False,
) -> list[VisaCategory]:
    """List visa categories for a jurisdiction. ``live_only=true`` returns only live ones."""
    jurisdiction = await session.scalar(
        select(Jurisdiction).where(Jurisdiction.code == jurisdiction_code.upper())
    )
    if jurisdiction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"jurisdiction '{jurisdiction_code}' not found",
        )
    stmt = (
        select(VisaCategory)
        .where(VisaCategory.jurisdiction_id == jurisdiction.id)
        .order_by(VisaCategory.code)
    )
    if live_only:
        stmt = stmt.where(VisaCategory.is_live.is_(True))
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.get(
    "/case-actions",
    response_model=list[CaseActionOut],
)
async def list_case_actions(
    session: SessionDep,
    jurisdiction_code: str = Query(..., min_length=2, max_length=8),
    live_only: bool = False,
) -> list[CaseAction]:
    """List case actions for a jurisdiction. ``live_only=true`` returns only live ones."""
    jurisdiction = await session.scalar(
        select(Jurisdiction).where(Jurisdiction.code == jurisdiction_code.upper())
    )
    if jurisdiction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"jurisdiction '{jurisdiction_code}' not found",
        )
    stmt = (
        select(CaseAction)
        .where(CaseAction.jurisdiction_id == jurisdiction.id)
        .order_by(CaseAction.code)
    )
    if live_only:
        stmt = stmt.where(CaseAction.is_live.is_(True))
    result = await session.execute(stmt)
    return list(result.scalars().all())


# ── Scope a case ──────────────────────────────────────────────────────────────


@router.post("/scope", response_model=CaseOut, status_code=status.HTTP_201_CREATED)
async def scope_case(
    payload: ScopeIn,
    session: SessionDep,
    user: CurrentUserDep,
) -> Case:
    """Create a new case scoped to a jurisdiction + visa category + action (US-01).

    Only live combinations are accepted. Returns the newly created case in ``draft`` status.
    """
    # Resolve jurisdiction
    jurisdiction = await session.scalar(
        select(Jurisdiction).where(Jurisdiction.code == payload.jurisdiction_code.upper())
    )
    if jurisdiction is None or not jurisdiction.is_live:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"jurisdiction '{payload.jurisdiction_code}' is not available",
        )

    # Resolve visa category
    visa_category = await session.scalar(
        select(VisaCategory).where(
            VisaCategory.jurisdiction_id == jurisdiction.id,
            VisaCategory.code == payload.visa_category_code.lower(),
        )
    )
    if visa_category is None or not visa_category.is_live:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"visa category '{payload.visa_category_code}'"
                f" is not available in {jurisdiction.code}"
            ),
        )

    # Resolve action
    case_action = await session.scalar(
        select(CaseAction).where(
            CaseAction.jurisdiction_id == jurisdiction.id,
            CaseAction.code == payload.action_code.lower(),
        )
    )
    if case_action is None or not case_action.is_live:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"action '{payload.action_code}' is not available in {jurisdiction.code}",
        )

    # Generate reference: JP-2026-000123
    from datetime import UTC, datetime

    year = datetime.now(UTC).year
    last_case = await session.scalar(
        select(Case)
        .where(Case.jurisdiction_id == jurisdiction.id)
        .order_by(Case.id.desc())
        .limit(1)
    )
    seq = 1
    if last_case and last_case.reference:
        parts = last_case.reference.split("-")
        if len(parts) == 3:
            try:
                seq = int(parts[2]) + 1
            except ValueError:
                pass
    reference = f"{jurisdiction.code}-{year}-{seq:06d}"

    case = Case(
        reference=reference,
        jurisdiction_id=jurisdiction.id,
        visa_category_id=visa_category.id,
        case_action_id=case_action.id,
        user_id=user.id,
        status="draft",
    )
    session.add(case)
    try:
        await session.flush()
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="case reference conflict — please retry",
        ) from exc
    await session.refresh(case)
    return case


# ── List my cases ─────────────────────────────────────────────────────────────


@router.get("", response_model=list[CaseOut])
async def list_cases(
    session: SessionDep,
    user: CurrentUserDep,
) -> list[Case]:
    """List the current user's cases."""
    result = await session.execute(
        select(Case).where(Case.user_id == user.id).order_by(Case.created_at.desc())
    )
    return list(result.scalars().all())
