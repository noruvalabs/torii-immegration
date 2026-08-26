"""Applicant-core case workflow endpoints (US-04 through US-16)."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import date
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from torii_api.api.cases import _owned_case, _research_for_case, _scope_label
from torii_api.auth.deps import CurrentUserDep
from torii_api.config import get_settings
from torii_api.db.models import (
    Case,
    CaseAction,
    CaseChecklistItem,
    CaseDocument,
    CaseEscalation,
    CaseGeneratedForm,
    DocumentRequirementSet,
    EligibilityRuleSet,
    FormTemplate,
    Jurisdiction,
    User,
)
from torii_api.db.session import get_session
from torii_api.services.citations import resolve_official_citation
from torii_api.services.checklist import ChecklistStatus, update_status, visible_requirement_items
from torii_api.services.eligibility import (
    EligibilityResult,
    evaluate_eligibility_with_ai,
)
from torii_api.services.forms import fill_form
from torii_api.services.guidance import next_status_for_phase
from torii_api.services.i18n import localized
from torii_api.services.packet import assemble_packet
from torii_api.services.payment import case_has_packet_entitlement
from torii_api.services.research import (
    research_documents,
    research_forms,
    research_is_usable,
    research_rules,
)
from torii_api.services.review import ReviewResult, review_packet

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
            return list(definition.rules)

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
            return list(definition.items)

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
    forms = [
        GeneratedFormOut.model_validate(item).model_dump(mode="json")
        for item in await _forms(session, case.id)
    ]
    return review_packet(dict(case.intake_answers or {}), documents, forms, live_versions)


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


@router.post("/{case_id}/eligibility/evaluate", response_model=EligibilityResult)
async def evaluate_case_eligibility(
    case_id: int, session: SessionDep, user: CurrentUserDep
) -> EligibilityResult:
    case = await _owned_case(session, case_id, user)
    rules = await _effective_rules(session, case)
    if not rules:
        raise HTTPException(
            status_code=404, detail="no eligibility rules available for this case scope"
        )
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


@router.get("/{case_id}/deadlines", response_model=dict[str, Any])
async def get_case_deadlines(
    case_id: int, session: SessionDep, user: CurrentUserDep
) -> dict[str, Any]:
    """Computed filing deadlines for a case (window open, online cut-off, grace period)."""
    from torii_api.api.cases import _scope_label
    from torii_api.services.deadlines import compute_deadlines

    case = await _owned_case(session, case_id, user)
    _, _, a_code, _ = await _scope_label(session, case)
    expiry = (case.intake_answers or {}).get("residence_card_expiry")
    if not expiry:
        return {"residence_expiry": None, "procedure": a_code or ""}
    return compute_deadlines(str(expiry), (a_code or "").replace("_", "").lower()).to_dict()


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
    for item in visible_requirement_items(items, dict(case.intake_answers or {})):
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
            item_key_or_code=item.code,
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


def _apply_extracted_fields_to_case_and_user(
    case: Case, user: User, extracted_fields: dict[str, Any]
) -> None:
    if not extracted_fields:
        return
    answers = dict(case.intake_answers or {})
    for key, raw_val in extracted_fields.items():
        val = raw_val.get("value") if isinstance(raw_val, dict) else raw_val
        if val is None:
            continue
        val_str = str(val).strip()
        if not val_str:
            continue

        answers[key] = val_str
        norm_key = key.lower().strip()

        # Update User global profile and intake aliases
        if norm_key in ("full_name", "applicant_name", "name", "legal_name", "holder_name", "employee_name"):
            user.full_name = val_str
            answers["full_name"] = val_str
        elif norm_key in ("nationality", "citizenship", "country_of_citizenship"):
            user.nationality = val_str
            answers["nationality"] = val_str
        elif norm_key in ("passport_number", "passport_no", "passport_num"):
            user.passport_number = val_str
            answers["passport_number"] = val_str
        elif norm_key in ("passport_expiry", "passport_expiry_date", "expiry_date", "passport_expiration_date"):
            user.passport_expiry = val_str
            answers["passport_expiry"] = val_str
        elif norm_key in ("date_of_birth", "dob", "birth_date", "applicant_dob"):
            user.date_of_birth = val_str
            answers["date_of_birth"] = val_str
        elif norm_key in ("current_country", "current_residence_country", "residence_country"):
            user.current_country = val_str
            answers["current_country"] = val_str
        elif norm_key in ("employer_name", "company_name", "sponsor_name"):
            answers["employer_name"] = val_str
            answers["company_name"] = val_str
            answers["sponsor_name"] = val_str
        elif norm_key in ("monthly_salary", "remuneration", "salary"):
            answers["monthly_salary"] = val_str
        elif norm_key in ("residence_card_number", "card_number"):
            answers["residence_card_number"] = val_str

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
    document = CaseDocument(case_id=case.id, confirmed=has_extracted, **payload.model_dump())
    session.add(document)
    await session.flush()
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


@router.post("/{case_id}/forms/generate", response_model=list[GeneratedFormOut])
async def generate_forms(
    case_id: int, session: SessionDep, user: CurrentUserDep
) -> list[CaseGeneratedForm]:
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
    return generated


@router.get("/{case_id}/forms", response_model=list[GeneratedFormOut])
async def get_forms(
    case_id: int, session: SessionDep, user: CurrentUserDep
) -> list[CaseGeneratedForm]:
    await _owned_case(session, case_id, user)
    return await _forms(session, case_id)


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
    j_code, _, _, scope_label = await _scope_label(session, case)
    snapshot = assemble_packet(
        case.reference,
        forms,
        checklist,
        case.submission_reference,
        jurisdiction_code=j_code,
        scope_label=scope_label,
    )
    case.packet_snapshot = snapshot
    case.status = "packet_ready"
    await session.flush()
    return snapshot


@router.get("/{case_id}/packet")
async def get_packet(case_id: int, session: SessionDep, user: CurrentUserDep) -> dict[str, Any]:
    case = await _owned_case(session, case_id, user)
    if get_settings().require_packet_entitlement:
        entitled = await case_has_packet_entitlement(session, case.id, user.id)
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
        j_code, _, _, scope_label = await _scope_label(session, case)
        snapshot = assemble_packet(
            case.reference,
            forms,
            checklist,
            case.submission_reference,
            jurisdiction_code=j_code,
            scope_label=scope_label,
        )
        case.packet_snapshot = snapshot
        case.status = "packet_ready"
        await session.flush()
    return case.packet_snapshot


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
        generate_uk_visa_application_pdf,
        generate_us_visa_application_pdf,
    )

    case = await _owned_case(session, case_id, user)
    answers = dict(case.intake_answers or {})
    j_code, v_code, a_code, scope_label = await _scope_label(session, case)
    j_code_upper = (j_code or (case.reference.split("-")[0] if case.reference else "JP")).upper()

    photo_data = user.avatar_url or answers.get("photo") or answers.get("applicant_photo") or answers.get("passport_photo")

    safe_ref = "".join(
        c for c in (case.reference or f"CASE-{case.id}") if c.isalnum() or c in ("-", "_", ".")
    )
    filename = f"{safe_ref or f'Case-{case_id}'}_Application_Form.pdf"

    if j_code_upper in ("UK", "GB"):
        pdf_bytes = generate_uk_visa_application_pdf(
            case.reference or f"UK-{case.id}",
            answers,
            destination_label=scope_label or "United Kingdom",
            applicant_email=case.applicant_email or user.email,
            photo_data=photo_data,
        )
    elif j_code_upper == "US":
        pdf_bytes = generate_us_visa_application_pdf(
            case.reference or f"US-{case.id}",
            answers,
            destination_label=scope_label or "United States",
            applicant_email=case.applicant_email or user.email,
            photo_data=photo_data,
        )
    elif j_code_upper == "JP":
        if a_code == "new_application" or (v_code == "tourist" and a_code not in ("renewal", "change_of_status")):
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
    _, _, _, scope_label = await _scope_label(session, case)
    safe_ref = "".join(
        c for c in (case.reference or f"CASE-{case.id}") if c.isalnum() or c in ("-", "_", ".")
    )
    filename = f"{safe_ref or f'Case-{case_id}'}_Cover_Letter.pdf"
    pdf_bytes = generate_cover_letter_pdf(
        case.reference or f"CASE-{case.id}",
        answers,
        checklist,
        scope_label=scope_label or "Visa Submission Dossier",
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


@router.get("/{case_id}/export/dossier-packet")
@router.get("/{case_id}/pdf/dossier-packet")
async def download_dossier_packet_pdf(
    case_id: int,
    session: SessionDep,
    user: CurrentUserDep,
    request: Request,
    format: str | None = Query(default=None),
) -> Response:
    from torii_api.services.packet import resolve_jurisdiction_submission_kit
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
    j_code, _, _, scope_label = await _scope_label(session, case)
    submission_kit = resolve_jurisdiction_submission_kit(
        jurisdiction_code=j_code, scope_label=scope_label
    )
    safe_ref = "".join(
        c for c in (case.reference or f"CASE-{case.id}") if c.isalnum() or c in ("-", "_", ".")
    )
    filename = f"{safe_ref or f'Case-{case_id}'}_Complete_Dossier_Packet.pdf"
    pdf_bytes = generate_dossier_packet_pdf(
        case.reference or f"CASE-{case.id}",
        answers,
        forms,
        checklist,
        submission_kit=submission_kit,
        scope_label=scope_label or "Immigration Filing Dossier",
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


@router.post("/{case_id}/submit")
async def submit_case(case_id: int, session: SessionDep, user: CurrentUserDep) -> dict[str, str]:
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
