"""Applicant-core case workflow endpoints (US-04 through US-16)."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from torii_api.api.cases import (
    _intake_questions_for_case,
    _owned_case,
    _research_for_case,
    _scope_label,
)
from torii_api.auth.deps import CurrentUserDep, require_roles
from torii_api.config import get_settings
from torii_api.db.models import (
    AppointmentStatus,
    Case,
    CaseAction,
    CaseAppointment,
    CaseChecklistItem,
    CaseDocument,
    CaseEscalation,
    CaseGeneratedForm,
    DocumentRequirementSet,
    EligibilityRuleSet,
    FormTemplate,
    Jurisdiction,
    PackOverride,
    User,
    UserRole,
)
from torii_api.db.session import get_session
from torii_api.services.agentic import (
    find_admissibility,
    find_case_stage,
    scope_key,
    stage_is_usable,
    stage_items,
)
from torii_api.services.case_audit import (
    APPOINTMENT_BLOCK_MESSAGES,
    APPOINTMENT_ROUTES,
    TASHEER_BOOKING_URL,
    TASHEER_CENTRE_DEFAULT,
    AuditStep,
    CaseAudit,
    assemble_audit,
    build_instructions,
    consistency_checks,
    document_audit,
    intake_completeness,
    route_for_case,
)
from torii_api.services.case_plan import build_payload, request_plan
from torii_api.services.checklist import ChecklistStatus, update_status, visible_requirement_items
from torii_api.services.citations import resolve_official_citation
from torii_api.services.content_packs import load_jurisdiction_meta, load_pack_by_scope
from torii_api.services.document_export import (
    MEDIA_TYPES,
    render_bundle,
    render_document,
    safe_stem,
)
from torii_api.services.eligibility import (
    EligibilityResult,
    evaluate_eligibility_with_ai,
)
from torii_api.services.forms import fill_form
from torii_api.services.guidance import next_status_for_phase
from torii_api.services.i18n import localized
from torii_api.services.intake import parse_questions
from torii_api.services.journey import build_journey
from torii_api.services.jp_official_forms import forms_for_scope
from torii_api.services.official_form_service import (
    describe_scope_forms,
    render_form,
    render_primary_form,
)
from torii_api.services.pack_overrides import (
    SECTION_DOCUMENTS,
    SECTION_RULES,
    apply_overrides,
)
from torii_api.services.packet import assemble_packet
from torii_api.services.payment import case_has_packet_entitlement
from torii_api.services.portal_pack import build_portal_pack
from torii_api.services.research import (
    research_documents,
    research_forms,
    research_is_usable,
    research_rules,
)
from torii_api.services.review import ReviewResult, review_packet
from torii_api.services.submission_kit import build_submission_kit, kit_from_research

router = APIRouter(prefix="/v1/cases", tags=["case-workflow"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]


class LocaleIn(BaseModel):
    locale: str = Field(min_length=2, max_length=16)
    host_locale: str | None = Field(default=None, min_length=2, max_length=16)


class LocaleOut(BaseModel):
    locale: str
    host_locale: str


class ChecklistItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    case_id: int
    code: str
    name: str
    how_to_obtain: str
    why_required: str
    is_required: bool
    status: ChecklistStatus
    citation: dict[str, Any]
    document_id: int | None = None


class ChecklistStatusIn(BaseModel):
    status: Literal["gathered", "uploaded"]


class DocumentIn(BaseModel):
    doc_type: str = Field(min_length=1, max_length=64)
    filename: str = Field(min_length=1, max_length=256)
    storage_key: str = Field(min_length=1, max_length=512)
    extracted_fields: dict[str, Any] = Field(default_factory=dict)
    extraction_confidence: float | None = Field(default=None, ge=0, le=1)
    content_type: str = Field(default="application/octet-stream", max_length=128)
    checklist_item_id: int | None = None


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    case_id: int
    doc_type: str
    filename: str
    storage_key: str
    extracted_fields: dict[str, Any]
    extraction_confidence: float | None
    confirmed: bool
    content_type: str


class GeneratedFormOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    case_id: int
    form_template_id: int | None = None
    research_id: int | None = None
    form_code: str
    form_version: str
    filled_fields: dict[str, Any]
    missing_required_fields: list[str]
    citation: dict[str, Any]
    # The form's own name, from the pack or the research that produced it. Resolved at
    # read time because the generated row stores only the code — without it the browser
    # was guessing a title from the code, and guessing it wrongly.
    official_title: str | None = None


class EscalationIn(BaseModel):
    reason: Literal[
        "out_of_scope", "low_confidence", "requires_legal_advice", "unsupported_request"
    ]
    message: str = Field(min_length=1, max_length=4000)
    consent_to_share: bool = False


class EscalationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    case_id: int
    reason: str
    message: str
    consent_to_share: bool
    status: str
    outcome: str | None


@dataclass
class _FormDescriptor:
    """One form to generate — either from a live FormTemplate or a research snapshot."""

    code: str
    version: str
    official_title: str
    citation: dict[str, Any]
    field_mappings: list[dict[str, Any]]
    template_id: int | None = None
    research_id: int | None = None


async def _research_is_usable_for(session: AsyncSession, case: Case) -> bool:
    research = await _research_for_case(session, case)
    return research is not None and research_is_usable(research)


async def _resolve_action_ids(
    session: AsyncSession, jurisdiction_id: int, action_id: int | None
) -> list[int]:
    if action_id is None:
        return []
    action_ids = [action_id]
    case_act = await session.get(CaseAction, action_id)
    if case_act is not None:
        alt_code = (
            "new_application"
            if case_act.code == "new"
            else ("new" if case_act.code == "new_application" else None)
        )
        if alt_code:
            alt_act = await session.scalar(
                select(CaseAction).where(
                    CaseAction.jurisdiction_id == jurisdiction_id,
                    CaseAction.code == alt_code,
                )
            )
            if alt_act is not None:
                action_ids.append(alt_act.id)
    return action_ids


async def _overrides_for_case(session: AsyncSession, case: Case) -> list[dict[str, Any]]:
    """Admin edits stored against this case's scope.

    Seed rewrites the seeded rows from the packs on every run, so an ops edit is kept
    beside them and re-applied here instead of being written into the row it would be
    erased from.
    """
    if case.visa_category_id is None or case.case_action_id is None:
        return []
    action_ids = await _resolve_action_ids(session, case.jurisdiction_id, case.case_action_id)
    rows = await session.scalars(
        select(PackOverride).where(
            PackOverride.jurisdiction_id == case.jurisdiction_id,
            PackOverride.visa_category_id == case.visa_category_id,
            PackOverride.case_action_id.in_(action_ids),
        )
    )
    return [{"path": row.path, "value": row.value} for row in rows]


async def _effective_rules(session: AsyncSession, case: Case) -> list[dict[str, Any]]:
    """Eligibility rules for the case: live definition if available, else research snapshot fallback."""
    if case.visa_category_id is not None and case.case_action_id is not None:
        action_ids = await _resolve_action_ids(session, case.jurisdiction_id, case.case_action_id)
        definition = await session.scalar(
            select(EligibilityRuleSet).where(
                EligibilityRuleSet.jurisdiction_id == case.jurisdiction_id,
                EligibilityRuleSet.visa_category_id == case.visa_category_id,
                EligibilityRuleSet.case_action_id.in_(action_ids),
                EligibilityRuleSet.is_live.is_(True),
            )
        )
        if definition is not None and definition.rules:
            return apply_overrides(
                list(definition.rules),
                await _overrides_for_case(session, case),
                section=SECTION_RULES,
            )

    # Check CaseStageResearch (newer agentic pipeline)
    stage_res = await find_case_stage(session, case.id, "eligibility")
    if stage_res is not None and stage_is_usable(stage_res):
        rules = stage_items(stage_res, "eligibility")
        if rules:
            return rules

    research = await _research_for_case(session, case)
    if research is not None and research_is_usable(research):
        rules = research_rules(research.payload)
        if rules:
            return rules
    return []


async def _effective_documents(session: AsyncSession, case: Case) -> list[dict[str, Any]]:
    """Document requirements for the case: live definition if available, else research snapshot fallback."""
    if case.visa_category_id is not None and case.case_action_id is not None:
        action_ids = await _resolve_action_ids(session, case.jurisdiction_id, case.case_action_id)
        definition = await session.scalar(
            select(DocumentRequirementSet).where(
                DocumentRequirementSet.jurisdiction_id == case.jurisdiction_id,
                DocumentRequirementSet.visa_category_id == case.visa_category_id,
                DocumentRequirementSet.case_action_id.in_(action_ids),
                DocumentRequirementSet.is_live.is_(True),
            )
        )
        if definition is not None and definition.items:
            return apply_overrides(
                list(definition.items),
                await _overrides_for_case(session, case),
                section=SECTION_DOCUMENTS,
            )

    # Check CaseStageResearch (newer agentic pipeline)
    stage_res = await find_case_stage(session, case.id, "documents")
    if stage_res is not None and stage_is_usable(stage_res):
        docs = stage_items(stage_res, "documents")
        if docs:
            return docs

    research = await _research_for_case(session, case)
    if research is not None and research_is_usable(research):
        docs = research_documents(research.payload)
        if docs:
            return docs
    return []


async def _effective_templates(session: AsyncSession, case: Case) -> list[_FormDescriptor]:
    """Forms for the case: live FormTemplates if available, else research snapshot fallback."""
    if case.visa_category_id is not None and case.case_action_id is not None:
        action_ids = await _resolve_action_ids(session, case.jurisdiction_id, case.case_action_id)
        result = await session.execute(
            select(FormTemplate)
            .where(
                FormTemplate.jurisdiction_id == case.jurisdiction_id,
                FormTemplate.visa_category_id == case.visa_category_id,
                FormTemplate.case_action_id.in_(action_ids),
                FormTemplate.is_live.is_(True),
            )
            .order_by(FormTemplate.code)
        )
        live = list(result.scalars().all())
        if live:
            seen_codes: set[str] = set()
            unique_live: list[FormTemplate] = []
            for t in live:
                if t.code not in seen_codes:
                    seen_codes.add(t.code)
                    unique_live.append(t)
            return [
                _FormDescriptor(
                    code=t.code,
                    version=t.version,
                    official_title=t.official_title,
                    citation=dict(t.citation or {}),
                    field_mappings=list(t.field_mappings or []),
                    template_id=t.id,
                )
                for t in unique_live
            ]

    # Check CaseStageResearch (newer agentic pipeline)
    stage_res = await find_case_stage(session, case.id, "forms")
    if stage_res is not None and stage_is_usable(stage_res):
        forms = [
            _FormDescriptor(
                code=str(form.get("code") or "form"),
                version=str(form.get("version") or ""),
                official_title=str(form.get("official_title") or form.get("code") or "form"),
                citation=dict(form.get("citation") or {}),
                field_mappings=list(form.get("field_mappings") or []),
                research_id=None,
            )
            for form in stage_items(stage_res, "forms")
            if isinstance(form, dict)
        ]
        if forms:
            return forms

    research = await _research_for_case(session, case)
    if research is not None and research_is_usable(research):
        forms = [
            _FormDescriptor(
                code=str(form.get("code") or "form"),
                version=str(form.get("version") or ""),
                official_title=str(form.get("official_title") or form.get("code") or "form"),
                citation=dict(form.get("citation") or {}),
                field_mappings=list(form.get("field_mappings") or []),
                research_id=research.id,
            )
            for form in research_forms(research.payload)
            if isinstance(form, dict)
        ]
        if forms:
            return forms
    return []


async def _documents(session: AsyncSession, case_id: int) -> list[CaseDocument]:
    result = await session.execute(
        select(CaseDocument).where(CaseDocument.case_id == case_id).order_by(CaseDocument.id)
    )
    return list(result.scalars().all())


async def _forms(session: AsyncSession, case_id: int) -> list[CaseGeneratedForm]:
    result = await session.execute(
        select(CaseGeneratedForm)
        .where(CaseGeneratedForm.case_id == case_id)
        .order_by(CaseGeneratedForm.id)
    )
    return list(result.scalars().all())


async def _checklist(session: AsyncSession, case_id: int) -> list[CaseChecklistItem]:
    result = await session.execute(
        select(CaseChecklistItem)
        .where(CaseChecklistItem.case_id == case_id)
        .order_by(CaseChecklistItem.id)
    )
    return list(result.scalars().all())


def _model_dict(item: BaseModel) -> dict[str, Any]:
    return item.model_dump(mode="json")


async def _review(session: AsyncSession, case: Case) -> ReviewResult:
    templates = await _effective_templates(session, case)
    live_versions = {template.code: template.version for template in templates}
    documents = [
        DocumentOut.model_validate(item).model_dump(mode="json")
        for item in await _documents(session, case.id)
    ]
    existing_forms = await _forms(session, case.id)
    answers = dict(case.intake_answers or {})
    if existing_forms and templates:
        template_by_code = {t.code: t for t in templates}
        for ef in existing_forms:
            t = template_by_code.get(ef.form_code)
            if t and t.field_mappings:
                filled = fill_form(t.field_mappings, answers)
                ef.filled_fields = filled.filled_fields
                ef.missing_required_fields = filled.missing_required_fields
        await session.flush()
    forms = [
        GeneratedFormOut.model_validate(item).model_dump(mode="json") for item in existing_forms
    ]
    return review_packet(answers, documents, forms, live_versions)


@router.patch("/{case_id}/locale", response_model=LocaleOut)
async def patch_locale(
    case_id: int, payload: LocaleIn, session: SessionDep, user: CurrentUserDep
) -> LocaleOut:
    case = await _owned_case(session, case_id, user)
    case.locale = payload.locale
    if payload.host_locale is not None:
        case.host_locale = payload.host_locale
    await session.flush()
    return LocaleOut(locale=case.locale, host_locale=case.host_locale)


async def _run_evaluation(session: AsyncSession, case: Case) -> EligibilityResult | None:
    """Run the scope's eligibility evaluation and store the snapshot.

    Returns ``None`` when the scope has no rules — callers that require an
    evaluation (the evaluate endpoint) turn that into a 404, while the
    audit reports eligibility as not-yet-evaluated instead.
    """
    rules = await _effective_rules(session, case)
    if not rules:
        return None
    # Evaluate against the rules in force on the day the application was received,
    # not today — a fee or requirement change mid-processing must not retroactively
    # affect a filing (e.g. the ISA's tiered fees effective 2026-10-01).
    as_of = case.created_at.date() if case.created_at is not None else date.today()
    # Context carries dimensions that live outside the intake answers: the employer
    j_code, v_code, a_code, _ = await _scope_label(session, case)
    context: dict[str, Any] = {
        "employer_category": (case.intake_answers or {}).get("employer_category"),
        "jurisdiction_code": j_code or "JP",
        "visa_category": v_code or "",
    }
    if case.prior_application:
        context.update(case.prior_application)
    answers = dict(case.intake_answers or {})
    result = await evaluate_eligibility_with_ai(
        answers,
        rules,
        destination_code=j_code or "JP",
        purpose_code=v_code or "tourist",
        action_code=a_code or "new_application",
        nationality=case.origin_country
        or str(answers.get("visitor_nationality") or answers.get("nationality") or ""),
        residence_country=case.residence_country
        or str(answers.get("current_residence_country") or answers.get("residence_country") or ""),
        as_of=as_of,
        context=context,
    )
    case.eligibility_snapshot = result.model_dump(mode="json")
    await session.flush()
    return result


@router.post("/{case_id}/eligibility/evaluate", response_model=EligibilityResult)
async def evaluate_case_eligibility(
    case_id: int, session: SessionDep, user: CurrentUserDep
) -> EligibilityResult:
    case = await _owned_case(session, case_id, user)
    result = await _run_evaluation(session, case)
    if result is None:
        raise HTTPException(
            status_code=404, detail="no eligibility rules available for this case scope"
        )
    new_status = next_status_for_phase("checklist", case.status)
    if new_status is not None:
        case.status = new_status
        await session.flush()
    return result


@router.get("/{case_id}/eligibility", response_model=EligibilityResult)
async def get_case_eligibility(
    case_id: int, session: SessionDep, user: CurrentUserDep
) -> EligibilityResult:
    case = await _owned_case(session, case_id, user)
    if case.eligibility_snapshot is None:
        raise HTTPException(status_code=404, detail="eligibility has not been evaluated")
    return EligibilityResult.model_validate(case.eligibility_snapshot)


# ── Readiness audit + in-person appointments (Phase 3) ───────────────────────


async def _build_audit(session: AsyncSession, case: Case) -> CaseAudit:
    """Assemble the readiness audit for a case from its live workflow data."""
    j_code, v_code, _a_code, _label = await _scope_label(session, case)
    answers = dict(case.intake_answers or {})
    questions = parse_questions(
        await _intake_questions_for_case(session, case),
        jurisdiction_code=j_code or "",
        visa_category=v_code or "",
    )
    owner = await session.get(User, case.user_id) if case.user_id else None
    contact_email = (
        answers.get("email_address")
        or answers.get("email")
        or case.applicant_email
        or (owner.email if owner is not None else None)
    )
    checklist_dicts = [
        {
            "code": item.code,
            "name": item.name,
            "is_required": item.is_required,
            "status": item.status,
            "document_id": item.document_id,
        }
        for item in await _checklist(session, case.id)
    ]
    document_dicts = [
        {
            "id": doc.id,
            "doc_type": doc.doc_type,
            "filename": doc.filename,
            "confirmed": doc.confirmed,
        }
        for doc in await _documents(session, case.id)
    ]
    documents, uploaded = document_audit(checklist_dicts, document_dicts)
    return assemble_audit(
        case_id=case.id,
        reference=case.reference or f"CASE-{case.id}",
        jurisdiction_code=j_code,
        route=route_for_case(j_code, answers),
        intake=intake_completeness(questions, answers),
        eligibility=await _run_evaluation(session, case),
        documents=documents,
        uploaded=uploaded,
        checks=consistency_checks(
            answers,
            profile_full_name=owner.full_name if owner is not None else None,
            profile_passport_number=owner.passport_number if owner is not None else None,
            contact_email=str(contact_email) if contact_email else None,
        ),
    )


@router.get("/{case_id}/audit", response_model=CaseAudit)
async def get_case_audit(case_id: int, session: SessionDep, user: CurrentUserDep) -> CaseAudit:
    """One readiness report: route, intake, eligibility, documents, checks."""
    case = await _owned_case(session, case_id, user)
    return await _build_audit(session, case)


class AppointmentRequestIn(BaseModel):
    preferred_date: date
    preferred_time_window: str | None = Field(default=None, max_length=64)
    centre: str = Field(default=TASHEER_CENTRE_DEFAULT, min_length=1, max_length=256)
    notes: str | None = Field(default=None, max_length=2000)


class AppointmentConfirmIn(BaseModel):
    appointment_date: date
    appointment_time: str = Field(min_length=1, max_length=32)
    centre: str = Field(default=TASHEER_CENTRE_DEFAULT, min_length=1, max_length=256)
    reference: str = Field(min_length=1, max_length=128)


class AppointmentOut(BaseModel):
    id: int | None = None
    case_id: int
    status: str  # "none" | "requested" | "booked"
    centre: str | None = None
    preferred_date: date | None = None
    preferred_time_window: str | None = None
    appointment_date: date | None = None
    appointment_time: str | None = None
    reference: str | None = None
    notes: str | None = None
    booking_url: str = TASHEER_BOOKING_URL
    prefill: dict[str, Any] = Field(default_factory=dict)
    instructions: list[AuditStep] = Field(default_factory=list)


OpsDep = Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.OPS))]


async def _appointment_route_or_400(session: AsyncSession, case: Case) -> str:
    """The appointment flow exists only for routes that file in person."""
    j_code, _v, _a, _label = await _scope_label(session, case)
    answers = dict(case.intake_answers or {})
    route = route_for_case(j_code, answers)
    if route is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "Visa-centre appointments are currently supported for Saudi Arabia cases only."
            ),
        )
    if route not in APPOINTMENT_ROUTES:
        raise HTTPException(
            status_code=400,
            detail=APPOINTMENT_BLOCK_MESSAGES.get(
                route, "This route does not file in person, so no appointment is available."
            ),
        )
    return route


async def _current_appointment(session: AsyncSession, case_id: int) -> CaseAppointment | None:
    """The case's active appointment: the booked one, else the latest request."""
    rows = (
        await session.scalars(
            select(CaseAppointment)
            .where(
                CaseAppointment.case_id == case_id,
                CaseAppointment.status.in_([AppointmentStatus.REQUESTED, AppointmentStatus.BOOKED]),
            )
            .order_by(CaseAppointment.id.desc())
        )
    ).all()
    for row in rows:
        if row.status == AppointmentStatus.BOOKED:
            return row
    return rows[0] if rows else None


async def _booked_appointment(session: AsyncSession, case_id: int) -> CaseAppointment | None:
    return (
        await session.scalars(
            select(CaseAppointment)
            .where(
                CaseAppointment.case_id == case_id,
                CaseAppointment.status == AppointmentStatus.BOOKED,
            )
            .order_by(CaseAppointment.id.desc())
        )
    ).first()


async def _appointment_out(
    session: AsyncSession, case: Case, appointment: CaseAppointment | None
) -> AppointmentOut:
    answers = dict(case.intake_answers or {})
    owner = await session.get(User, case.user_id) if case.user_id else None
    prefill: dict[str, Any] = {
        "full_name": answers.get("full_name") or (owner.full_name if owner else None),
        "passport_number": answers.get("passport_number")
        or (owner.passport_number if owner else None),
        "nationality": answers.get("nationality") or case.origin_country,
        "purpose_of_visit": answers.get("purpose_of_visit"),
        "preferred_date": (
            appointment.preferred_date.isoformat() if appointment is not None else None
        ),
    }
    route = route_for_case((await _scope_label(session, case))[0], answers)
    if appointment is None:
        return AppointmentOut(case_id=case.id, status="none", prefill=prefill)
    return AppointmentOut(
        id=appointment.id,
        case_id=case.id,
        status=appointment.status,
        centre=appointment.centre,
        preferred_date=appointment.preferred_date,
        preferred_time_window=appointment.preferred_time_window,
        appointment_date=appointment.appointment_date,
        appointment_time=appointment.appointment_time,
        reference=appointment.reference,
        notes=appointment.notes,
        prefill=prefill,
        instructions=build_instructions(route),
    )


def _audit_pdf_summary(audit: CaseAudit) -> dict[str, Any]:
    """Compact audit block for the printed dossier packet."""
    return {
        "overall": audit.overall,
        "summary": audit.summary,
        "eligibility_result": audit.eligibility.result if audit.eligibility else None,
        "checks": [
            {"key": check.key, "status": check.status, "message": check.message}
            for check in audit.checks
        ],
    }


def _appointment_pdf_dict(appointment: CaseAppointment) -> dict[str, Any]:
    return {
        "status": appointment.status,
        "appointment_date": (
            appointment.appointment_date.isoformat() if appointment.appointment_date else None
        ),
        "appointment_time": appointment.appointment_time,
        "centre": appointment.centre,
        "reference": appointment.reference,
    }


@router.post("/{case_id}/appointment/request", response_model=AppointmentOut)
async def request_case_appointment(
    case_id: int, payload: AppointmentRequestIn, session: SessionDep, user: CurrentUserDep
) -> AppointmentOut:
    """Record a preferred Tasheer slot for an in-person-route case.

    One active appointment per case: a new request supersedes a pending
    (not yet booked) one; a booked appointment must be resolved by ops
    before another request is taken.
    """
    case = await _owned_case(session, case_id, user)
    await _appointment_route_or_400(session, case)
    current = await _current_appointment(session, case.id)
    if current is not None and current.status == AppointmentStatus.BOOKED:
        raise HTTPException(
            status_code=400,
            detail=(
                "An appointment is already booked for this case "
                f"(reference {current.reference or 'n/a'}). Ask ops to change it "
                "on the Tasheer portal instead of requesting a new slot."
            ),
        )
    if current is not None:
        current.status = AppointmentStatus.SUPERSEDED
    appointment = CaseAppointment(
        case_id=case.id,
        status=AppointmentStatus.REQUESTED,
        centre=payload.centre,
        preferred_date=payload.preferred_date,
        preferred_time_window=payload.preferred_time_window,
        notes=payload.notes,
        requested_by=user.id,
    )
    session.add(appointment)
    await session.flush()
    return await _appointment_out(session, case, appointment)


@router.post("/{case_id}/appointment/confirm", response_model=AppointmentOut)
async def confirm_case_appointment(
    case_id: int, payload: AppointmentConfirmIn, session: SessionDep, user: OpsDep
) -> AppointmentOut:
    """Ops-only: record the slot actually booked on vc.tasheer.com.

    Torii does not book on the Tasheer site itself — ops complete the
    booking there and confirm it here with the centre-issued reference,
    which lands the appointment in the audit trail and the dossier.
    """
    case = await _owned_case(session, case_id, user)
    await _appointment_route_or_400(session, case)
    current = await _current_appointment(session, case.id)
    if current is None or current.status != AppointmentStatus.REQUESTED:
        raise HTTPException(
            status_code=400,
            detail="No appointment request is pending for this case — request one first.",
        )
    current.status = AppointmentStatus.BOOKED
    current.appointment_date = payload.appointment_date
    current.appointment_time = payload.appointment_time
    current.centre = payload.centre
    current.reference = payload.reference
    current.confirmed_by = user.id
    await session.flush()
    return await _appointment_out(session, case, current)


@router.get("/{case_id}/appointment", response_model=AppointmentOut)
async def get_case_appointment(
    case_id: int, session: SessionDep, user: CurrentUserDep
) -> AppointmentOut:
    case = await _owned_case(session, case_id, user)
    return await _appointment_out(session, case, await _current_appointment(session, case.id))


@router.get("/{case_id}/deadlines", response_model=dict[str, Any])
async def get_case_deadlines(
    case_id: int, session: SessionDep, user: CurrentUserDep
) -> dict[str, Any]:
    """Computed filing deadlines for a case (window open, online cut-off, grace period)."""
    from torii_api.api.cases import _scope_label
    from torii_api.services.deadlines import compute_deadlines

    case = await _owned_case(session, case_id, user)
    j_code, _, a_code, _ = await _scope_label(session, case)
    expiry = (case.intake_answers or {}).get("residence_card_expiry")
    if not expiry:
        return {
            "residence_expiry": None,
            "procedure": a_code or "",
            "jurisdiction": (j_code or "").upper(),
        }
    return compute_deadlines(
        str(expiry),
        (a_code or "").replace("_", "").lower(),
        jurisdiction=j_code,
    ).to_dict()


@router.post("/{case_id}/checklist/refresh", response_model=list[ChecklistItemOut])
async def refresh_checklist(
    case_id: int, session: SessionDep, user: CurrentUserDep
) -> list[CaseChecklistItem]:
    case = await _owned_case(session, case_id, user)
    items = await _effective_documents(session, case)
    if not items:
        raise HTTPException(
            status_code=404, detail="no document requirements available for this case scope"
        )
    old_items = {item.code: item for item in await _checklist(session, case.id)}
    await session.execute(delete(CaseChecklistItem).where(CaseChecklistItem.case_id == case.id))
    new_items: list[CaseChecklistItem] = []
    j_code, v_code, _, _ = await _scope_label(session, case)
    answers_ctx = dict(case.intake_answers or {})
    if case.origin_country:
        answers_ctx.setdefault("origin_country", case.origin_country.upper())
        answers_ctx.setdefault("nationality", case.origin_country.upper())
        answers_ctx.setdefault("passport_country", case.origin_country.upper())
    if case.residence_country:
        answers_ctx.setdefault("residence_country", case.residence_country.upper())
        answers_ctx.setdefault("current_residence_country", case.residence_country.upper())

    for item in visible_requirement_items(items, answers_ctx):
        old = old_items.get(item.code)
        doc_name = localized(item.name, case.locale) or item.code or "Document"
        how = localized(item.how_to_obtain, case.locale) if item.how_to_obtain else ""
        if not how:
            how = f"Obtain official {doc_name} from the issuing authority or institution."
        why = localized(item.why_required, case.locale) if item.why_required else ""
        if not why:
            why = "Required supporting document for your visa application dossier."
        specific_citation = resolve_official_citation(
            jurisdiction_code=j_code or "JP",
            visa_category=v_code or "",
            existing_citation=item.citation,
        )
        created = CaseChecklistItem(
            case_id=case.id,
            code=item.code,
            name=doc_name,
            how_to_obtain=how,
            why_required=why,
            is_required=item.is_required,
            status=old.status if old else "needed",
            citation=specific_citation,
            document_id=old.document_id if old else None,
        )
        session.add(created)
        new_items.append(created)
    required_needed = [item for item in new_items if item.is_required and item.status == "needed"]
    if new_items and not required_needed:
        new_status = next_status_for_phase("forms", case.status)
        if new_status is not None:
            case.status = new_status
    else:
        mid = next_status_for_phase("checklist", case.status)
        if mid is not None:
            case.status = mid
    await session.flush()
    return new_items


@router.get("/{case_id}/checklist", response_model=list[ChecklistItemOut])
async def get_checklist(
    case_id: int, session: SessionDep, user: CurrentUserDep
) -> list[CaseChecklistItem]:
    await _owned_case(session, case_id, user)
    return await _checklist(session, case_id)


@router.patch("/{case_id}/checklist/{item_id}", response_model=ChecklistItemOut)
async def patch_checklist_item(
    case_id: int,
    item_id: int,
    payload: ChecklistStatusIn,
    session: SessionDep,
    user: CurrentUserDep,
) -> CaseChecklistItem:
    case = await _owned_case(session, case_id, user)
    item = await session.scalar(
        select(CaseChecklistItem).where(
            CaseChecklistItem.id == item_id, CaseChecklistItem.case_id == case_id
        )
    )
    if item is None:
        raise HTTPException(status_code=404, detail=f"checklist item {item_id} not found")
    item.status = update_status(item.status, payload.status)
    items = await _checklist(session, case_id)
    required_needed = [i for i in items if i.is_required and i.status == "needed"]
    if items and not required_needed:
        new_status = next_status_for_phase("forms", case.status)
        if new_status is not None:
            case.status = new_status
    await session.flush()
    return item


def _normalize_extracted_key(key: str) -> str:
    import re

    cleaned = re.sub(r"^[\d\.\s\-_]+", "", key.strip())
    jp_map = {
        "国籍": "nationality",
        "氏名": "full_name",
        "名前": "full_name",
        "生年月日": "date_of_birth",
        "性別": "sex",
        "住居地": "current_japan_address",
        "住所": "current_japan_address",
        "在留カード番号": "residence_card_number",
        "在留期間の満了の日": "current_status_expiry_date",
        "在留資格": "current_status_of_residence",
        "旅券番号": "passport_number",
        "有効期限": "passport_expiry",
    }
    for jp_label, mapped in jp_map.items():
        if jp_label in cleaned:
            return mapped
    return cleaned.lower().replace(" ", "_").replace("-", "_")


def _apply_extracted_fields_to_case_and_user(
    case: Case | None, user: User, extracted_fields: dict[str, Any]
) -> None:
    if not extracted_fields:
        return
    answers = dict(case.intake_answers or {}) if case is not None else {}
    for key, raw_val in extracted_fields.items():
        val = raw_val.get("value") if isinstance(raw_val, dict) else raw_val
        if val is None:
            continue
        val_str = str(val).strip()
        if not val_str:
            continue

        canonical_key = _normalize_extracted_key(key)
        answers[canonical_key] = val_str
        norm_key = canonical_key.lower().strip()

        # Update User global profile and intake aliases
        if norm_key in (
            "full_name",
            "applicant_name",
            "name",
            "legal_name",
            "holder_name",
            "employee_name",
        ):
            clean_name = val_str.splitlines()[0].strip()
            user.full_name = clean_name
            answers["full_name"] = clean_name
            answers["applicant_name"] = clean_name
        elif norm_key in (
            "nationality",
            "citizenship",
            "country_of_citizenship",
            "country_of_nationality",
        ):
            from torii_api.services.ocr_extractor import extract_country_from_text

            clean_nat = extract_country_from_text(val_str)
            user.nationality = clean_nat
            answers["nationality"] = clean_nat
            answers["citizenship"] = clean_nat
        elif norm_key in ("passport_number", "passport_no", "passport_num"):
            clean_p = val_str.upper()
            if (
                clean_p not in {"PASSPORT", "PASSEPORT", "DOCUMENT", "NULL", "NONE", "JAPAN"}
                and any(c.isdigit() for c in clean_p)
                and len(clean_p) >= 6
            ):
                user.passport_number = val_str
                answers["passport_number"] = val_str
        elif norm_key in (
            "passport_expiry",
            "passport_expiry_date",
            "expiry_date",
            "passport_expiration_date",
        ):
            from torii_api.services.ocr_extractor import normalize_date_to_iso

            iso_exp = normalize_date_to_iso(val_str)
            user.passport_expiry = iso_exp
            answers["passport_expiry"] = iso_exp
        elif norm_key in ("date_of_birth", "dob", "birth_date", "applicant_dob"):
            from torii_api.services.ocr_extractor import normalize_date_to_iso

            iso_dob = normalize_date_to_iso(val_str)
            user.date_of_birth = iso_dob
            answers["date_of_birth"] = iso_dob
        elif norm_key in (
            "current_country",
            "current_residence_country",
            "residence_country",
            "current_location_country",
            "current_residence",
            "current_residing",
        ):
            from torii_api.services.ocr_extractor import extract_country_from_text

            ctry = extract_country_from_text(val_str)
            user.current_country = ctry
            answers["current_country"] = ctry
            answers["current_location_country"] = ctry
            answers["current_residence_country"] = ctry
            answers["residence_country"] = ctry
        elif norm_key in ("sex", "gender"):
            s_val = val_str.strip().lower()
            norm_s = (
                "male"
                if s_val in ("male", "m")
                else "female"
                if s_val in ("female", "f")
                else s_val
            )
            answers["sex"] = norm_s
            answers["gender"] = norm_s
        elif norm_key in ("marital_status", "marital"):
            answers["marital_status"] = val_str.strip().lower()
        elif norm_key in ("occupation", "profession"):
            answers["occupation"] = val_str
        elif norm_key in ("phone_number", "phone", "mobile_number", "mobile", "contact_number"):
            answers["phone_number"] = val_str
        elif norm_key in ("employer_name", "company_name", "sponsor_name"):
            answers["employer_name"] = val_str
            answers["company_name"] = val_str
            answers["sponsor_name"] = val_str
        elif norm_key in ("monthly_salary", "remuneration", "salary"):
            answers["monthly_salary"] = val_str
        elif norm_key in ("residence_card_number", "card_number", "zairyu_card_number"):
            clean_rc = val_str.upper()
            if (
                clean_rc not in {"RESIDENCE", "ENGINEER", "MINISTRY", "NULL", "NONE"}
                and any(c.isdigit() for c in clean_rc)
                and len(clean_rc) >= 8
            ):
                answers["residence_card_number"] = val_str
        elif norm_key in (
            "status_of_residence",
            "current_status_of_residence",
            "visa_status",
            "residence_status",
        ):
            answers["status_of_residence"] = val_str
            answers["current_status_of_residence"] = val_str
        elif norm_key in ("current_status_expiry_date", "residence_expiry_date"):
            answers["current_status_expiry_date"] = val_str
        elif norm_key in ("current_japan_address", "japan_address", "address", "residence_address"):
            answers["current_japan_address"] = val_str
            answers["address"] = val_str
        elif norm_key in ("bank_name", "financial_institution", "bank"):
            answers["bank_name"] = val_str
        elif norm_key in ("account_number", "bank_account_number"):
            answers["account_number"] = val_str
        elif norm_key in (
            "balance",
            "current_balance",
            "available_balance",
            "proof_of_funds",
            "funds_amount",
        ):
            answers["balance"] = val_str
            answers["proof_of_funds"] = val_str
        elif norm_key in ("account_holder", "account_name"):
            answers["account_holder"] = val_str
        elif norm_key in ("annual_income", "gross_income", "gross_salary", "total_income"):
            answers["annual_income"] = val_str
            answers["gross_income"] = val_str
        elif norm_key in ("taxable_income", "taxable_amount"):
            answers["taxable_income"] = val_str
        elif norm_key in ("tax_paid", "paid_tax", "income_tax_paid"):
            answers["tax_paid"] = val_str
        elif norm_key in ("tax_year", "assessment_year"):
            answers["tax_year"] = val_str
        elif norm_key in ("position", "job_title", "designation"):
            answers["position"] = val_str
            answers["job_title"] = val_str
        elif norm_key in ("departure_date",):
            answers["departure_date"] = val_str
        elif norm_key in ("issuing_country", "passport_issuing_country"):
            answers["issuing_country"] = val_str

    if case is not None:
        case.intake_answers = answers
        case.review_flags_acknowledged = False

    user.profile_complete = bool(
        user.full_name and user.nationality and user.passport_number and user.current_country
    )


@router.post(
    "/{case_id}/documents", response_model=DocumentOut, status_code=status.HTTP_201_CREATED
)
async def register_document(
    case_id: int, payload: DocumentIn, session: SessionDep, user: CurrentUserDep
) -> CaseDocument:
    case = await _owned_case(session, case_id, user)
    has_extracted = bool(payload.extracted_fields)
    data = payload.model_dump()
    checklist_item_id = data.pop("checklist_item_id", None)
    document = CaseDocument(case_id=case.id, confirmed=has_extracted, **data)
    session.add(document)
    await session.flush()

    checklist_item = None
    if checklist_item_id is not None:
        checklist_item = await session.scalar(
            select(CaseChecklistItem).where(
                CaseChecklistItem.case_id == case.id, CaseChecklistItem.id == checklist_item_id
            )
        )
    if checklist_item is None:
        checklist_item = await session.scalar(
            select(CaseChecklistItem).where(
                CaseChecklistItem.case_id == case.id, CaseChecklistItem.code == payload.doc_type
            )
        )
    if checklist_item is not None:
        checklist_item.document_id = document.id
        checklist_item.status = "uploaded"

    if payload.extracted_fields:
        _apply_extracted_fields_to_case_and_user(case, user, payload.extracted_fields)

    await session.flush()
    return document


@router.post("/{case_id}/documents/{doc_id}/confirm", response_model=DocumentOut)
async def confirm_document(
    case_id: int, doc_id: int, session: SessionDep, user: CurrentUserDep
) -> CaseDocument:
    case = await _owned_case(session, case_id, user)
    document = await session.scalar(
        select(CaseDocument).where(CaseDocument.id == doc_id, CaseDocument.case_id == case.id)
    )
    if document is None:
        raise HTTPException(status_code=404, detail=f"document {doc_id} not found")

    if document.extracted_fields:
        _apply_extracted_fields_to_case_and_user(case, user, dict(document.extracted_fields))

    document.confirmed = True
    await session.flush()
    return document


@router.get("/{case_id}/documents", response_model=list[DocumentOut])
async def get_documents(
    case_id: int, session: SessionDep, user: CurrentUserDep
) -> list[CaseDocument]:
    await _owned_case(session, case_id, user)
    return await _documents(session, case_id)


async def _stream_case_document_file(
    session: AsyncSession,
    case: Case,
    doc: CaseDocument | None,
    doc_type: str,
    fallback_filename: str = "document.pdf",
) -> Response:
    from torii_api.db.models import DocumentWalletItem
    from torii_api.services.dummy_generator import generate_dummy_pdf
    from torii_api.services.wallet import get_document_content, save_document_content

    filename = (doc.filename if doc and doc.filename else fallback_filename).strip()
    storage_key = doc.storage_key if doc else None
    content: bytes | None = None

    if storage_key:
        content = get_document_content(storage_key)
        if not content and storage_key.startswith("wallet/"):
            try:
                wallet_id = int(storage_key.split("/", 1)[1])
                w_item = await session.scalar(
                    select(DocumentWalletItem).where(DocumentWalletItem.id == wallet_id)
                )
                if w_item and w_item.storage_key:
                    content = get_document_content(w_item.storage_key)
                    if w_item.filename:
                        filename = w_item.filename
            except Exception:
                pass

    if not content and case.user_id:
        w_item = await session.scalar(
            select(DocumentWalletItem)
            .where(
                DocumentWalletItem.user_id == case.user_id,
                DocumentWalletItem.doc_type == doc_type,
            )
            .order_by(DocumentWalletItem.id.desc())
        )
        if w_item and w_item.storage_key:
            content = get_document_content(w_item.storage_key)
            if w_item.filename:
                filename = w_item.filename

    if not content:
        answers = case.intake_answers or {}
        applicant_name = (
            answers.get("full_name")
            or answers.get("given_names")
            or answers.get("applicant_name")
            or (case.applicant_email or "Applicant").split("@")[0].capitalize()
        )
        try:
            content, gen_filename, _ = generate_dummy_pdf(doc_type, str(applicant_name))
            if not filename or filename == "document.pdf":
                filename = gen_filename
            if storage_key:
                try:
                    save_document_content(storage_key, content)
                except Exception:
                    pass
        except Exception:
            content = b"%PDF-1.4\n1 0 obj\n<< /Title (Document) >>\nendobj\ntrailer\n<< >>\n%%EOF\n"

    media_type = "application/pdf"
    lower_name = filename.lower()
    if lower_name.endswith(".png"):
        media_type = "image/png"
    elif lower_name.endswith((".jpg", ".jpeg")):
        media_type = "image/jpeg"
    elif lower_name.endswith(".webp"):
        media_type = "image/webp"
    elif doc and doc.content_type:
        media_type = doc.content_type

    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Cache-Control": "public, max-age=3600",
        },
    )


@router.get("/{case_id}/documents/{doc_id}/file")
async def get_case_document_file(
    case_id: int,
    doc_id: int,
    session: SessionDep,
    token: str | None = None,
    authorization: str | None = Header(default=None),
) -> Response:
    """Stream raw case document file for inline viewing or download."""
    auth_token = token
    if not auth_token and authorization and authorization.startswith("Bearer "):
        auth_token = authorization.replace("Bearer ", "").strip()
    if not auth_token:
        raise HTTPException(status_code=401, detail="Authentication token required")

    settings = get_settings()
    try:
        from torii_api.auth.security import decode_access_token

        claims = decode_access_token(auth_token, settings)
        user_id = int(claims["sub"])
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid auth token: {e}") from e

    user = await session.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    case = await _owned_case(session, case_id, user)
    doc = await session.scalar(
        select(CaseDocument).where(CaseDocument.id == doc_id, CaseDocument.case_id == case.id)
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    return await _stream_case_document_file(session, case, doc, doc.doc_type, doc.filename)


@router.get("/{case_id}/checklist/{item_id}/file")
async def get_checklist_item_file(
    case_id: int,
    item_id: int,
    session: SessionDep,
    token: str | None = None,
    authorization: str | None = Header(default=None),
) -> Response:
    """Stream file associated with a checklist item for inline viewing or download."""
    auth_token = token
    if not auth_token and authorization and authorization.startswith("Bearer "):
        auth_token = authorization.replace("Bearer ", "").strip()
    if not auth_token:
        raise HTTPException(status_code=401, detail="Authentication token required")

    settings = get_settings()
    try:
        from torii_api.auth.security import decode_access_token

        claims = decode_access_token(auth_token, settings)
        user_id = int(claims["sub"])
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid auth token: {e}") from e

    user = await session.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    case = await _owned_case(session, case_id, user)
    item = await session.scalar(
        select(CaseChecklistItem).where(
            CaseChecklistItem.id == item_id, CaseChecklistItem.case_id == case.id
        )
    )
    if not item:
        raise HTTPException(status_code=404, detail="Checklist item not found")

    doc: CaseDocument | None = None
    if item.document_id:
        doc = await session.scalar(
            select(CaseDocument).where(
                CaseDocument.id == item.document_id, CaseDocument.case_id == case.id
            )
        )
    if not doc:
        doc = await session.scalar(
            select(CaseDocument)
            .where(CaseDocument.case_id == case.id, CaseDocument.doc_type == item.code)
            .order_by(CaseDocument.id.desc())
        )

    return await _stream_case_document_file(session, case, doc, item.code, f"{item.code}.pdf")


class MedicalValidationIn(BaseModel):
    passport_ocr: dict[str, Any] | None = None
    hospital_letter_ocr: dict[str, Any] | None = None


class DocumentAlertOut(BaseModel):
    severity: str
    field: str
    message: str


class MedicalValidationOut(BaseModel):
    is_valid: bool
    alerts: list[DocumentAlertOut]
    error_count: int
    warning_count: int


@router.post("/{case_id}/validate-medical", response_model=MedicalValidationOut)
async def validate_medical_case_documents(
    case_id: int,
    session: SessionDep,
    user: CurrentUserDep,
    payload: MedicalValidationIn | None = None,
) -> MedicalValidationOut:
    """Cross-validate uploaded medical documents against intake answers."""
    case = await _owned_case(session, case_id, user)
    docs = await _documents(session, case_id)

    passport_ocr = payload.passport_ocr if payload and payload.passport_ocr else None
    hospital_letter_ocr = (
        payload.hospital_letter_ocr if payload and payload.hospital_letter_ocr else None
    )

    if passport_ocr is None or hospital_letter_ocr is None:
        for doc in docs:
            fields = dict(doc.extracted_fields or {})
            if not fields:
                continue
            doc_type = (doc.doc_type or "").lower()
            if passport_ocr is None and ("passport" in doc_type):
                passport_ocr = fields
            elif hospital_letter_ocr is None and (
                "hospital" in doc_type or "medical" in doc_type or "invitation" in doc_type
            ):
                hospital_letter_ocr = fields

    from torii_api.services.medical_visa_validation import validate_medical_visa_documents

    alerts = validate_medical_visa_documents(
        passport_ocr=passport_ocr or {},
        hospital_letter_ocr=hospital_letter_ocr or {},
        intake_answers=dict(case.intake_answers or {}),
    )
    errors = [a for a in alerts if a.get("severity") == "error"]
    warnings = [a for a in alerts if a.get("severity") == "warning"]
    return MedicalValidationOut(
        is_valid=len(errors) == 0,
        alerts=[DocumentAlertOut(**a) for a in alerts],
        error_count=len(errors),
        warning_count=len(warnings),
    )


@router.post("/{case_id}/forms/generate", response_model=list[GeneratedFormOut])
async def generate_forms(
    case_id: int, session: SessionDep, user: CurrentUserDep
) -> list[dict[str, Any]]:
    case = await _owned_case(session, case_id, user)
    templates = await _effective_templates(session, case)
    answers = dict(case.intake_answers or {})
    # When research/live packs have no form templates, synthesize a summary form
    # from intake answers so generate never hard-fails an otherwise ready case.
    if not templates:
        if not answers:
            raise HTTPException(
                status_code=400,
                detail="no form templates available and intake answers are empty",
            )
        mappings = [{"form_field": key, "answer_key": key, "required": False} for key in answers]
        templates = [
            _FormDescriptor(
                code="application_summary",
                version="auto",
                official_title="Application summary (auto-filled)",
                citation={
                    "authority": "Torii",
                    "title": "Synthesized from intake",
                    "source_version": "auto",
                },
                field_mappings=mappings,
                research_id=case.research_id,
            )
        ]
    await session.execute(delete(CaseGeneratedForm).where(CaseGeneratedForm.case_id == case.id))
    generated: list[CaseGeneratedForm] = []
    for template in templates:
        filled = fill_form(template.field_mappings, answers)
        form = CaseGeneratedForm(
            case_id=case.id,
            form_template_id=template.template_id,
            research_id=template.research_id or case.research_id,
            form_code=(template.code or "form")[:64],
            form_version=(template.version or "1")[:32],
            filled_fields=filled.filled_fields,
            missing_required_fields=filled.missing_required_fields,
            citation=dict(template.citation or {}),
        )
        session.add(form)
        generated.append(form)
    case.review_flags_acknowledged = False
    new_status = next_status_for_phase("review", case.status)
    if new_status is not None:
        case.status = new_status
    await session.flush()
    return await _forms_with_titles(session, case)


async def _forms_with_titles(session: AsyncSession, case: Case) -> list[dict[str, Any]]:
    """Generated forms, each carrying the official title of the template behind it."""
    titles = {
        descriptor.code: descriptor.official_title
        for descriptor in await _effective_templates(session, case)
    }
    out: list[dict[str, Any]] = []
    for row in await _forms(session, case.id):
        item = GeneratedFormOut.model_validate(row).model_dump(mode="json")
        item["official_title"] = titles.get(row.form_code)
        out.append(item)
    return out


@router.get("/{case_id}/forms", response_model=list[GeneratedFormOut])
async def get_forms(
    case_id: int, session: SessionDep, user: CurrentUserDep
) -> list[dict[str, Any]]:
    case = await _owned_case(session, case_id, user)
    return await _forms_with_titles(session, case)


@router.post("/{case_id}/review", response_model=ReviewResult)
async def review_case(case_id: int, session: SessionDep, user: CurrentUserDep) -> ReviewResult:
    case = await _owned_case(session, case_id, user)
    result = await _review(session, case)
    if result.ready:
        case.review_flags_acknowledged = True
        await session.flush()
    return result


@router.post("/{case_id}/review/acknowledge")
async def acknowledge_review(
    case_id: int, session: SessionDep, user: CurrentUserDep
) -> dict[str, bool]:
    case = await _owned_case(session, case_id, user)
    case.review_flags_acknowledged = True
    await session.flush()
    return {"review_flags_acknowledged": True}


@router.post("/{case_id}/packet")
async def build_packet(case_id: int, session: SessionDep, user: CurrentUserDep) -> dict[str, Any]:
    case = await _owned_case(session, case_id, user)
    review = await _review(session, case)
    if review.flags and not case.review_flags_acknowledged:
        raise HTTPException(
            status_code=400,
            detail="review flags must be acknowledged before packet assembly",
        )
    forms = [
        GeneratedFormOut.model_validate(item).model_dump(mode="json")
        for item in await _forms(session, case.id)
    ]
    checklist = [
        ChecklistItemOut.model_validate(item).model_dump(mode="json")
        for item in await _checklist(session, case.id)
    ]
    j_code, v_code, a_code, scope_label = await _scope_label(session, case)
    snapshot = assemble_packet(
        case.reference,
        forms,
        checklist,
        case.submission_reference,
        jurisdiction_code=j_code,
        scope_label=scope_label,
        visa_category=v_code,
        action=a_code,
    )
    case.packet_snapshot = snapshot
    if case.status != "submitted":
        case.status = "packet_ready"
    await session.flush()
    return snapshot


@router.get("/{case_id}/packet")
async def get_packet(case_id: int, session: SessionDep, user: CurrentUserDep) -> dict[str, Any]:
    case = await _owned_case(session, case_id, user)
    if get_settings().require_packet_entitlement:
        entitled = (
            case.is_entitled
            or case.status == "submitted"
            or await case_has_packet_entitlement(session, case.id, user.id)
        )
        if not entitled:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="packet download requires a completed payment entitlement",
            )
    if case.packet_snapshot is None:
        forms = [
            GeneratedFormOut.model_validate(item).model_dump(mode="json")
            for item in await _forms(session, case.id)
        ]
        checklist = [
            ChecklistItemOut.model_validate(item).model_dump(mode="json")
            for item in await _checklist(session, case.id)
        ]
        j_code, v_code, a_code, scope_label = await _scope_label(session, case)
        snapshot = assemble_packet(
            case.reference,
            forms,
            checklist,
            case.submission_reference,
            jurisdiction_code=j_code,
            scope_label=scope_label,
            visa_category=v_code,
            action=a_code,
        )
        case.packet_snapshot = snapshot
        if case.status != "submitted":
            case.status = "packet_ready"
        await session.flush()
    return case.packet_snapshot


async def _submission_kit(session: AsyncSession, case: Case) -> Any | None:
    """Filing instructions for this case's application type, or ``None`` if not modelled.

    Fees come from the scope's own content pack so only published figures with a citation
    reach the applicant (NF-2).
    """
    j_code, v_code, a_code, _label = await _scope_label(session, case)
    fees: list[Any] = []
    if j_code and v_code and a_code:
        action = "new_application" if a_code == "new" else a_code
        try:
            fees = list(load_pack_by_scope(f"{j_code.lower()}/{v_code}.{action}").fees)
        except (KeyError, FileNotFoundError):
            fees = []
    checklist = [
        ChecklistItemOut.model_validate(item).model_dump(mode="json")
        for item in await _checklist(session, case.id)
    ]
    authored = build_submission_kit(
        jurisdiction_code=j_code,
        visa_category=v_code,
        action=a_code,
        checklist=checklist,
        fees=fees,
    )

    # Research wins where it exists, because the filing route is corridor-specific: Japan's
    # own pages tell a Bangladeshi applicant to file through an accredited agency and quote
    # the fee in taka, neither of which follows from the destination alone. The authored
    # per-procedure facts stay as the fallback for a corridor nobody has researched yet.
    admissibility = await _admissibility_research(session, case)
    if admissibility is not None:
        researched = kit_from_research(
            admissibility.payload or {}, fallback=authored, checklist=checklist
        )
        if researched is not None:
            return researched
    return authored


async def _admissibility_research(session: AsyncSession, case: Case) -> Any | None:
    """The corridor's admissibility research, if a usable one has been cached."""
    j_code, v_code, a_code, _label = await _scope_label(session, case)
    if not (j_code and v_code and a_code):
        return None
    key = scope_key(
        destination_code=j_code,
        purpose_code=v_code,
        action_code=a_code,
        nationality=case.origin_country,
        residence_country=case.residence_country,
    )
    research = await find_admissibility(session, key)
    return research if stage_is_usable(research) else None


def _jurisdiction_meta(jurisdiction_code: str | None) -> Any:
    """Pack metadata for a jurisdiction, or ``None`` when it has no pack."""
    if not jurisdiction_code:
        return None
    try:
        return load_jurisdiction_meta(jurisdiction_code)
    except (FileNotFoundError, ValueError):
        return None


def _filing_mode(jurisdiction_code: str | None) -> str:
    """How this country is filed with — declared in its ``_jurisdiction.yml``."""
    meta = _jurisdiction_meta(jurisdiction_code)
    return getattr(meta, "filing_mode", "official_form_pdf") if meta else "official_form_pdf"


def _apply_url(jurisdiction_code: str | None) -> str | None:
    meta = _jurisdiction_meta(jurisdiction_code)
    return getattr(meta, "apply_url", None) if meta else None


def _photo_bytes(photo_data: Any) -> bytes | None:
    """Decode whatever the case is carrying as a photo (data URL, base64, raw bytes)."""
    from torii_api.services.pdf_generator import _extract_image_bytes

    return _extract_image_bytes(photo_data)


def _pdf_response(
    content: bytes,
    filename: str,
    request: Request,
    response_format: str | None,
    metadata: dict[str, Any] | None = None,
) -> Response:
    """Serve a PDF, as a download or as the base64 envelope the web client asks for."""
    wants_json = response_format in ("base64", "json") or "application/json" in request.headers.get(
        "accept", ""
    )
    if wants_json:
        payload: dict[str, Any] = {
            "filename": filename,
            "media_type": "application/pdf",
            "data_base64": base64.b64encode(content).decode("ascii"),
            "size_bytes": len(content),
        }
        if metadata is not None:
            payload["form"] = metadata
        return JSONResponse(content=payload)
    return Response(
        content=content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(content)),
        },
    )


@router.get("/{case_id}/export/application-form")
@router.get("/{case_id}/pdf/application-form")
async def download_application_form_pdf(
    case_id: int,
    session: SessionDep,
    user: CurrentUserDep,
    request: Request,
    format: str | None = Query(default=None),
) -> Response:
    from torii_api.services.pdf_generator import (
        generate_generic_visa_application_pdf,
        generate_japan_work_renewal_pdf,
        generate_official_japan_visa_form_pdf,
        generate_portal_application_pack_pdf,
        generate_uk_visa_application_pdf,
    )

    case = await _owned_case(session, case_id, user)
    answers = dict(case.intake_answers or {})
    j_code, v_code, a_code, scope_label = await _scope_label(session, case)
    j_code_upper = (j_code or (case.reference.split("-")[0] if case.reference else "JP")).upper()

    photo_data = (
        user.avatar_url
        or answers.get("photo")
        or answers.get("applicant_photo")
        or answers.get("passport_photo")
    )

    safe_ref = "".join(
        c for c in (case.reference or f"CASE-{case.id}") if c.isalnum() or c in ("-", "_", ".")
    )
    filename = f"{safe_ref or f'Case-{case_id}'}_Application_Form.pdf"

    if j_code_upper == "JP":
        # Japan issues a different statutory sheet per (residence status, procedure).
        # Resolve and fill that exact form; only fall back when it cannot be obtained.
        rendered = await render_primary_form(
            v_code or "",
            a_code or "",
            answers,
            reference=case.reference,
            case_id=case.id,
            photo=_photo_bytes(photo_data),
            applicant_email=case.applicant_email or user.email,
            scope_label=scope_label or "Japan",
        )
        if rendered is not None:
            return _pdf_response(rendered.content, rendered.filename, request, format)

    if _filing_mode(j_code) == "online_portal":
        # Nothing is submitted on paper for this jurisdiction, so a document styled as an
        # application form would misrepresent the process. Give the applicant their
        # answers in the order the online service asks for them instead.
        templates = await _effective_templates(session, case)
        pdf_bytes = generate_portal_application_pack_pdf(
            case.reference or f"CASE-{case.id}",
            answers,
            [
                {
                    "code": descriptor.code,
                    "citation": descriptor.citation,
                    "field_mappings": descriptor.field_mappings,
                }
                for descriptor in templates
            ],
            jurisdiction=j_code_upper,
            scope_label=scope_label or j_code_upper,
            apply_url=_apply_url(j_code),
        )
        filename = f"{safe_ref or f'Case-{case_id}'}_Online_Application_Pack.pdf"
        return _pdf_response(pdf_bytes, filename, request, format)

    if j_code_upper in ("UK", "GB"):
        pdf_bytes = generate_uk_visa_application_pdf(
            case.reference or f"UK-{case.id}",
            answers,
            destination_label=scope_label or "United Kingdom",
            applicant_email=case.applicant_email or user.email,
            photo_data=photo_data,
        )
    elif j_code_upper == "JP":
        if a_code == "new_application" or (
            v_code == "tourist" and a_code not in ("renewal", "change_of_status")
        ):
            pdf_bytes = generate_official_japan_visa_form_pdf(
                case.reference or f"JP-{case.id}",
                answers,
                destination_label=scope_label or "Japan",
                applicant_email=case.applicant_email or user.email,
                photo_data=photo_data,
            )
        else:
            pdf_bytes = generate_japan_work_renewal_pdf(
                case.reference or f"JP-{case.id}",
                answers,
                destination_label=scope_label or "Japan",
                photo_data=photo_data,
                action_code=a_code,
            )
    else:
        pdf_bytes = generate_generic_visa_application_pdf(
            case.reference or f"CASE-{case.id}",
            answers,
            destination_label=scope_label or "Visa Application",
            applicant_email=case.applicant_email or user.email,
            photo_data=photo_data,
        )

    return _pdf_response(pdf_bytes, filename, request, format)


@router.get("/{case_id}/filing")
async def get_filing_mode(
    case_id: int, session: SessionDep, user: CurrentUserDep
) -> dict[str, Any]:
    """How this case is filed, and the pack that goes with it.

    ``official_form_pdf`` means the government publishes a form to fill in and hand over.
    ``online_portal`` means there is nothing to submit on paper — the answer pack is what
    the applicant works from while completing the government's own website.
    """
    case = await _owned_case(session, case_id, user)
    answers = dict(case.intake_answers or {})
    j_code, _v_code, _a_code, scope_label = await _scope_label(session, case)
    mode = _filing_mode(j_code)
    payload: dict[str, Any] = {
        "case_id": case.id,
        "jurisdiction": j_code,
        "scope_label": scope_label,
        "filing_mode": mode,
        "apply_url": _apply_url(j_code),
    }
    if mode == "online_portal":
        templates = await _effective_templates(session, case)
        pack = build_portal_pack(
            [
                {
                    "code": descriptor.code,
                    "citation": descriptor.citation,
                    "field_mappings": descriptor.field_mappings,
                }
                for descriptor in templates
            ],
            answers,
            jurisdiction=(j_code or "").upper(),
            scope_label=scope_label or (j_code or ""),
            apply_url=_apply_url(j_code),
        )
        payload["portal_pack"] = pack.as_dict()
    return payload


@router.get("/{case_id}/official-forms")
async def get_official_forms(
    case_id: int, session: SessionDep, user: CurrentUserDep
) -> dict[str, Any]:
    """Which official government forms this application type requires, and their state.

    Lets the applicant see the exact sheet — form series, issuing ministry, source page —
    before downloading it, and which of their answers each one is still waiting on.
    """
    case = await _owned_case(session, case_id, user)
    answers = dict(case.intake_answers or {})
    j_code, v_code, a_code, scope_label = await _scope_label(session, case)
    if (j_code or "").upper() != "JP":
        return {"jurisdiction": j_code, "scope_label": scope_label, "forms": []}
    return {
        "jurisdiction": "JP",
        "visa_category": v_code,
        "action": a_code,
        "scope_label": scope_label,
        "forms": describe_scope_forms(v_code or "", a_code or "", answers),
    }


@router.get("/{case_id}/export/official-form/{form_code}")
async def download_official_form_pdf(
    case_id: int,
    form_code: str,
    session: SessionDep,
    user: CurrentUserDep,
    request: Request,
    format: str | None = Query(default=None),
) -> Response:
    """Download one specific official form for the case, filled from its intake answers."""
    case = await _owned_case(session, case_id, user)
    answers = dict(case.intake_answers or {})
    _j_code, v_code, a_code, scope_label = await _scope_label(session, case)

    form = next(
        (item for item in forms_for_scope(v_code or "", a_code or "") if item.code == form_code),
        None,
    )
    if form is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"'{form_code}' is not an official form for this application type",
        )

    photo_data = (
        user.avatar_url
        or answers.get("photo")
        or answers.get("applicant_photo")
        or answers.get("passport_photo")
    )
    rendered = await render_form(
        form,
        answers,
        reference=case.reference,
        case_id=case.id,
        photo=_photo_bytes(photo_data),
        applicant_email=case.applicant_email or user.email,
        scope_label=scope_label or "Japan",
    )
    if rendered is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                f"the official template for '{form_code}' could not be retrieved from "
                f"{form.authority}; try again shortly"
            ),
        )
    return _pdf_response(rendered.content, rendered.filename, request, format, rendered.metadata)


@router.get("/{case_id}/export/cover-letter")
@router.get("/{case_id}/pdf/cover-letter")
async def download_cover_letter_pdf(
    case_id: int,
    session: SessionDep,
    user: CurrentUserDep,
    request: Request,
    format: str | None = Query(default=None),
) -> Response:
    from torii_api.services.pdf_generator import generate_cover_letter_pdf

    case = await _owned_case(session, case_id, user)
    answers = dict(case.intake_answers or {})
    checklist = [
        ChecklistItemOut.model_validate(item).model_dump(mode="json")
        for item in await _checklist(session, case.id)
    ]
    j_code, v_code, a_code, scope_label = await _scope_label(session, case)
    forms = [
        GeneratedFormOut.model_validate(item).model_dump(mode="json")
        for item in await _forms(session, case.id)
    ]
    safe_ref = "".join(
        c for c in (case.reference or f"CASE-{case.id}") if c.isalnum() or c in ("-", "_", ".")
    )
    filename = f"{safe_ref or f'Case-{case_id}'}_Cover_Letter.pdf"
    pdf_bytes = generate_cover_letter_pdf(
        case.reference or f"CASE-{case.id}",
        answers,
        checklist,
        scope_label=scope_label or "Visa Submission Dossier",
        submission_kit=await _submission_kit(session, case),
        forms=forms,
    )
    if format in ("base64", "json") or "application/json" in request.headers.get("accept", ""):
        return JSONResponse(
            content={
                "filename": filename,
                "media_type": "application/pdf",
                "data_base64": base64.b64encode(pdf_bytes).decode("ascii"),
                "size_bytes": len(pdf_bytes),
            }
        )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(pdf_bytes)),
        },
    )


@router.get("/{case_id}/export/filing-kit-zip")
@router.get("/{case_id}/export/filing-kit.zip")
async def download_filing_kit_zip(
    case_id: int,
    session: SessionDep,
    user: CurrentUserDep,
    request: Request,
    format: str | None = Query(default=None),
) -> Response:
    """Bundle the complete offline/consular dossier into a single ZIP archive.

    Includes:
    1. 00_ALL_IN_ONE_PRINT_READY_DOSSIER.pdf (Single merged PDF for 1-click printing)
    2. 01_Official_Embassy_Cover_Letter.pdf
    3. 02_Complete_Dossier_Packet.pdf
    4. 00_Filing_Instructions_ReadMe.txt
    5. Supporting_Documents/ folder with all uploaded files (passport, bank, photos, etc.)
    """
    import io
    import zipfile

    from torii_api.services.pdf_generator import (
        build_single_master_dossier_pdf,
        generate_cover_letter_pdf,
        generate_dossier_packet_pdf,
    )
    from torii_api.services.wallet import get_document_content

    case = await _owned_case(session, case_id, user)
    answers = dict(case.intake_answers or {})
    checklist_raw = await _checklist(session, case.id)
    checklist = [
        ChecklistItemOut.model_validate(item).model_dump(mode="json")
        for item in checklist_raw
    ]
    forms_raw = await _forms(session, case.id)
    forms = [
        GeneratedFormOut.model_validate(item).model_dump(mode="json")
        for item in forms_raw
    ]
    j_code, _v_code, _a_code, scope_label = await _scope_label(session, case)
    safe_ref = "".join(
        c for c in (case.reference or f"CASE-{case.id}") if c.isalnum() or c in ("-", "_", ".")
    )
    filename = f"{safe_ref or f'Case-{case_id}'}_Complete_Filing_Kit.zip"

    # 1. Generate Cover Letter PDF
    sub_kit = await _submission_kit(session, case)
    cover_pdf = generate_cover_letter_pdf(
        case.reference or f"CASE-{case.id}",
        answers,
        checklist,
        scope_label=scope_label or "Visa Submission Dossier",
        submission_kit=sub_kit,
        forms=forms,
    )

    # 2. Generate Complete Dossier Packet PDF
    audit_summary: dict[str, Any] | None = None
    if (j_code or "").upper() == "SA":
        audit_summary = _audit_pdf_summary(await _build_audit(session, case))
    booked = await _booked_appointment(session, case.id)
    dossier_pdf = generate_dossier_packet_pdf(
        case.reference or f"CASE-{case.id}",
        answers,
        forms,
        checklist,
        submission_kit=sub_kit,
        scope_label=scope_label or "Immigration Filing Dossier",
        audit_summary=audit_summary,
        appointment=_appointment_pdf_dict(booked) if booked is not None else None,
    )

    # 3. Fetch Case Documents
    docs_res = await session.execute(
        select(CaseDocument).where(CaseDocument.case_id == case.id)
    )
    case_docs = docs_res.scalars().all()

    # 4. Instructions README
    applicant_name = (
        answers.get("full_name")
        or answers.get("applicant_name")
        or user.full_name
        or "Applicant"
    )
    instructions = f"""================================================================================
OFFICIAL IMMIGRATION FILING KIT & DOSSIER
Case Reference : {case.reference or f'CASE-{case.id}'}
Applicant Name : {applicant_name}
Target Country : {j_code or 'Destination'}
Visa Track     : Consular / In-Person Appointment Kit
Generated by   : Torii Legal Tech Concierge
================================================================================

INSTRUCTIONS FOR YOUR EMBASSY / VFS GLOBAL / TASHEER APPOINTMENT:

1. HASSLE-FREE 1-CLICK PRINTING:
   - For your convenience, print '00_{safe_ref}_ALL_IN_ONE_PRINT_READY_DOSSIER.pdf'.
   - This single master PDF already merges your Cover Letter, Application Forms, and all supporting documents (Passports, Bank Statements, Photos) in exact statutory embassy submission order!
   - You can also find individual PDF and image files in this folder if needed.

2. SIGNING:
   - Review your typed particulars on 01_Official_Cover_Letter.pdf and application forms.
   - Sign and date where indicated using a dark blue or black ink ballpoint pen.

3. DOSSIER ORDER:
   Arrange your physical papers in the exact order below before attending your appointment:
   [1] Official Embassy Cover Letter (Signed)
   [2] Official Typed Government Application Form (Signed)
   [3] Appointment Slip & Consular Fee Payment Receipt
   [4] Original Valid Passport (and bio-data photocopies)
   [5] Passport-Sized Photographs (as per embassy dimensions)
   [6] Proof of Financial Solvency (Bank Statements, Solvency Letters)
   [7] Travel Itinerary / Accommodation Proof / Invitation Documents

4. APPOINTMENT DAY:
   - Bring your original passport with at least 6 months validity and 2 blank pages.
   - Pay the statutory consular/visa fee at the counter (cash or certified bank draft as required).
================================================================================
"""

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        # Cover Letter
        zip_file.writestr(f"01_{safe_ref}_Official_Cover_Letter.pdf", cover_pdf)
        # Complete Dossier
        zip_file.writestr(f"02_{safe_ref}_Complete_Dossier_Packet.pdf", dossier_pdf)
        # Instructions
        zip_file.writestr("00_Filing_Instructions_ReadMe.txt", instructions)

        # Supporting Documents Folder & collecting for Master PDF
        supporting_docs_for_master: list[tuple[str, bytes]] = []
        for i, doc in enumerate(case_docs, 1):
            try:
                doc_bytes = get_document_content(doc.storage_key)
                if doc_bytes:
                    clean_doc_name = "".join(
                        c for c in doc.filename if c.isalnum() or c in ("-", "_", ".")
                    ) or f"document_{i}.pdf"
                    zip_file.writestr(
                        f"Supporting_Documents/{i:02d}_{clean_doc_name}", doc_bytes
                    )
                    supporting_docs_for_master.append((clean_doc_name, doc_bytes))
            except Exception:
                pass

        # All-in-One Master Print-Ready PDF
        try:
            master_pdf_bytes = build_single_master_dossier_pdf(
                case.reference or f"CASE-{case.id}",
                cover_pdf,
                dossier_pdf,
                supporting_docs_for_master,
            )
            zip_file.writestr(
                f"00_{safe_ref}_ALL_IN_ONE_PRINT_READY_DOSSIER.pdf", master_pdf_bytes
            )
        except Exception:
            pass

    zip_bytes = buffer.getvalue()

    if format in ("base64", "json") or "application/json" in request.headers.get("accept", ""):
        return JSONResponse(
            content={
                "filename": filename,
                "media_type": "application/zip",
                "data_base64": base64.b64encode(zip_bytes).decode("ascii"),
                "size_bytes": len(zip_bytes),
            }
        )
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(zip_bytes)),
        },
    )


@router.get("/{case_id}/export/dossier-packet")
@router.get("/{case_id}/pdf/dossier-packet")
async def download_dossier_packet_pdf(
    case_id: int,
    session: SessionDep,
    user: CurrentUserDep,
    request: Request,
    format: str | None = Query(default=None),
) -> Response:
    from torii_api.services.pdf_generator import generate_dossier_packet_pdf

    case = await _owned_case(session, case_id, user)
    answers = dict(case.intake_answers or {})
    forms = [
        GeneratedFormOut.model_validate(item).model_dump(mode="json")
        for item in await _forms(session, case.id)
    ]
    checklist = [
        ChecklistItemOut.model_validate(item).model_dump(mode="json")
        for item in await _checklist(session, case.id)
    ]
    j_code, _v_code, _a_code, scope_label = await _scope_label(session, case)
    safe_ref = "".join(
        c for c in (case.reference or f"CASE-{case.id}") if c.isalnum() or c in ("-", "_", ".")
    )
    filename = f"{safe_ref or f'Case-{case_id}'}_Complete_Dossier_Packet.pdf"
    # Phase 3: the printed packet carries the readiness audit and the booked
    # Tasheer appointment for the in-person track. Saudi-scoped so other
    # jurisdictions' packets keep their existing structure; the appointment
    # block only exists for cases that can book one anyway.
    audit_summary: dict[str, Any] | None = None
    if (j_code or "").upper() == "SA":
        audit_summary = _audit_pdf_summary(await _build_audit(session, case))
    booked = await _booked_appointment(session, case.id)
    pdf_bytes = generate_dossier_packet_pdf(
        case.reference or f"CASE-{case.id}",
        answers,
        forms,
        checklist,
        submission_kit=await _submission_kit(session, case),
        scope_label=scope_label or "Immigration Filing Dossier",
        audit_summary=audit_summary,
        appointment=_appointment_pdf_dict(booked) if booked is not None else None,
    )
    if format in ("base64", "json") or "application/json" in request.headers.get("accept", ""):
        return JSONResponse(
            content={
                "filename": filename,
                "media_type": "application/pdf",
                "data_base64": base64.b64encode(pdf_bytes).decode("ascii"),
                "size_bytes": len(pdf_bytes),
            }
        )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(pdf_bytes)),
        },
    )


@router.get("/{case_id}/export/master-dossier-pdf")
@router.get("/{case_id}/pdf/master-dossier")
async def download_master_dossier_pdf(
    case_id: int,
    session: SessionDep,
    user: CurrentUserDep,
    request: Request,
    format: str | None = Query(default=None),
) -> Response:
    """Generate a single, unified, print-ready PDF containing the entire submission dossier.

    Arranged in strict embassy submission order:
    1. Official Signed Embassy Cover Letter
    2. Complete Application Dossier Packet / Official Forms
    3. Supporting Documents (passports, bank statements, photos, vouchers) normalized to clean A4 pages.
    """
    from torii_api.services.pdf_generator import (
        build_single_master_dossier_pdf,
        generate_cover_letter_pdf,
        generate_dossier_packet_pdf,
    )
    from torii_api.services.wallet import get_document_content

    case = await _owned_case(session, case_id, user)
    answers = dict(case.intake_answers or {})
    checklist_raw = await _checklist(session, case.id)
    checklist = [
        ChecklistItemOut.model_validate(item).model_dump(mode="json")
        for item in checklist_raw
    ]
    forms_raw = await _forms(session, case.id)
    forms = [
        GeneratedFormOut.model_validate(item).model_dump(mode="json")
        for item in forms_raw
    ]
    j_code, _v_code, _a_code, scope_label = await _scope_label(session, case)
    safe_ref = "".join(
        c for c in (case.reference or f"CASE-{case.id}") if c.isalnum() or c in ("-", "_", ".")
    )
    filename = f"{safe_ref or f'Case-{case_id}'}_Complete_Dossier_Print_Ready.pdf"

    # 1. Generate Cover Letter PDF
    sub_kit = await _submission_kit(session, case)
    cover_pdf = generate_cover_letter_pdf(
        case.reference or f"CASE-{case.id}",
        answers,
        checklist,
        scope_label=scope_label or "Visa Submission Dossier",
        submission_kit=sub_kit,
        forms=forms,
    )

    # 2. Generate Complete Dossier Packet PDF
    audit_summary: dict[str, Any] | None = None
    if (j_code or "").upper() == "SA":
        audit_summary = _audit_pdf_summary(await _build_audit(session, case))
    booked = await _booked_appointment(session, case.id)
    dossier_pdf = generate_dossier_packet_pdf(
        case.reference or f"CASE-{case.id}",
        answers,
        forms,
        checklist,
        submission_kit=sub_kit,
        scope_label=scope_label or "Immigration Filing Dossier",
        audit_summary=audit_summary,
        appointment=_appointment_pdf_dict(booked) if booked is not None else None,
    )

    # 3. Supporting Documents
    docs_res = await session.execute(
        select(CaseDocument).where(CaseDocument.case_id == case.id)
    )
    case_docs = docs_res.scalars().all()
    supporting_docs: list[tuple[str, bytes]] = []
    for i, doc in enumerate(case_docs, 1):
        try:
            doc_bytes = get_document_content(doc.storage_key)
            if doc_bytes:
                clean_name = doc.filename or f"Document_{i}"
                supporting_docs.append((clean_name, doc_bytes))
        except Exception:
            pass

    master_pdf = build_single_master_dossier_pdf(
        case.reference or f"CASE-{case.id}",
        cover_pdf,
        dossier_pdf,
        supporting_docs,
    )

    if format in ("base64", "json") or "application/json" in request.headers.get("accept", ""):
        return JSONResponse(
            content={
                "filename": filename,
                "media_type": "application/pdf",
                "data_base64": base64.b64encode(master_pdf).decode("ascii"),
                "size_bytes": len(master_pdf),
            }
        )
    return Response(
        content=master_pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(master_pdf)),
        },
    )


class ExportDocumentIn(BaseModel):
    """One drafted document, exactly as the applicant has it on screen."""

    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=200_000)
    filename_stem: str | None = Field(default=None, max_length=140)


class ExportDocumentsIn(BaseModel):
    documents: list[ExportDocumentIn] = Field(min_length=1, max_length=12)
    format: Literal["pdf", "docx"] = "pdf"
    # ``separate`` returns a zip holding one file per document; otherwise the documents
    # are laid out in a single file, one per page.
    separate: bool = False


@router.post("/{case_id}/export/documents")
async def export_case_documents(
    case_id: int,
    payload: ExportDocumentsIn,
    session: SessionDep,
    user: CurrentUserDep,
    request: Request,
    format: str | None = Query(default=None),
) -> Response:
    """Render the drafted documents the applicant is looking at as a PDF or a Word file.

    The text is round-tripped from the client because it is the applicant's: it may be the
    template, an AI draft, or either of those after they edited it in the browser. The
    server adds typography and the "check and sign before filing" footer, and nothing else
    — no reference, scope or preparation date is printed above the applicant's own wording,
    since these documents are read by a consular officer, not by Torii.

    The case reference is still used for the *filename*, which is how the applicant tells
    one download from another.
    """
    case = await _owned_case(session, case_id, user)
    reference = case.reference or f"CASE-{case.id}"

    fmt = payload.format
    single = len(payload.documents) == 1
    first = payload.documents[0]
    stem_source = (
        (first.filename_stem or f"{reference}-{first.title}")
        if single
        else f"{reference}-filing-kit"
    )
    default_stem = safe_stem(stem_source, "torii-document")

    if payload.separate and not single:
        content = render_bundle(
            [
                (
                    item.title,
                    item.filename_stem or f"{reference}-{item.title}",
                    item.content,
                )
                for item in payload.documents
            ],
            fmt=fmt,
        )
        filename = f"{default_stem}.zip"
        media_type = MEDIA_TYPES["zip"]
    else:
        content = render_document(
            [(item.title, item.content) for item in payload.documents], fmt=fmt
        )
        filename = f"{default_stem}.{fmt}"
        media_type = MEDIA_TYPES[fmt]

    wants_json = format in ("base64", "json") or "application/json" in request.headers.get(
        "accept", ""
    )
    if wants_json:
        return JSONResponse(
            content={
                "filename": filename,
                "media_type": media_type,
                "data_base64": base64.b64encode(content).decode("ascii"),
                "size_bytes": len(content),
            }
        )
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(content)),
        },
    )


async def _journey_for(session: AsyncSession, case: Case) -> tuple[dict[str, Any], str | None]:
    """The journey payload for one case, and its jurisdiction code."""
    from torii_api.api.cases import _case_guidance

    j_code, _v_code, _a_code, scope_label = await _scope_label(session, case)
    guidance = await _case_guidance(session, case)
    checklist = [
        ChecklistItemOut.model_validate(item).model_dump(mode="json")
        for item in await _checklist(session, case.id)
    ]
    forms = [
        GeneratedFormOut.model_validate(item).model_dump(mode="json")
        for item in await _forms(session, case.id)
    ]
    journey = build_journey(
        reference=case.reference or f"CASE-{case.id}",
        scope_label=scope_label or case.locale.upper(),
        phase=guidance.phase,
        case_status=case.status,
        checklist=checklist,
        forms=forms,
        submission_kit=await _submission_kit(session, case),
        filing_mode=_filing_mode(j_code),
        apply_url=_apply_url(j_code),
        has_research=await _research_for_case(session, case) is not None,
    )
    return journey, j_code


@router.get("/{case_id}/journey")
async def get_case_journey(
    case_id: int, session: SessionDep, user: CurrentUserDep
) -> dict[str, Any]:
    """The whole application end to end, including what has to be arranged elsewhere.

    The workflow steps show the applicant what to do next; this shows them the shape of
    the entire process — preparation, filing, decision, renewal — and which requirements
    come from a bank, an airline or another government rather than from Torii, because
    those lead times are what actually decide when the application can be filed.
    """
    case = await _owned_case(session, case_id, user)
    journey, _j_code = await _journey_for(session, case)
    return journey


@router.get("/{case_id}/plan")
async def get_case_plan(case_id: int, session: SessionDep, user: CurrentUserDep) -> dict[str, Any]:
    """The plan already built for this case, if there is one.

    Returned from the case rather than rebuilt, so opening the step again costs nothing
    and shows the applicant the same words they read last time.
    """
    case = await _owned_case(session, case_id, user)
    snapshot = case.packet_snapshot or {}
    plan = snapshot.get("ai_plan") if isinstance(snapshot, dict) else None
    return {"plan": plan if isinstance(plan, dict) else None}


@router.post("/{case_id}/plan")
async def build_case_plan(
    case_id: int, session: SessionDep, user: CurrentUserDep
) -> dict[str, Any]:
    """Build the applicant's action plan once, and keep it on the case.

    The case is reduced to the handful of facts a plan is made of before the model sees
    it — the outstanding items and their lead times, the cited filing route, the answers
    that say something — which is what makes this quick. The result is stored on the
    packet snapshot, so it is built once rather than on every visit; assembling the packet
    again clears it, because a packet that changed deserves a plan that did too.
    """
    case = await _owned_case(session, case_id, user)
    journey, j_code = await _journey_for(session, case)
    checklist = [
        ChecklistItemOut.model_validate(item).model_dump(mode="json")
        for item in await _checklist(session, case.id)
    ]
    payload = build_payload(
        journey=journey,
        checklist=checklist,
        answers=dict(case.intake_answers or {}),
        jurisdiction_code=j_code,
        nationality=case.origin_country,
        residence_country=case.residence_country,
    )
    plan = await request_plan(payload)

    snapshot = dict(case.packet_snapshot or {})
    snapshot["ai_plan"] = plan
    case.packet_snapshot = snapshot
    await session.flush()
    return {"plan": plan}


@router.post("/{case_id}/filed")
async def record_case_filed(
    case_id: int, session: SessionDep, user: CurrentUserDep
) -> dict[str, Any]:
    """Record that the applicant has filed the application themselves.

    This is not the same act as ``/submit``, and conflating the two was a bug the
    applicant met head-on: the packet step's "mark as filed" button called the e-file
    endpoint, which refuses every jurisdiction that does not accept electronic submission
    from a third party — Japan among them, because its bureau takes applications in
    person. Handing an applicant "E-file is unavailable for this jurisdiction" when all
    they said was that they had been to the counter is a refusal of the wrong question.

    Filing it themselves is the normal path. Recording it freezes the packet they filed
    from, so what was submitted can be reproduced later, and starts the renewal clock.
    No submission reference is written: the receipt number comes from the office, and
    inventing one would put a number on the case that no authority ever issued.
    """
    case = await _owned_case(session, case_id, user)
    if case.packet_snapshot is None:
        raise HTTPException(
            status_code=400,
            detail="assemble your filing kit before recording the application as filed",
        )
    checklist_items = (
        (
            await session.execute(
                select(CaseChecklistItem).where(CaseChecklistItem.case_id == case.id)
            )
        )
        .scalars()
        .all()
    )
    missing_required = [
        item
        for item in checklist_items
        if item.is_required and item.status not in ("uploaded", "gathered")
    ]
    if missing_required:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot record as filed: {len(missing_required)} required document(s) must be uploaded first.",
        )
    filed_at = datetime.now(UTC).isoformat()
    case.status = "submitted"
    case.packet_snapshot = {**case.packet_snapshot, "filed_at": filed_at}
    await session.flush()
    return {
        "status": case.status,
        "filed_at": filed_at,
        "submission_reference": case.submission_reference,
    }


@router.post("/{case_id}/submit")
async def submit_case(case_id: int, session: SessionDep, user: CurrentUserDep) -> dict[str, str]:
    """File electronically on the applicant's behalf, where the jurisdiction accepts it.

    Most do not. An applicant who filed at a counter wants ``/filed`` instead.
    """
    case = await _owned_case(session, case_id, user)
    jurisdiction = await session.get(Jurisdiction, case.jurisdiction_id)
    if jurisdiction is None or not jurisdiction.efile_enabled:
        raise HTTPException(
            status_code=400,
            detail="E-file is unavailable for this jurisdiction; use the mail/in-person packet.",
        )
    if case.packet_snapshot is None:
        raise HTTPException(status_code=400, detail="assemble the packet before submission")
    reference = f"EFILE-{case.reference}"
    case.submission_reference = reference
    case.status = "submitted"
    case.packet_snapshot = {
        **case.packet_snapshot,
        "submission_reference": reference,
    }
    await session.flush()
    return {"submission_reference": reference}


@router.post(
    "/{case_id}/escalations",
    response_model=EscalationOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_escalation(
    case_id: int, payload: EscalationIn, session: SessionDep, user: CurrentUserDep
) -> CaseEscalation:
    case = await _owned_case(session, case_id, user)
    escalation = CaseEscalation(case_id=case.id, status="open", **payload.model_dump())
    session.add(escalation)
    await session.flush()
    return escalation


@router.get("/{case_id}/escalations", response_model=list[EscalationOut])
async def get_escalations(
    case_id: int, session: SessionDep, user: CurrentUserDep
) -> list[CaseEscalation]:
    await _owned_case(session, case_id, user)
    result = await session.execute(
        select(CaseEscalation).where(CaseEscalation.case_id == case_id).order_by(CaseEscalation.id)
    )
    return list(result.scalars().all())
