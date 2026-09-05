"""Jurisdictions — admin CRUD + public listing (US-01, US-29).

Public ``GET`` endpoints list jurisdictions / visa categories / actions for the applicant
onboarding flow (US-01). Admin endpoints let staff create, update, and switch jurisdictions,
visa categories, and actions on and off (US-29).

Three flags decide whether a route reaches an applicant, and they are not the same question:

* ``is_enabled`` — the admin's switch. Nothing seeds it, so switching a country or a route
  off stays off across a deploy. This is what the admin panel toggles.
* ``is_live`` — a seeded content pack backs this scope. ``seed()`` rewrites it from
  ``docs/jurisdictions`` on every run, which is exactly why it is not the admin's switch.
* ``research_enabled`` — a scope with no pack may still be offered, with requirements
  produced on demand by the live-research pipeline (NF-2 gated).

An applicant sees a route when ``is_enabled`` and (``is_live`` or ``research_enabled``).
``POST /{id}/discover`` fills the list in the first place: it reads the destination's own
immigration pages and writes what it finds as candidates, switched off.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from torii_api.auth.deps import CurrentUserDep, require_roles
from torii_api.db.models import (
    Case,
    CaseAction,
    DocumentRequirementSet,
    EligibilityRuleSet,
    FormTemplate,
    IntakeDefinition,
    Jurisdiction,
    PackOverride,
    ScopeResearch,
    UserRole,
    VisaCategory,
)
from torii_api.db.session import get_session
from torii_api.services.scope_discovery import (
    SOURCE_MANUAL,
    ScopeDiscoveryUnavailable,
    apply_discovery,
    discover_scopes,
)

router = APIRouter(prefix="/v1/jurisdictions", tags=["jurisdictions"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]
AdminDep = Annotated[CurrentUserDep, Depends(require_roles(UserRole.ADMIN))]

# The routes a brand-new country starts with, switched off. Generic on purpose: they are a
# placeholder until discovery reads the country's real ones, never a claim about it.
STARTER_CATEGORIES: tuple[tuple[str, str], ...] = (
    ("work", "Work / Employment"),
    ("student", "Student"),
    ("tourist", "Tourist / Visitor"),
)
STARTER_ACTIONS: tuple[tuple[str, str], ...] = (
    ("new", "New Visa"),
    ("renewal", "Renewal / Extension"),
    ("change_of_status", "Change of status"),
)


# ── Schemas ───────────────────────────────────────────────────────────────────


class JurisdictionIn(BaseModel):
    code: str = Field(min_length=2, max_length=8, examples=["JP"])
    name: str = Field(min_length=1, max_length=128, examples=["Japan"])
    is_live: bool = False
    is_enabled: bool = True


class JurisdictionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    is_live: bool | None = None
    is_enabled: bool | None = None


class JurisdictionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    is_live: bool
    is_enabled: bool


# Visa categories and case actions carry the same columns, so the three payload shapes are
# written once and named per table — the endpoints stay separate because their URLs and
# their meaning do.


class _ScopeIn(BaseModel):
    code: str = Field(min_length=1, max_length=32, examples=["work"])
    name: str = Field(min_length=1, max_length=128, examples=["Work Visa"])
    is_live: bool = False
    is_enabled: bool = True
    research_enabled: bool = False
    description: str = Field(default="", max_length=512)


class _ScopeUpdate(BaseModel):
    """``is_enabled`` is the admin's switch and the one the panel toggles.

    ``is_live`` and ``research_enabled`` are patchable because ops occasionally needs them,
    not because an on/off control should be touching them.
    """

    name: str | None = Field(default=None, min_length=1, max_length=128)
    is_live: bool | None = None
    is_enabled: bool | None = None
    research_enabled: bool | None = None
    description: str | None = Field(default=None, max_length=512)


class _ScopeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    jurisdiction_id: int
    code: str
    name: str
    is_live: bool
    is_enabled: bool
    research_enabled: bool
    description: str
    source: str
    citation: dict[str, Any] = Field(default_factory=dict)


class VisaCategoryIn(_ScopeIn):
    """Create a visa route under a jurisdiction."""


class VisaCategoryUpdate(_ScopeUpdate):
    """Patch a visa route."""


class VisaCategoryOut(_ScopeOut):
    """A visa route as stored."""


class CaseActionIn(_ScopeIn):
    """Create an application procedure under a jurisdiction."""


class CaseActionUpdate(_ScopeUpdate):
    """Patch an application procedure."""


class CaseActionOut(_ScopeOut):
    """An application procedure as stored."""


class DiscoveredScopeOut(BaseModel):
    """One route discovery proposed, and what happened to it."""

    code: str
    name: str
    description: str
    citation: dict[str, Any] = Field(default_factory=dict)
    outcome: str = Field(examples=["created", "enriched", "unchanged"])


class DiscoveryOut(BaseModel):
    jurisdiction_code: str
    visa_categories: list[DiscoveredScopeOut] = Field(default_factory=list)
    case_actions: list[DiscoveredScopeOut] = Field(default_factory=list)
    source_pages: list[dict[str, Any]] = Field(default_factory=list)
    discovered_at: str = ""
    created: int = 0
    message: str = ""


# ── Public read endpoints ─────────────────────────────────────────────────────


@router.get("", response_model=list[JurisdictionOut])
async def list_jurisdictions(
    session: SessionDep,
    live_only: bool = False,
) -> list[Jurisdiction]:
    """List jurisdictions; ``live_only=true`` returns just the ones offered to applicants."""
    stmt = select(Jurisdiction).order_by(Jurisdiction.code)
    if live_only:
        stmt = stmt.where(Jurisdiction.is_live.is_(True), Jurisdiction.is_enabled.is_(True))
    result = await session.execute(stmt)
    return list(result.scalars().all())


# ── Admin: jurisdictions CRUD ─────────────────────────────────────────────────


@router.post("", response_model=JurisdictionOut, status_code=status.HTTP_201_CREATED)
async def create_jurisdiction(
    payload: JurisdictionIn,
    session: SessionDep,
    _admin: AdminDep,
) -> Jurisdiction:
    """Create a jurisdiction with a starter set of routes, all switched off (admin only).

    The starter routes are a floor, not an answer: they exist so a fresh country is never an
    empty screen if discovery cannot reach its sources. They arrive switched off and
    uncited, and ``POST /{id}/discover`` is what fills in what the country actually
    publishes.
    """
    code_upper = payload.code.strip().upper()
    name_clean = payload.name.strip().lower()

    # Prevent creating duplicates for the same jurisdiction (exact code, aliases like UK/GB, or name)
    alias_codes = [code_upper]
    if code_upper == "GB":
        alias_codes.append("UK")
    elif code_upper == "UK":
        alias_codes.append("GB")

    existing_alias = await session.scalar(
        select(Jurisdiction).where(
            (Jurisdiction.code.in_(alias_codes)) | (func.lower(Jurisdiction.name) == name_clean)
        )
    )
    if existing_alias is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"jurisdiction '{code_upper}' already exists (as '{existing_alias.name}' [{existing_alias.code}])",
        )

    jurisdiction = Jurisdiction(
        code=code_upper,
        name=payload.name.strip(),
        is_live=payload.is_live,
        is_enabled=payload.is_enabled,
    )
    session.add(jurisdiction)
    try:
        await session.flush()
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"jurisdiction '{code_upper}' already exists",
        ) from exc
    await session.refresh(jurisdiction)

    for c_code, c_name in STARTER_CATEGORIES:
        session.add(
            VisaCategory(
                jurisdiction_id=jurisdiction.id,
                code=c_code,
                name=c_name,
                is_live=False,
                is_enabled=False,
                research_enabled=True,
                source=SOURCE_MANUAL,
            )
        )
    for a_code, a_name in STARTER_ACTIONS:
        session.add(
            CaseAction(
                jurisdiction_id=jurisdiction.id,
                code=a_code,
                name=a_name,
                is_live=False,
                is_enabled=False,
                research_enabled=True,
                source=SOURCE_MANUAL,
            )
        )
    await session.flush()
    return jurisdiction


@router.patch("/{jurisdiction_id}", response_model=JurisdictionOut)
async def update_jurisdiction(
    jurisdiction_id: int,
    payload: JurisdictionUpdate,
    session: SessionDep,
    _admin: AdminDep,
) -> Jurisdiction:
    """Update a jurisdiction's name, admin switch, or pack status (admin only)."""
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
    if payload.is_enabled is not None:
        jurisdiction.is_enabled = payload.is_enabled
    await session.flush()
    await session.refresh(jurisdiction)
    return jurisdiction


@router.delete(
    "/{jurisdiction_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_jurisdiction(
    jurisdiction_id: int,
    session: SessionDep,
    _admin: AdminDep,
) -> None:
    """Delete a jurisdiction (admin only). Fails if it has associated cases."""
    jurisdiction = await session.get(Jurisdiction, jurisdiction_id)
    if jurisdiction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="jurisdiction not found",
        )

    has_cases = await session.scalar(
        select(Case.id).where(Case.jurisdiction_id == jurisdiction_id).limit(1)
    )
    if has_cases is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"cannot delete {jurisdiction.name} ({jurisdiction.code}): it has associated cases",
        )

    # Clean up associated configuration and definition records
    await session.execute(delete(ScopeResearch).where(ScopeResearch.jurisdiction_id == jurisdiction_id))
    await session.execute(delete(PackOverride).where(PackOverride.jurisdiction_id == jurisdiction_id))
    await session.execute(delete(FormTemplate).where(FormTemplate.jurisdiction_id == jurisdiction_id))
    await session.execute(delete(DocumentRequirementSet).where(DocumentRequirementSet.jurisdiction_id == jurisdiction_id))
    await session.execute(delete(EligibilityRuleSet).where(EligibilityRuleSet.jurisdiction_id == jurisdiction_id))
    await session.execute(delete(IntakeDefinition).where(IntakeDefinition.jurisdiction_id == jurisdiction_id))
    await session.execute(delete(CaseAction).where(CaseAction.jurisdiction_id == jurisdiction_id))
    await session.execute(delete(VisaCategory).where(VisaCategory.jurisdiction_id == jurisdiction_id))
    await session.delete(jurisdiction)
    await session.flush()


# ── Admin: discover what a country offers ─────────────────────────────────────


@router.post("/{jurisdiction_id}/discover", response_model=DiscoveryOut)
async def discover_jurisdiction_scopes(
    jurisdiction_id: int,
    session: SessionDep,
    _admin: AdminDep,
    origin_country: str | None = None,
) -> DiscoveryOut:
    """Read this country's own immigration pages and record the routes it publishes.

    Called right after a country is added, and re-runnable later when a country changes what
    it offers. Every route it writes arrives switched off, so nothing reaches an applicant
    until an admin turns it on; a re-run adds only what is genuinely new and leaves existing
    switches exactly as the admin left them.
    """
    jurisdiction = await session.get(Jurisdiction, jurisdiction_id)
    if jurisdiction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="jurisdiction not found",
        )

    try:
        result = await discover_scopes(jurisdiction.code, origin_country)
    except ScopeDiscoveryUnavailable as exc:
        # 502, not 500: the request was fine, the upstream research service was not, and the
        # panel needs to say "could not ask" rather than "this country offers nothing".
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not discover routes for {jurisdiction.code}: {exc}",
        ) from exc

    applied = await apply_discovery(session, jurisdiction, result)
    found = len(applied.visa_categories) + len(applied.case_actions)
    pages = len(applied.source_pages)
    if found == 0 and pages == 0:
        message = (
            f"No official pages listing {jurisdiction.name}'s visa routes could be reached. "
            "Add its routes by hand, or try again later."
        )
    elif found == 0:
        # Pages were read and none yielded a citable route. Saying "nothing found" here
        # would read as "this country offers nothing", so the pages are named instead:
        # they are where an admin adding routes by hand should look.
        message = (
            f"Read {pages} official page(s) for {jurisdiction.name} but could not read a "
            "single route off them. The pages are linked below — add its routes by hand, "
            "or try again later."
        )
    else:
        message = (
            f"Found {found} route(s) on {jurisdiction.name}'s official pages, "
            f"{applied.created_count} new. New ones are switched off until you enable them."
        )

    return DiscoveryOut(
        jurisdiction_code=jurisdiction.code,
        visa_categories=[
            DiscoveredScopeOut(
                code=item.code,
                name=item.name,
                description=item.description,
                citation=item.citation,
                outcome=item.outcome,
            )
            for item in applied.visa_categories
        ],
        case_actions=[
            DiscoveredScopeOut(
                code=item.code,
                name=item.name,
                description=item.description,
                citation=item.citation,
                outcome=item.outcome,
            )
            for item in applied.case_actions
        ],
        source_pages=applied.source_pages,
        discovered_at=applied.discovered_at,
        created=applied.created_count,
        message=message,
    )


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
    """List visa categories for a jurisdiction; ``live_only`` = what an applicant is offered."""
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
        stmt = stmt.where(
            VisaCategory.is_enabled.is_(True),
            VisaCategory.is_live.is_(True) | VisaCategory.research_enabled.is_(True),
        )
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
    code = payload.code.lower()
    # Checked here, and backed by a unique index (migration 0016). The check gives the admin
    # the 409 that says which code clashed; the index is what makes it true under a race or
    # a raw-SQL writer.
    clash = await session.scalar(
        select(VisaCategory.id)
        .where(VisaCategory.jurisdiction_id == jurisdiction_id)
        .where(VisaCategory.code == code)
    )
    if clash is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"visa category '{code}' already exists in this jurisdiction",
        )
    vc = VisaCategory(
        jurisdiction_id=jurisdiction_id,
        code=code,
        name=payload.name,
        is_live=payload.is_live,
        is_enabled=payload.is_enabled,
        research_enabled=payload.research_enabled,
        description=payload.description,
        source=SOURCE_MANUAL,
    )
    session.add(vc)
    await session.flush()
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
    """Update a visa category's name, admin switch, or content flags (admin only)."""
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
    if payload.is_enabled is not None:
        vc.is_enabled = payload.is_enabled
    if payload.research_enabled is not None:
        vc.research_enabled = payload.research_enabled
    if payload.description is not None:
        vc.description = payload.description
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
    """List case actions for a jurisdiction; ``live_only`` = what an applicant is offered."""
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
        stmt = stmt.where(
            CaseAction.is_enabled.is_(True),
            CaseAction.is_live.is_(True) | CaseAction.research_enabled.is_(True),
        )
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
    code = payload.code.lower()
    # Same as visa categories above: an explicit 409, with the index behind it.
    clash = await session.scalar(
        select(CaseAction.id)
        .where(CaseAction.jurisdiction_id == jurisdiction_id)
        .where(CaseAction.code == code)
    )
    if clash is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"case action '{code}' already exists in this jurisdiction",
        )
    ca = CaseAction(
        jurisdiction_id=jurisdiction_id,
        code=code,
        name=payload.name,
        is_live=payload.is_live,
        is_enabled=payload.is_enabled,
        research_enabled=payload.research_enabled,
        description=payload.description,
        source=SOURCE_MANUAL,
    )
    session.add(ca)
    await session.flush()
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
    """Update a case action's name, admin switch, or content flags (admin only)."""
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
    if payload.is_enabled is not None:
        ca.is_enabled = payload.is_enabled
    if payload.research_enabled is not None:
        ca.research_enabled = payload.research_enabled
    if payload.description is not None:
        ca.description = payload.description
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
