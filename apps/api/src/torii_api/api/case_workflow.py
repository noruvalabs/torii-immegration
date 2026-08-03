"""Applicant-core case workflow endpoints (US-04 through US-16)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from torii_api.api.cases import _owned_case, _research_for_case
from torii_api.auth.deps import CurrentUserDep
from torii_api.config import get_settings
from torii_api.db.models import (
    Case,
    CaseChecklistItem,
    CaseDocument,
    CaseEscalation,
    CaseGeneratedForm,
    DocumentRequirementSet,
    EligibilityRuleSet,
    FormTemplate,
    Jurisdiction,
)
from torii_api.db.session import get_session
from torii_api.services.checklist import ChecklistStatus, update_status, visible_requirement_items
from torii_api.services.eligibility import EligibilityResult, evaluate_eligibility
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


async def _effective_rules(session: AsyncSession, case: Case) -> list[dict[str, Any]]:
    """Eligibility rules for the case: live definition, else the research snapshot."""
    if case.visa_category_id is not None and case.case_action_id is not None:
        definition = await session.scalar(
            select(EligibilityRuleSet).where(
                EligibilityRuleSet.jurisdiction_id == case.jurisdiction_id,
                EligibilityRuleSet.visa_category_id == case.visa_category_id,
                EligibilityRuleSet.case_action_id == case.case_action_id,
                EligibilityRuleSet.is_live.is_(True),
            )
        )
        if definition is not None:
            return list(definition.rules or [])
    research = await _research_for_case(session, case)
    if research is not None and research_is_usable(research):
        return research_rules(research.payload)
    return []


async def _effective_documents(session: AsyncSession, case: Case) -> list[dict[str, Any]]:
    """Document requirements for the case: live definition, else the research snapshot."""
    if case.visa_category_id is not None and case.case_action_id is not None:
        definition = await session.scalar(
            select(DocumentRequirementSet).where(
                DocumentRequirementSet.jurisdiction_id == case.jurisdiction_id,
                DocumentRequirementSet.visa_category_id == case.visa_category_id,
                DocumentRequirementSet.case_action_id == case.case_action_id,
                DocumentRequirementSet.is_live.is_(True),
            )
        )
        if definition is not None:
            return list(definition.items or [])
    research = await _research_for_case(session, case)
    if research is not None and research_is_usable(research):
        return research_documents(research.payload)
    return []


async def _effective_templates(session: AsyncSession, case: Case) -> list[_FormDescriptor]:
    """Forms for the case: live FormTemplates, else the research snapshot's templates."""
    if case.visa_category_id is not None and case.case_action_id is not None:
        result = await session.execute(
            select(FormTemplate)
            .where(
                FormTemplate.jurisdiction_id == case.jurisdiction_id,
                FormTemplate.visa_category_id == case.visa_category_id,
                FormTemplate.case_action_id == case.case_action_id,
                FormTemplate.is_live.is_(True),
            )
            .order_by(FormTemplate.code)
        )
        live = list(result.scalars().all())
        if live:
            return [
                _FormDescriptor(
                    code=t.code,
                    version=t.version,
                    official_title=t.official_title,
                    citation=dict(t.citation or {}),
                    field_mappings=list(t.field_mappings or []),
                    template_id=t.id,
                )
                for t in live
            ]
    research = await _research_for_case(session, case)
    if research is not None and research_is_usable(research):
        return [
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
    result = evaluate_eligibility(dict(case.intake_answers or {}), rules)
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
    for item in visible_requirement_items(items, dict(case.intake_answers or {})):
        old = old_items.get(item.code)
        created = CaseChecklistItem(
            case_id=case.id,
            code=item.code,
            name=localized(item.name, case.locale),
            how_to_obtain=localized(item.how_to_obtain, case.locale),
            why_required=localized(item.why_required, case.locale),
            is_required=item.is_required,
            status=old.status if old else "needed",
            citation=item.citation,
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


@router.post(
    "/{case_id}/documents", response_model=DocumentOut, status_code=status.HTTP_201_CREATED
)
async def register_document(
    case_id: int, payload: DocumentIn, session: SessionDep, user: CurrentUserDep
) -> CaseDocument:
    case = await _owned_case(session, case_id, user)
    document = CaseDocument(case_id=case.id, confirmed=False, **payload.model_dump())
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
    confirmed_fields: dict[str, Any] = {}
    for key, raw_value in dict(document.extracted_fields or {}).items():
        confirmed_fields[key] = raw_value.get("value") if isinstance(raw_value, dict) else raw_value
    case.intake_answers = {**dict(case.intake_answers or {}), **confirmed_fields}
    case.review_flags_acknowledged = False
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
    if not templates:
        raise HTTPException(
            status_code=404, detail="no form templates available for this case scope"
        )
    await session.execute(delete(CaseGeneratedForm).where(CaseGeneratedForm.case_id == case.id))
    generated: list[CaseGeneratedForm] = []
    for template in templates:
        filled = fill_form(template.field_mappings, dict(case.intake_answers or {}))
        form = CaseGeneratedForm(
            case_id=case.id,
            form_template_id=template.template_id,
            research_id=template.research_id,
            form_code=template.code,
            form_version=template.version,
            filled_fields=filled.filled_fields,
            missing_required_fields=filled.missing_required_fields,
            citation=template.citation,
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
    snapshot = assemble_packet(case.reference, forms, checklist, case.submission_reference)
    case.packet_snapshot = snapshot
    case.status = "packet_ready"
    await session.flush()
    return snapshot


@router.get("/{case_id}/packet")
async def get_packet(case_id: int, session: SessionDep, user: CurrentUserDep) -> dict[str, Any]:
    case = await _owned_case(session, case_id, user)
    if case.packet_snapshot is None:
        raise HTTPException(status_code=404, detail="packet has not been assembled")
    if get_settings().require_packet_entitlement:
        entitled = await case_has_packet_entitlement(session, case.id, user.id)
        if not entitled:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="packet download requires a completed payment entitlement",
            )
    return case.packet_snapshot


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
