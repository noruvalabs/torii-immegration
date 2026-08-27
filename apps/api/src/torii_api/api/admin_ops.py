"""Admin OPS endpoints — receive scraped data from the AI worker (US-25, US-26).

These endpoints let the AI scraper service POST extracted data to be stored
in the system of record. All changes require human review before going live (NF-9).
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from torii_api.auth.deps import CurrentUserDep, require_roles
from torii_api.db.models import (
    CaseAction,
    DocumentRequirementSet,
    EligibilityRuleSet,
    FormTemplate,
    IntakeDefinition,
    Jurisdiction,
    UserRole,
    VisaCategory,
)
from torii_api.db.session import get_session
from torii_api.services.form_revisions import load_revisions, pending_reviews

router = APIRouter(prefix="/v1/admin/ops", tags=["admin-ops"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]
AdminOpsDep = Annotated[CurrentUserDep, Depends(require_roles(UserRole.ADMIN, UserRole.OPS))]


# ── Request schemas ────────────────────────────────────────────────────────────


class ScopeMixin(BaseModel):
    jurisdiction_code: str = Field(min_length=2, max_length=8)
    visa_category: str = Field(min_length=1, max_length=32)
    action: str = Field(min_length=1, max_length=32)


class EligibilityRulesIn(ScopeMixin):
    rules: list[dict[str, Any]] = Field(default_factory=list)


class DocumentRequirementsIn(ScopeMixin):
    items: list[dict[str, Any]] = Field(default_factory=list)


class IntakeDefinitionIn(ScopeMixin):
    questions: list[dict[str, Any]] = Field(default_factory=list)


class FormTemplateIn(ScopeMixin):
    code: str = Field(min_length=1, max_length=64)
    version: str = Field(min_length=1, max_length=32)
    official_title: str = Field(min_length=1, max_length=256)
    citation: dict[str, Any] = Field(default_factory=dict)
    field_mappings: list[dict[str, Any]] = Field(default_factory=list)


# ── Helpers ────────────────────────────────────────────────────────────────────


async def _resolve_scope(
    session: AsyncSession,
    jurisdiction_code: str,
    visa_category: str,
    action: str,
) -> tuple[Jurisdiction, VisaCategory, CaseAction]:
    """Resolve jurisdiction + visa category + case action from codes, raising 404 if missing."""
    jurisdiction = await session.scalar(
        select(Jurisdiction).where(Jurisdiction.code == jurisdiction_code.upper())
    )
    if jurisdiction is None:
        raise HTTPException(status_code=404, detail=f"jurisdiction '{jurisdiction_code}' not found")

    vc = await session.scalar(
        select(VisaCategory).where(
            VisaCategory.jurisdiction_id == jurisdiction.id,
            VisaCategory.code == visa_category.lower(),
        )
    )
    if vc is None:
        raise HTTPException(
            status_code=404,
            detail=f"visa category '{visa_category}' not found in {jurisdiction_code}",
        )

    ca = await session.scalar(
        select(CaseAction).where(
            CaseAction.jurisdiction_id == jurisdiction.id,
            CaseAction.code == action.lower(),
        )
    )
    if ca is None:
        raise HTTPException(
            status_code=404,
            detail=f"case action '{action}' not found in {jurisdiction_code}",
        )

    return jurisdiction, vc, ca


# ── Endpoints ──────────────────────────────────────────────────────────────────


@router.post("/eligibility-rules")
async def upsert_eligibility_rules(
    payload: EligibilityRulesIn,
    session: SessionDep,
    _admin: AdminOpsDep,
) -> dict[str, str]:
    """Create or update eligibility rules for a scope. New rules are created as drafts (NF-9)."""
    _, vc, ca = await _resolve_scope(
        session, payload.jurisdiction_code, payload.visa_category, payload.action
    )

    existing = await session.scalar(
        select(EligibilityRuleSet).where(
            EligibilityRuleSet.jurisdiction_id == _.id,
            EligibilityRuleSet.visa_category_id == vc.id,
            EligibilityRuleSet.case_action_id == ca.id,
        )
    )

    if existing:
        existing.rules = payload.rules
        existing.is_live = False  # Require human review (NF-9)
    else:
        session.add(
            EligibilityRuleSet(
                jurisdiction_id=_.id,
                visa_category_id=vc.id,
                case_action_id=ca.id,
                rules=payload.rules,
                is_live=False,
            )
        )

    await session.flush()
    return {"status": "ok", "message": f"{len(payload.rules)} rules stored as draft"}


@router.post("/document-requirements")
async def upsert_document_requirements(
    payload: DocumentRequirementsIn,
    session: SessionDep,
    _admin: AdminOpsDep,
) -> dict[str, str]:
    """Create or update document requirements for a scope. New sets are drafts (NF-9)."""
    _, vc, ca = await _resolve_scope(
        session, payload.jurisdiction_code, payload.visa_category, payload.action
    )

    existing = await session.scalar(
        select(DocumentRequirementSet).where(
            DocumentRequirementSet.jurisdiction_id == _.id,
            DocumentRequirementSet.visa_category_id == vc.id,
            DocumentRequirementSet.case_action_id == ca.id,
        )
    )

    if existing:
        existing.items = payload.items
        existing.is_live = False
    else:
        session.add(
            DocumentRequirementSet(
                jurisdiction_id=_.id,
                visa_category_id=vc.id,
                case_action_id=ca.id,
                items=payload.items,
                is_live=False,
            )
        )

    await session.flush()
    return {
        "status": "ok",
        "message": f"{len(payload.items)} document requirements stored as draft",
    }


@router.post("/intake-definitions")
async def upsert_intake_definitions(
    payload: IntakeDefinitionIn,
    session: SessionDep,
    _admin: AdminOpsDep,
) -> dict[str, str]:
    """Create or update intake questionnaire for a scope. New definitions are drafts (NF-9)."""
    _, vc, ca = await _resolve_scope(
        session, payload.jurisdiction_code, payload.visa_category, payload.action
    )

    existing = await session.scalar(
        select(IntakeDefinition).where(
            IntakeDefinition.jurisdiction_id == _.id,
            IntakeDefinition.visa_category_id == vc.id,
            IntakeDefinition.case_action_id == ca.id,
        )
    )

    if existing:
        existing.questions = payload.questions
        existing.is_live = False
    else:
        session.add(
            IntakeDefinition(
                jurisdiction_id=_.id,
                visa_category_id=vc.id,
                case_action_id=ca.id,
                questions=payload.questions,
                is_live=False,
            )
        )

    await session.flush()
    return {"status": "ok", "message": f"{len(payload.questions)} intake questions stored as draft"}


@router.post("/form-templates")
async def upsert_form_template(
    payload: FormTemplateIn,
    session: SessionDep,
    _admin: AdminOpsDep,
) -> dict[str, str]:
    """Create or update a form template for a scope. New templates are drafts (NF-9)."""
    _, vc, ca = await _resolve_scope(
        session, payload.jurisdiction_code, payload.visa_category, payload.action
    )

    existing = await session.scalar(
        select(FormTemplate).where(
            FormTemplate.jurisdiction_id == _.id,
            FormTemplate.visa_category_id == vc.id,
            FormTemplate.case_action_id == ca.id,
            FormTemplate.code == payload.code,
        )
    )

    if existing:
        existing.version = payload.version
        existing.official_title = payload.official_title
        existing.citation = payload.citation
        existing.field_mappings = payload.field_mappings
        existing.is_live = False
    else:
        session.add(
            FormTemplate(
                jurisdiction_id=_.id,
                visa_category_id=vc.id,
                case_action_id=ca.id,
                code=payload.code,
                version=payload.version,
                official_title=payload.official_title,
                citation=payload.citation,
                field_mappings=payload.field_mappings,
                is_live=False,
            )
        )

    await session.flush()
    return {
        "status": "ok",
        "message": f"form template '{payload.code}' v{payload.version} stored as draft",
    }


# ── Official form revisions ────────────────────────────────────────────────────
# A ministry revision is a review, not a break. `torii-check-form-revisions` records what
# the Immigration Services Agency publishes today; this endpoint is the queue ops work
# from. Nothing here adopts a revision: a revised sheet may have moved a field, so the
# layout is re-verified by hand and the digest repinned in `jp_official_forms.py`. Until
# then the fill gate leaves that page blank rather than writing into stale coordinates.


@router.get("/form-revisions")
async def list_form_revisions(_: AdminOpsDep) -> dict[str, Any]:
    """Every form the last revision check recorded, with the queue called out."""
    records = load_revisions()
    queue = pending_reviews()
    return {
        "checked": len(records),
        "needs_review": len(queue),
        "queue": [
            {
                "code": record.code,
                "status": record.status,
                "pdf_url": record.pdf_url,
                "published_sha256": record.sha256,
                "verified_sha256": record.verified_sha256,
                "pages": record.pages,
                "note": record.note,
            }
            for record in queue
        ],
        "forms": {
            code: {
                "status": record.status,
                "pdf_url": record.pdf_url,
                "published_sha256": record.sha256,
                "verified_sha256": record.verified_sha256,
                "pages": record.pages,
            }
            for code, record in sorted(records.items())
        },
    }
