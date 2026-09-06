"""Admin OPS endpoints — receive scraped data from the AI worker (US-25, US-26).

These endpoints let the AI scraper service POST extracted data to be stored
in the system of record. All changes require human review before going live (NF-9).
"""

from __future__ import annotations

import hashlib
import io
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

import pypdf
from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from fastapi.responses import FileResponse
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
AdminOpsDep = Annotated[
    CurrentUserDep, Depends(require_roles(UserRole.ADMIN, UserRole.OPS, UserRole.EMPLOYER))
]


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
async def delete_pack_override(
    override_id: int, session: SessionDep, _admin: AdminOpsDep
) -> Response:
    """Revert one edit. The pack's own value is what the scope shows again."""
    row = await session.get(PackOverride, override_id)
    if row is None:
        raise HTTPException(status_code=404, detail="no such override")
    await session.delete(row)
    await session.flush()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ── Scope Details & Intake/PDF Editor ──────────────────────────────────────────


class ScopeDetailOut(BaseModel):
    jurisdiction: dict[str, Any]
    visa_category: dict[str, Any]
    case_action: dict[str, Any] | None = None
    available_actions: list[dict[str, Any]] = Field(default_factory=list)
    intake_questions: list[dict[str, Any]] = Field(default_factory=list)
    document_requirements: list[dict[str, Any]] = Field(default_factory=list)
    form_templates: list[dict[str, Any]] = Field(default_factory=list)
    eligibility_rules: list[dict[str, Any]] = Field(default_factory=list)


class ScopeDetailUpdate(BaseModel):
    jurisdiction_code: str
    visa_category_code: str
    action_code: str
    category_name: str | None = None
    category_description: str | None = None
    is_enabled: bool | None = None
    intake_questions: list[dict[str, Any]] | None = None
    document_requirements: list[dict[str, Any]] | None = None
    form_templates: list[dict[str, Any]] | None = None
    eligibility_rules: list[dict[str, Any]] | None = None


def _get_official_forms_dir() -> Path:
    d = Path.cwd() / "var" / "official_forms"
    if not d.is_dir():
        d = Path(__file__).resolve().parent.parent.parent.parent / "var" / "official_forms"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _find_pdf_path(code: str) -> Path | None:
    forms_dir = _get_official_forms_dir()
    clean = code.strip().lower().replace("-", "_")
    candidates = [
        forms_dir / f"{code}.pdf",
        forms_dir / f"{clean}.pdf",
        forms_dir / f"{code.lower()}.pdf",
        forms_dir / f"{code.upper()}.pdf",
    ]
    if "coe" in clean and "work" in clean:
        candidates.append(forms_dir / "jp_work_coe.pdf")
    if "ext" in clean and "work" in clean:
        candidates.append(forms_dir / "jp_work_extension.pdf")
    if "change" in clean and "work" in clean:
        candidates.append(forms_dir / "jp_work_change_of_status.pdf")

    for c in candidates:
        if c.is_file():
            return c
    return None


def _get_pdf_info(code: str, citation: dict[str, Any] | None = None) -> dict[str, Any]:
    cit = citation or {}
    pdf_path = _find_pdf_path(code)
    has_pdf = pdf_path is not None and pdf_path.is_file()

    filesize = cit.get("pdf_filesize")
    pages = cit.get("pdf_pages")
    sha256_hash = cit.get("pdf_sha256")
    filename = cit.get("pdf_filename") or (pdf_path.name if has_pdf and pdf_path else None)
    uploaded_at = cit.get("pdf_uploaded_at")
    detected_fields = cit.get("detected_fields") or []

    if has_pdf and pdf_path and (pages is None or filesize is None or not detected_fields):
        try:
            raw = pdf_path.read_bytes()
            if filesize is None:
                filesize = len(raw)
            if sha256_hash is None:
                sha256_hash = hashlib.sha256(raw).hexdigest()
            reader = pypdf.PdfReader(io.BytesIO(raw))
            if pages is None:
                pages = len(reader.pages)
            fields = reader.get_fields()
            if not detected_fields and fields:
                detected_fields = list(fields.keys())
        except Exception:
            pass

    return {
        "has_pdf": has_pdf,
        "pdf_filename": filename,
        "pdf_filesize": filesize,
        "pdf_pages": pages,
        "pdf_sha256": sha256_hash,
        "pdf_uploaded_at": uploaded_at,
        "detected_fields": detected_fields,
        "download_url": f"/backend/v1/admin/ops/form-templates/{code}/pdf" if has_pdf else None,
    }


def _fallback_pack(
    jurisdiction_code: str, visa_category_code: str, action_code: str
) -> dict[str, Any]:
    import yaml

    from torii_api.services.content_packs import resolve_packs_dir

    try:
        packs_dir = resolve_packs_dir()
        jur_dir = packs_dir / jurisdiction_code.lower()
        candidates = [
            jur_dir / f"{visa_category_code}.{action_code}.yml",
            jur_dir / f"{visa_category_code}.new_application.yml"
            if action_code in ("new", "new_application")
            else None,
            jur_dir / f"{visa_category_code}.new.yml"
            if action_code in ("new", "new_application")
            else None,
            jur_dir / f"{visa_category_code}.renewal.yml"
            if action_code in ("renewal", "extension")
            else None,
            jur_dir / f"{visa_category_code}.change_of_status.yml"
            if action_code == "change_of_status"
            else None,
        ]
        for cand in candidates:
            if cand and cand.is_file():
                with cand.open(encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                intake = data.get("intake") or {}
                docs = data.get("documents") or {}
                elig = data.get("eligibility") or {}
                forms = data.get("forms") or []
                if isinstance(forms, dict):
                    forms = [forms]
                return {
                    "questions": intake.get("questions") or [],
                    "documents": docs.get("items") or docs.get("requirements") or [],
                    "forms": forms,
                    "rules": elig.get("rules") or [],
                }
    except Exception:
        pass
    return {"questions": [], "documents": [], "forms": [], "rules": []}


@router.get("/scope-details", response_model=ScopeDetailOut)
async def get_scope_details(
    jurisdiction_code: str,
    visa_category_code: str,
    session: SessionDep,
    action_code: str | None = None,
) -> ScopeDetailOut:
    """Return full configuration of a visa route, including its intake questions, forms, and documents."""
    jurisdiction = await session.scalar(
        select(Jurisdiction).where(Jurisdiction.code == jurisdiction_code.upper())
    )
    if jurisdiction is None:
        raise HTTPException(status_code=404, detail=f"jurisdiction '{jurisdiction_code}' not found")

    vc = await session.scalar(
        select(VisaCategory).where(
            VisaCategory.jurisdiction_id == jurisdiction.id,
            VisaCategory.code == visa_category_code.lower(),
        )
    )
    if vc is None:
        raise HTTPException(
            status_code=404,
            detail=f"visa category '{visa_category_code}' not found in {jurisdiction_code}",
        )

    actions_result = await session.scalars(
        select(CaseAction)
        .where(CaseAction.jurisdiction_id == jurisdiction.id)
        .order_by(CaseAction.id)
    )
    all_actions = list(actions_result.all())

    # Find active action
    active_action: CaseAction | None = None
    if action_code:
        active_action = next(
            (a for a in all_actions if a.code.lower() == action_code.lower()), None
        )
    if active_action is None and all_actions:
        active_action = next(
            (a for a in all_actions if a.code in ("new_application", "new")), all_actions[0]
        )

    intake_questions: list[dict[str, Any]] = []
    doc_requirements: list[dict[str, Any]] = []
    form_templates: list[dict[str, Any]] = []
    eligibility_rules: list[dict[str, Any]] = []

    if active_action:
        # 1. Intake
        intake_row = await session.scalar(
            select(IntakeDefinition).where(
                IntakeDefinition.jurisdiction_id == jurisdiction.id,
                IntakeDefinition.visa_category_id == vc.id,
                IntakeDefinition.case_action_id == active_action.id,
            )
        )
        if intake_row and intake_row.questions:
            intake_questions = list(intake_row.questions)

        # 2. Documents
        doc_row = await session.scalar(
            select(DocumentRequirementSet).where(
                DocumentRequirementSet.jurisdiction_id == jurisdiction.id,
                DocumentRequirementSet.visa_category_id == vc.id,
                DocumentRequirementSet.case_action_id == active_action.id,
            )
        )
        if doc_row and doc_row.items:
            doc_requirements = list(doc_row.items)

        # 3. Forms
        forms_rows = await session.scalars(
            select(FormTemplate).where(
                FormTemplate.jurisdiction_id == jurisdiction.id,
                FormTemplate.visa_category_id == vc.id,
                FormTemplate.case_action_id == active_action.id,
            )
        )
        for f in forms_rows:
            pdf_info = _get_pdf_info(f.code, f.citation)
            form_templates.append(
                {
                    "code": f.code,
                    "version": f.version,
                    "official_title": f.official_title,
                    "citation": f.citation or {},
                    "field_mappings": f.field_mappings or [],
                    "is_live": f.is_live,
                    **pdf_info,
                }
            )

        # 4. Rules
        rule_row = await session.scalar(
            select(EligibilityRuleSet).where(
                EligibilityRuleSet.jurisdiction_id == jurisdiction.id,
                EligibilityRuleSet.visa_category_id == vc.id,
                EligibilityRuleSet.case_action_id == active_action.id,
            )
        )
        if rule_row and rule_row.rules:
            eligibility_rules = list(rule_row.rules)

        # Fallback if empty
        if (
            not intake_questions
            or not doc_requirements
            or not form_templates
            or not eligibility_rules
        ):
            fallback = _fallback_pack(jurisdiction.code, vc.code, active_action.code)
            if not intake_questions and fallback.get("questions"):
                intake_questions = fallback["questions"]
            if not doc_requirements and fallback.get("documents"):
                doc_requirements = fallback["documents"]
            if not form_templates and fallback.get("forms"):
                for f in fallback["forms"]:
                    code = f.get("code") or ""
                    pdf_info = _get_pdf_info(code, f.get("citation"))
                    form_templates.append({**f, **pdf_info})
            if not eligibility_rules and fallback.get("rules"):
                eligibility_rules = fallback["rules"]

    return ScopeDetailOut(
        jurisdiction={"id": jurisdiction.id, "code": jurisdiction.code, "name": jurisdiction.name},
        visa_category={
            "id": vc.id,
            "code": vc.code,
            "name": vc.name,
            "description": vc.description or "",
            "is_enabled": vc.is_enabled,
            "is_live": vc.is_live,
            "citation": vc.citation or {},
        },
        case_action={
            "id": active_action.id,
            "code": active_action.code,
            "name": active_action.name,
            "description": active_action.description or "",
            "is_enabled": active_action.is_enabled,
        }
        if active_action
        else None,
        available_actions=[
            {
                "id": a.id,
                "code": a.code,
                "name": a.name,
                "description": a.description or "",
                "is_enabled": a.is_enabled,
            }
            for a in all_actions
        ],
        intake_questions=intake_questions,
        document_requirements=doc_requirements,
        form_templates=form_templates,
        eligibility_rules=eligibility_rules,
    )


@router.put("/scope-details", response_model=ScopeDetailOut)
async def update_scope_details(
    payload: ScopeDetailUpdate,
    session: SessionDep,
    _admin: AdminOpsDep,
) -> ScopeDetailOut:
    """Save changes to a visa route's intake questionnaire, forms, documents, and rules."""
    jurisdiction, vc, ca = await _resolve_scope(
        session, payload.jurisdiction_code, payload.visa_category_code, payload.action_code
    )

    if payload.category_name is not None:
        vc.name = payload.category_name
    if payload.category_description is not None:
        vc.description = payload.category_description
    if payload.is_enabled is not None:
        vc.is_enabled = payload.is_enabled

    # 1. Update IntakeDefinition
    if payload.intake_questions is not None:
        intake_row = await session.scalar(
            select(IntakeDefinition).where(
                IntakeDefinition.jurisdiction_id == jurisdiction.id,
                IntakeDefinition.visa_category_id == vc.id,
                IntakeDefinition.case_action_id == ca.id,
            )
        )
        if intake_row:
            intake_row.questions = payload.intake_questions
            intake_row.is_live = True
        else:
            session.add(
                IntakeDefinition(
                    jurisdiction_id=jurisdiction.id,
                    visa_category_id=vc.id,
                    case_action_id=ca.id,
                    questions=payload.intake_questions,
                    is_live=True,
                )
            )

    # 2. Update DocumentRequirementSet
    if payload.document_requirements is not None:
        doc_row = await session.scalar(
            select(DocumentRequirementSet).where(
                DocumentRequirementSet.jurisdiction_id == jurisdiction.id,
                DocumentRequirementSet.visa_category_id == vc.id,
                DocumentRequirementSet.case_action_id == ca.id,
            )
        )
        if doc_row:
            doc_row.items = payload.document_requirements
            doc_row.is_live = True
        else:
            session.add(
                DocumentRequirementSet(
                    jurisdiction_id=jurisdiction.id,
                    visa_category_id=vc.id,
                    case_action_id=ca.id,
                    items=payload.document_requirements,
                    is_live=True,
                )
            )

    # 3. Update EligibilityRuleSet
    if payload.eligibility_rules is not None:
        rule_row = await session.scalar(
            select(EligibilityRuleSet).where(
                EligibilityRuleSet.jurisdiction_id == jurisdiction.id,
                EligibilityRuleSet.visa_category_id == vc.id,
                EligibilityRuleSet.case_action_id == ca.id,
            )
        )
        if rule_row:
            rule_row.rules = payload.eligibility_rules
            rule_row.is_live = True
        else:
            session.add(
                EligibilityRuleSet(
                    jurisdiction_id=jurisdiction.id,
                    visa_category_id=vc.id,
                    case_action_id=ca.id,
                    rules=payload.eligibility_rules,
                    is_live=True,
                )
            )

    # 4. Update FormTemplate
    if payload.form_templates is not None:
        for f in payload.form_templates:
            code = f.get("code")
            if not code:
                continue
            existing_form = await session.scalar(
                select(FormTemplate).where(
                    FormTemplate.jurisdiction_id == jurisdiction.id,
                    FormTemplate.visa_category_id == vc.id,
                    FormTemplate.case_action_id == ca.id,
                    FormTemplate.code == code,
                )
            )
            if existing_form:
                existing_form.version = f.get("version", "1.0")
                existing_form.official_title = f.get("official_title", code)
                existing_form.citation = f.get("citation", {})
                existing_form.field_mappings = f.get("field_mappings", [])
                existing_form.is_live = True
            else:
                session.add(
                    FormTemplate(
                        jurisdiction_id=jurisdiction.id,
                        visa_category_id=vc.id,
                        case_action_id=ca.id,
                        code=code,
                        version=f.get("version", "1.0"),
                        official_title=f.get("official_title", code),
                        citation=f.get("citation", {}),
                        field_mappings=f.get("field_mappings", []),
                        is_live=True,
                    )
                )

    await session.commit()
    await session.refresh(vc)
    await session.refresh(ca)

    return await get_scope_details(
        jurisdiction_code=payload.jurisdiction_code,
        visa_category_code=payload.visa_category_code,
        action_code=payload.action_code,
        session=session,
    )


@router.post("/form-templates/{code}/upload-pdf")
async def upload_form_template_pdf(
    code: str,
    session: SessionDep,
    _admin: AdminOpsDep,
    file: UploadFile = File(...),
    jurisdiction_code: str | None = None,
    visa_category_code: str | None = None,
    action_code: str | None = None,
) -> dict[str, Any]:
    """Upload or replace the official government PDF template for a form."""
    content = await file.read()
    if not content.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is not a valid PDF document (must start with %PDF- header).",
        )

    try:
        reader = pypdf.PdfReader(io.BytesIO(content))
        pages = len(reader.pages)
        fields = reader.get_fields()
        detected_fields = list(fields.keys()) if fields else []
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Could not parse PDF: {exc}",
        ) from exc

    sha256_hash = hashlib.sha256(content).hexdigest()
    now_iso = datetime.now(UTC).isoformat()

    forms_dir = _get_official_forms_dir()
    clean_code = code.strip().lower().replace("-", "_")
    save_path = forms_dir / f"{clean_code}.pdf"
    save_path.write_bytes(content)

    # Also update DB row citation if exists
    form_query = select(FormTemplate).where(FormTemplate.code.ilike(code))
    if jurisdiction_code:
        jur = await session.scalar(
            select(Jurisdiction).where(Jurisdiction.code == jurisdiction_code.upper())
        )
        if jur:
            form_query = form_query.where(FormTemplate.jurisdiction_id == jur.id)
    if visa_category_code:
        vc = await session.scalar(
            select(VisaCategory).where(VisaCategory.code == visa_category_code.lower())
        )
        if vc:
            form_query = form_query.where(FormTemplate.visa_category_id == vc.id)

    db_forms = (await session.scalars(form_query)).all()
    for f in db_forms:
        citation = dict(f.citation or {})
        citation["pdf_filename"] = file.filename
        citation["pdf_filesize"] = len(content)
        citation["pdf_sha256"] = sha256_hash
        citation["pdf_pages"] = pages
        citation["pdf_uploaded_at"] = now_iso
        citation["detected_fields"] = detected_fields
        f.citation = citation

    if db_forms:
        await session.commit()

    return {
        "success": True,
        "code": code,
        "filename": file.filename,
        "filesize": len(content),
        "pages": pages,
        "sha256": sha256_hash,
        "detected_fields": detected_fields,
        "uploaded_at": now_iso,
        "download_url": f"/backend/v1/admin/ops/form-templates/{code}/pdf",
        "message": f"PDF successfully uploaded for form '{code}' ({pages} pages, {len(detected_fields)} detected fields).",
    }


@router.get("/form-templates/{code}/pdf")
async def get_form_template_pdf(code: str) -> FileResponse:
    """Preview or download the official government PDF template for a form."""
    pdf_path = _find_pdf_path(code)
    if not pdf_path or not pdf_path.is_file():
        raise HTTPException(
            status_code=404,
            detail=f"No PDF file uploaded for form template '{code}'",
        )
    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=f"{code}.pdf",
        content_disposition_type="inline",
    )


@router.get("/form-templates")
async def list_all_form_templates(
    session: SessionDep,
) -> list[dict[str, Any]]:
    """List all form templates across all jurisdictions with PDF status."""
    templates = (await session.scalars(select(FormTemplate).order_by(FormTemplate.code))).all()
    out = []
    for t in templates:
        pdf_info = _get_pdf_info(t.code, t.citation)
        jur = await session.get(Jurisdiction, t.jurisdiction_id) if t.jurisdiction_id else None
        vc = await session.get(VisaCategory, t.visa_category_id) if t.visa_category_id else None
        ca = await session.get(CaseAction, t.case_action_id) if t.case_action_id else None
        out.append(
            {
                "id": t.id,
                "code": t.code,
                "version": t.version,
                "official_title": t.official_title,
                "is_live": t.is_live,
                "jurisdiction_code": jur.code if jur else None,
                "jurisdiction_name": jur.name if jur else None,
                "visa_category_code": vc.code if vc else None,
                "visa_category_name": vc.name if vc else None,
                "action_code": ca.code if ca else None,
                "action_name": ca.name if ca else None,
                "field_mappings": t.field_mappings or [],
                **pdf_info,
            }
        )
    return out
