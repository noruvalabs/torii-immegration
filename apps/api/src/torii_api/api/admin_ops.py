"""Admin OPS endpoints — receive scraped data from the AI worker (US-25, US-26).

These endpoints let the AI scraper service POST extracted data to be stored
in the system of record. All changes require human review before going live (NF-9).
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
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
    PackOverride,
    UserRole,
    VisaCategory,
)
from torii_api.db.session import get_session
from torii_api.services.form_revisions import load_revisions, pending_reviews
from torii_api.services.pack_overrides import (
    SECTION_DOCUMENTS,
    SECTION_INTAKE,
    SECTION_RULES,
    OverrideError,
    applies_to,
    section_of,
    stale_overrides,
    validate_path,
)
from torii_api.services.pack_proposals import (
    Change,
    Proposal,
    ProposalError,
    decide,
    diff_against_pack,
    list_proposals,
    load_proposal,
    propose,
)

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


class PackChangeIn(BaseModel):
    """One line of a pack and what the agent found it should say."""

    path: str = Field(min_length=1, max_length=200)
    to: Any = None
    citation: dict[str, Any] = Field(default_factory=dict)
    reason: str = Field(default="", max_length=500)


class PackProposalIn(BaseModel):
    """Either an explicit set of changed lines, or a whole researched pack to diff."""

    scope: str = Field(min_length=4, max_length=64)
    source: str = Field(default="agentic_research", max_length=64)
    summary: str = Field(default="", max_length=500)
    changes: list[PackChangeIn] = Field(default_factory=list)
    pack: dict[str, Any] | None = None


class PackDecisionIn(BaseModel):
    accept: bool
    note: str = Field(default="", max_length=500)


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


# ── Pack proposals: the agent proposes, ops promote ────────────────────────────
# Research either went live automatically or not at all. That is right for a fee or a
# filing channel, where the citation gate is the whole review; it is wrong for the wording
# an applicant reads. A proposal is a diff against `docs/jurisdictions/**` with the source
# for each changed line, so a bad one is a rejected diff rather than a live regression.


def _proposal_out(proposal: Proposal) -> dict[str, Any]:
    return proposal.as_dict()


@router.post("/pack-proposals", status_code=201)
async def create_pack_proposal(payload: PackProposalIn, _: AdminOpsDep) -> dict[str, Any]:
    """Queue a proposed change for review. An uncited line is refused, not queued."""
    changes = [
        Change(
            path=change.path,
            to=change.to,
            citation={str(k): str(v) for k, v in (change.citation or {}).items()},
            reason=change.reason,
        )
        for change in payload.changes
    ]
    try:
        if payload.pack is not None:
            changes.extend(diff_against_pack(payload.scope, payload.pack))
        proposal = propose(
            scope=payload.scope,
            changes=changes,
            source=payload.source,
            summary=payload.summary,
        )
    except ProposalError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _proposal_out(proposal)


@router.get("/pack-proposals")
async def list_pack_proposals(
    _: AdminOpsDep, status: str | None = None, scope: str | None = None
) -> dict[str, Any]:
    proposals = list_proposals(status=status, scope=scope)
    return {
        "count": len(proposals),
        "pending": sum(1 for item in proposals if item.status == "pending"),
        "proposals": [_proposal_out(item) for item in proposals],
    }


@router.get("/pack-proposals/{proposal_id}")
async def get_pack_proposal(proposal_id: str, _: AdminOpsDep) -> dict[str, Any]:
    try:
        proposal = load_proposal(proposal_id)
    except ProposalError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if proposal is None:
        raise HTTPException(status_code=404, detail="no such proposal")
    return _proposal_out(proposal)


@router.post("/pack-proposals/{proposal_id}/decision")
async def decide_pack_proposal(
    proposal_id: str, payload: PackDecisionIn, user: AdminOpsDep
) -> dict[str, Any]:
    """Accept a proposal, rewriting its pack, or reject it. A decision is made once."""
    try:
        proposal = decide(
            proposal_id,
            accept=payload.accept,
            reviewer=getattr(user, "email", None) or str(getattr(user, "id", "ops")),
            note=payload.note,
        )
    except ProposalError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _proposal_out(proposal)


# ── Pack overrides ─────────────────────────────────────────────────────────────
# The upserts above write into the seeded rows, which `seed()` rewrites from the packs on
# every run — so an edit saved through them lives until the next boot and no longer. These
# endpoints edit one value at a time, beside the seeded row rather than inside it, and
# survive a reseed. See torii_api.services.pack_overrides.


class PackOverrideIn(ScopeMixin):
    path: str = Field(min_length=1, max_length=256)
    value: Any = None
    reason: str = Field(default="", max_length=2000)


def _override_out(row: PackOverride) -> dict[str, Any]:
    return {
        "id": row.id,
        "path": row.path,
        "value": row.value,
        "reason": row.reason,
        "created_by": row.created_by,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


@router.get("/pack-overrides")
async def list_pack_overrides(
    session: SessionDep,
    _admin: AdminOpsDep,
    jurisdiction_code: str,
    visa_category: str,
    action: str,
) -> dict[str, Any]:
    """Every admin edit live on a scope, and which of them no longer land.

    A pack that moved on can leave an override addressing a question that no longer
    exists. It is skipped at read time rather than applied to the wrong item, and named
    here so that is visible instead of merely quiet.
    """
    jurisdiction, category, case_action = await _resolve_scope(
        session, jurisdiction_code, visa_category, action
    )
    rows = list(
        await session.scalars(
            select(PackOverride).where(
                PackOverride.jurisdiction_id == jurisdiction.id,
                PackOverride.visa_category_id == category.id,
                PackOverride.case_action_id == case_action.id,
            )
        )
    )
    overrides = [{"path": row.path, "value": row.value} for row in rows]

    stale: list[str] = []
    for model, attribute, section in (
        (IntakeDefinition, "questions", SECTION_INTAKE),
        (EligibilityRuleSet, "rules", SECTION_RULES),
        (DocumentRequirementSet, "items", SECTION_DOCUMENTS),
    ):
        seeded = await session.scalar(
            select(model).where(
                model.jurisdiction_id == jurisdiction.id,
                model.visa_category_id == category.id,
                model.case_action_id == case_action.id,
            )
        )
        items = list(getattr(seeded, attribute) or []) if seeded is not None else []
        stale.extend(stale_overrides(items, overrides, section=section))

    return {"overrides": [_override_out(row) for row in rows], "stale": stale}


@router.put("/pack-overrides")
async def upsert_pack_override(
    payload: PackOverrideIn, session: SessionDep, user: AdminOpsDep
) -> dict[str, Any]:
    """Set one value on a scope, or change the value already set at that path.

    The path is validated against the seeded content before it is stored: a path that
    addresses nothing is refused here rather than accepted and silently never applied,
    which is the failure this whole mechanism exists to stop happening quietly.
    """
    jurisdiction, category, case_action = await _resolve_scope(
        session, payload.jurisdiction_code, payload.visa_category, payload.action
    )
    try:
        section = section_of(payload.path)
        validate_path(payload.path)
    except OverrideError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    model, attribute = {
        SECTION_INTAKE: (IntakeDefinition, "questions"),
        SECTION_RULES: (EligibilityRuleSet, "rules"),
        SECTION_DOCUMENTS: (DocumentRequirementSet, "items"),
    }[section]
    seeded = await session.scalar(
        select(model).where(
            model.jurisdiction_id == jurisdiction.id,
            model.visa_category_id == category.id,
            model.case_action_id == case_action.id,
        )
    )
    items = list(getattr(seeded, attribute) or []) if seeded is not None else []
    if not applies_to(items, payload.path):
        raise HTTPException(
            status_code=404,
            detail=f"{payload.path} addresses nothing in this scope's {section}",
        )

    existing = await session.scalar(
        select(PackOverride).where(
            PackOverride.jurisdiction_id == jurisdiction.id,
            PackOverride.visa_category_id == category.id,
            PackOverride.case_action_id == case_action.id,
            PackOverride.path == payload.path,
        )
    )
    editor = getattr(user, "email", None) or str(getattr(user, "id", "ops"))
    if existing is not None:
        existing.value = payload.value
        existing.reason = payload.reason
        existing.created_by = editor
        row = existing
    else:
        row = PackOverride(
            jurisdiction_id=jurisdiction.id,
            visa_category_id=category.id,
            case_action_id=case_action.id,
            path=payload.path,
            value=payload.value,
            reason=payload.reason,
            created_by=editor,
        )
        session.add(row)
    await session.flush()
    # The timestamps come from the database clock, so they are unloaded until they are
    # read back. Reading them lazily while serialising is synchronous IO on an async
    # session, which raises MissingGreenlet rather than returning a row.
    await session.refresh(row)
    return _override_out(row)


@router.delete(
    "/pack-overrides/{override_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_pack_override(override_id: int, session: SessionDep, _admin: AdminOpsDep) -> None:
    """Revert one edit. The pack's own value is what the scope shows again."""
    row = await session.get(PackOverride, override_id)
    if row is None:
        raise HTTPException(status_code=404, detail="no such override")
    await session.delete(row)
    await session.flush()
