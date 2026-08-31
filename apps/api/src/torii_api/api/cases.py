"""Cases — the core resource applicants and staff interact with.

US-01: Scoping a case to jurisdiction + visa category + action.
US-02: Branching intake questionnaire with validation and progress.
US-03: Persist progress so an applicant can stop and resume.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from torii_api.auth.deps import CurrentUserDep
from torii_api.db.models import (
    Case,
    CaseAction,
    CaseChecklistItem,
    CaseGeneratedForm,
    DocumentRequirementSet,
    EligibilityRuleSet,
    FormTemplate,
    IntakeDefinition,
    Jurisdiction,
    OutboxEvent,
    PackOverride,
    ScopeResearch,
    ScopeResearchStatus,
    User,
    VisaCategory,
)
from torii_api.db.session import get_session
from torii_api.services.deadlines import compute_deadlines
from torii_api.services.guidance import compute_guidance, next_status_for_phase
from torii_api.services.intake import (
    IntakeProgress,
    IntakeQuestion,
    is_visible,
    parse_questions,
    progress_for,
    prune_answers,
    validate_answer,
    visible_questions,
)
from torii_api.services.jp_official_forms import merge_form_questions
from torii_api.services.pack_overrides import SECTION_INTAKE, apply_overrides
from torii_api.services.research import (
    find_research,
    research_documents,
    research_for_case,
    research_forms,
    research_is_usable,
    research_progress_steps,
    research_questions,
    research_rules,
)

router = APIRouter(prefix="/v1/cases", tags=["cases"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


# ── Profile pre-fill ─────────────────────────────────────────────────────────

# Maps User profile fields to one or more intake question keys.
PROFILE_TO_INTAKE_MAP: dict[str, list[str]] = {
    "full_name": [
        "full_name",
        "applicant_name",
        "name",
        "legal_name",
        "full_legal_name",
    ],
    "nationality": [
        "nationality",
        "citizenship",
        "country_of_citizenship",
        "country_of_nationality",
    ],
    "passport_number": [
        "passport_number",
        "passport_no",
        "passport_num",
        "travel_document_number",
    ],
    "passport_expiry": [
        "passport_expiry",
        "passport_expiry_date",
        "passport_expiration_date",
        "passport_valid_until",
    ],
    "date_of_birth": [
        "date_of_birth",
        "dob",
        "birth_date",
        "applicant_dob",
        "applicant_date_of_birth",
    ],
    "current_country": [
        "current_country",
        "current_location_country",
        "current_residence_country",
        "residence_country",
        "country_of_residence",
    ],
}

INTAKE_TO_PROFILE_MAP: dict[str, str] = {
    intake_key: profile_field
    for profile_field, intake_keys in PROFILE_TO_INTAKE_MAP.items()
    for intake_key in intake_keys
}


def _prefill_from_profile(user: User) -> dict[str, Any]:
    """Pre-fill intake answers from the user's saved profile fields."""
    answers: dict[str, Any] = {}
    for profile_field, intake_keys in PROFILE_TO_INTAKE_MAP.items():
        value = getattr(user, profile_field, None)
        if value:
            for intake_key in intake_keys:
                answers[intake_key] = value
    return answers


# ── Request / response schemas ────────────────────────────────────────────────


class VisaCategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    jurisdiction_id: int
    code: str
    name: str
    is_live: bool
    research_enabled: bool = False
    # One line for the applicant, under the route name on the visa-type step.
    description: str = ""


class CaseActionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    jurisdiction_id: int
    code: str
    name: str
    is_live: bool
    research_enabled: bool = False
    description: str = ""


class ScopeIn(BaseModel):
    jurisdiction_code: str = Field(min_length=2, max_length=8, examples=["JP"])
    visa_category_code: str = Field(min_length=1, max_length=32, examples=["work"])
    action_code: str = Field(min_length=1, max_length=32, examples=["renewal"])
    locale: str = Field(default="en", min_length=2, max_length=16)
    # Cross-border cases (e.g. a Bangladeshi citizen resident in Japan). ISO-3166 alpha-2.
    origin_country: str | None = Field(default=None, min_length=2, max_length=8)
    residence_country: str | None = Field(default=None, min_length=2, max_length=8)


class CaseProgressIn(BaseModel):
    """Partial update of in-progress case state (US-03.1)."""

    intake_answers: dict[str, Any] | None = None
    intake_step: str | None = Field(default=None, max_length=128)
    notes: str | None = None


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
    locale: str
    host_locale: str
    submission_reference: str | None = None
    intake_answers: dict[str, Any] = Field(default_factory=dict)
    intake_step: str | None = None
    notes: str | None = None
    created_at: Any = None
    updated_at: Any = None
    jurisdiction_code: str | None = None
    visa_category_code: str | None = None
    case_action_code: str | None = None
    scope_label: str | None = None
    next_phase: str | None = None
    next_title: str | None = None
    origin_country: str | None = None
    residence_country: str | None = None
    research_id: int | None = None


class IntakeAnswerIn(BaseModel):
    key: str = Field(min_length=1, max_length=64)
    value: bool | str | int | None = None


class IntakeStateOut(BaseModel):
    case_id: int
    questions: list[IntakeQuestion]
    answers: dict[str, Any]
    progress: IntakeProgress
    intake_step: str | None = None


class ResearchStepOut(BaseModel):
    key: str
    label: str
    detail: str = ""
    at: str = ""


class GuidanceOut(BaseModel):
    phase: str
    title: str
    instruction: str
    cta_label: str
    blocked_reason: str | None = None
    progress: IntakeProgress | None = None
    scope_label: str | None = None
    research_status: str | None = None
    research_steps: list[ResearchStepOut] = []
    deadlines: dict[str, Any] | None = None


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
    """List visa categories for a jurisdiction. ``live_only=true`` = what an applicant is offered."""
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
        # The admin switch first, then how the content is produced — see the module docstring
        # in ``api/jurisdictions.py`` for why those are separate questions.
        stmt = stmt.where(
            VisaCategory.is_enabled.is_(True),
            VisaCategory.is_live.is_(True) | VisaCategory.research_enabled.is_(True),
        )
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
    """List case actions for a jurisdiction. ``live_only=true`` = what an applicant is offered."""
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
        stmt = stmt.where(
            CaseAction.is_enabled.is_(True),
            CaseAction.is_live.is_(True) | CaseAction.research_enabled.is_(True),
        )
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

    A scope is selectable when the admin has it switched on (``is_enabled`` on the country,
    the route and the procedure) **and** it has a live content pack or is research-enabled
    (requirements produced on demand by the live-research pipeline). Cross-border cases
    record ``origin_country`` / ``residence_country``. Returns the case in ``draft`` status.
    """
    jurisdiction = await session.scalar(
        select(Jurisdiction).where(Jurisdiction.code == payload.jurisdiction_code.upper())
    )
    if jurisdiction is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"jurisdiction '{payload.jurisdiction_code}' is not available",
        )

    visa_category = await session.scalar(
        select(VisaCategory).where(
            VisaCategory.jurisdiction_id == jurisdiction.id,
            VisaCategory.code == payload.visa_category_code.lower(),
        )
    )
    if visa_category is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"visa category '{payload.visa_category_code}'"
                f" is not available in {jurisdiction.code}"
            ),
        )

    case_action = await session.scalar(
        select(CaseAction).where(
            CaseAction.jurisdiction_id == jurisdiction.id,
            CaseAction.code == payload.action_code.lower(),
        )
    )
    if case_action is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"action '{payload.action_code}' is not available in {jurisdiction.code}",
        )

    # The admin switch is checked here and not only in the listing: an applicant who kept a
    # tab open, or posted the scope directly, must not get a case on a route ops has since
    # switched off.
    is_enabled_scope = (
        jurisdiction.is_enabled and visa_category.is_enabled and case_action.is_enabled
    )
    is_live_scope = jurisdiction.is_live and visa_category.is_live and case_action.is_live
    is_research_scope = visa_category.research_enabled and case_action.research_enabled
    if not is_enabled_scope or not (is_live_scope or is_research_scope):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="this case scope is not available",
        )

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
        locale=payload.locale,
        intake_answers=_prefill_from_profile(user),
        origin_country=_normalize_country_code(payload.origin_country),
        residence_country=_normalize_country_code(payload.residence_country),
    )
    session.add(case)
    try:
        await session.flush()
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="case reference conflict — please retry",
        ) from exc
    # Link (and queue when needed) a live-research snapshot for a scope without a live pack.
    await _enqueue_research_if_needed(session, case, jurisdiction, visa_category, case_action)
    await session.refresh(case)
    return case


# ── Shared helpers ────────────────────────────────────────────────────────────


def _normalize_country_code(value: str | None) -> str | None:
    """Normalize an ISO-3166 alpha-2 code to uppercase, or None when blank."""
    if value is None:
        return None
    value = value.strip().upper()
    return value or None


async def _research_for_case(session: AsyncSession, case: Case) -> ScopeResearch | None:
    """Load the research snapshot attached to a case, if any."""
    return await research_for_case(session, case.id, case.research_id)


def _effective_research_status(research: ScopeResearch | None) -> str | None:
    """Collapse a snapshot into the guidance-consumable status vocabulary."""
    if research is None:
        return None
    if research.status == ScopeResearchStatus.COMPLETED:
        return "completed" if research_is_usable(research) else "stale"
    return research.status


async def _enqueue_research_if_needed(
    session: AsyncSession,
    case: Case,
    jurisdiction: Jurisdiction,
    visa_category: VisaCategory,
    case_action: CaseAction,
) -> str | None:
    """Link (and queue) a research snapshot for a research-driven scope.

    Scopes without a live seeded content pack are researched live via Tavily web search
    and LLM extraction. Scopes with verified live packs use their authoritative content.
    Fresh snapshots are reused; stale/failed ones are reset and re-queued via the
    transactional outbox (``case.research.queued``).
    """
    if case.visa_category_id is None or case.case_action_id is None:
        return None

    # Do not enqueue or link research if the scope has live seeded definitions
    has_intake, has_eligibility, has_docs, _ = await _def_flags(session, case)
    if has_intake and has_eligibility and has_docs:
        return None

    origin = _normalize_country_code(case.origin_country)
    residence = _normalize_country_code(case.residence_country)
    research = await find_research(
        session,
        jurisdiction_id=case.jurisdiction_id,
        visa_category_id=case.visa_category_id,
        case_action_id=case.case_action_id,
        origin_country=origin,
        residence_country=residence,
    )
    if research is not None and research_is_usable(research):
        case.research_id = research.id
        await session.flush()
        return "completed"

    if research is not None and research.status in (
        ScopeResearchStatus.QUEUED,
        ScopeResearchStatus.RUNNING,
    ):
        # A job is already in flight for this scope — attach the case to it instead of
        # resetting the row and enqueueing a second concurrent outbox event (repeated
        # retries while a job is running would otherwise race multiple scrapes against
        # the same ScopeResearch row).
        case.research_id = research.id
        await session.flush()
        return research.status

    if research is None:
        research = ScopeResearch(
            jurisdiction_id=case.jurisdiction_id,
            visa_category_id=case.visa_category_id,
            case_action_id=case.case_action_id,
            origin_country=origin,
            residence_country=residence,
            status=ScopeResearchStatus.QUEUED,
            payload={},
            source_pages=[],
        )
        session.add(research)
        await session.flush()
    else:
        research.status = ScopeResearchStatus.QUEUED
        research.payload = {}
        research.source_pages = []
        research.error = None
        research.researched_at = None
        research.expires_at = None
        await session.flush()

    case.research_id = research.id
    session.add(
        OutboxEvent(
            topic="case.research.queued",
            payload={
                "research_id": research.id,
                "case_id": case.id,
                "jurisdiction_code": jurisdiction.code,
                "visa_category": visa_category.code,
                "action": case_action.code,
                "origin_country": origin,
                "residence_country": residence,
            },
        )
    )
    await session.flush()
    return "queued"


async def _owned_case(session: AsyncSession, case_id: int, user: User) -> Case:
    """Load a case owned by ``user``, or raise 404 (no existence leak across owners)."""
    case = await session.scalar(select(Case).where(Case.id == case_id, Case.user_id == user.id))
    if case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"case {case_id} not found",
        )
    return case


async def _intake_questions_for_case(session: AsyncSession, case: Case) -> list[dict[str, Any]]:
    """Resolve intake questions for the case: live definition if available, else research snapshot fallback."""
    if case.visa_category_id is None or case.case_action_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="case is not fully scoped for intake",
        )
    action_ids = [case.case_action_id]
    case_act = await session.get(CaseAction, case.case_action_id)
    if case_act is not None:
        alt_code = (
            "new_application"
            if case_act.code == "new"
            else ("new" if case_act.code == "new_application" else None)
        )
        if alt_code:
            alt_act = await session.scalar(
                select(CaseAction).where(
                    CaseAction.jurisdiction_id == case.jurisdiction_id,
                    CaseAction.code == alt_code,
                )
            )
            if alt_act is not None:
                action_ids.append(alt_act.id)

    definition = await session.scalar(
        select(IntakeDefinition).where(
            IntakeDefinition.jurisdiction_id == case.jurisdiction_id,
            IntakeDefinition.visa_category_id == case.visa_category_id,
            IntakeDefinition.case_action_id.in_(action_ids),
            IntakeDefinition.is_live.is_(True),
        )
    )
    if definition is not None and definition.questions:
        questions = apply_overrides(
            list(definition.questions),
            await _pack_overrides_for_case(session, case, action_ids),
            section=SECTION_INTAKE,
        )
        return await _with_official_form_questions(session, case, questions)

    research = await _research_for_case(session, case)
    if research is not None and _effective_research_status(research) == "completed":
        questions = research_questions(research.payload)
        if questions:
            return await _with_official_form_questions(session, case, questions)

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="no intake definition for this case scope",
    )


async def _pack_overrides_for_case(
    session: AsyncSession, case: Case, action_ids: list[int]
) -> list[dict[str, Any]]:
    """Admin edits stored against this case's scope, which a reseed does not erase."""
    if case.visa_category_id is None:
        return []
    rows = await session.scalars(
        select(PackOverride).where(
            PackOverride.jurisdiction_id == case.jurisdiction_id,
            PackOverride.visa_category_id == case.visa_category_id,
            PackOverride.case_action_id.in_(action_ids),
        )
    )
    return [{"path": row.path, "value": row.value} for row in rows]


async def _with_official_form_questions(
    session: AsyncSession, case: Case, questions: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Extend a scope's intake with the items its official government form asks for.

    The applicant signs a specific ministry sheet, so intake has to cover every box on
    it — nationality, sex, residence card number, the 有/無 disclosures. Pack-authored
    questions still win on any key they define; the rest are appended as optional so a
    case in flight is never blocked by the new ones.
    """
    j_code, v_code, a_code, _label = await _scope_label(session, case)
    if (j_code or "").upper() != "JP" or not v_code or not a_code:
        return questions
    return merge_form_questions(questions, v_code, a_code)


def _intake_state(
    case: Case,
    questions: list[dict[str, Any]],
    jurisdiction_code: str = "JP",
    visa_category: str = "",
) -> IntakeStateOut:
    parsed = parse_questions(
        questions, jurisdiction_code=jurisdiction_code, visa_category=visa_category
    )
    answers = dict(case.intake_answers or {})
    return IntakeStateOut(
        case_id=case.id,
        questions=visible_questions(parsed, answers),
        answers=answers,
        progress=progress_for(parsed, answers),
        intake_step=case.intake_step,
    )


# Intake answer keys that capture continuity facts for the current application.
# Values are copied verbatim into Case.prior_application so rules can evaluate
# "unchanged since the last application" predicates deterministically (NF-1).
PRIOR_APPLICATION_ANSWER_KEYS: tuple[str, ...] = (
    "same_employer_as_last_application",
    "same_duties_as_last_application",
    "same_institution_as_last_application",
)


def _sync_prior_application(case: Case) -> None:
    """Mirror continuity intake answers into ``case.prior_application`` (NF-1)."""
    answers = dict(case.intake_answers or {})
    facts = {key: answers[key] for key in PRIOR_APPLICATION_ANSWER_KEYS if key in answers}
    if not facts:
        return
    case.prior_application = {**dict(case.prior_application or {}), **facts}


async def _scope_label(
    session: AsyncSession, case: Case
) -> tuple[str | None, str | None, str | None, str | None]:
    jurisdiction = await session.get(Jurisdiction, case.jurisdiction_id)
    visa = (
        await session.get(VisaCategory, case.visa_category_id)
        if case.visa_category_id is not None
        else None
    )
    action = (
        await session.get(CaseAction, case.case_action_id)
        if case.case_action_id is not None
        else None
    )
    j_code = jurisdiction.code if jurisdiction else None
    v_code = visa.code if visa else None
    a_code = action.code if action else None
    parts = [
        p
        for p in (
            jurisdiction.name if jurisdiction else None,
            visa.name if visa else None,
            action.name if action else None,
        )
        if p
    ]
    label = " · ".join(parts) if parts else None
    return j_code, v_code, a_code, label


async def _def_flags(session: AsyncSession, case: Case) -> tuple[bool, bool, bool, bool]:
    if case.visa_category_id is None or case.case_action_id is None:
        return False, False, False, False
    scope = (
        case.jurisdiction_id,
        case.visa_category_id,
        case.case_action_id,
    )
    has_intake = (
        await session.scalar(
            select(IntakeDefinition.id).where(
                IntakeDefinition.jurisdiction_id == scope[0],
                IntakeDefinition.visa_category_id == scope[1],
                IntakeDefinition.case_action_id == scope[2],
                IntakeDefinition.is_live.is_(True),
            )
        )
        is not None
    )
    has_eligibility = (
        await session.scalar(
            select(EligibilityRuleSet.id).where(
                EligibilityRuleSet.jurisdiction_id == scope[0],
                EligibilityRuleSet.visa_category_id == scope[1],
                EligibilityRuleSet.case_action_id == scope[2],
                EligibilityRuleSet.is_live.is_(True),
            )
        )
        is not None
    )
    has_docs = (
        await session.scalar(
            select(DocumentRequirementSet.id).where(
                DocumentRequirementSet.jurisdiction_id == scope[0],
                DocumentRequirementSet.visa_category_id == scope[1],
                DocumentRequirementSet.case_action_id == scope[2],
                DocumentRequirementSet.is_live.is_(True),
            )
        )
        is not None
    )
    has_forms = (
        await session.scalar(
            select(FormTemplate.id).where(
                FormTemplate.jurisdiction_id == scope[0],
                FormTemplate.visa_category_id == scope[1],
                FormTemplate.case_action_id == scope[2],
                FormTemplate.is_live.is_(True),
            )
        )
        is not None
    )
    return has_intake, has_eligibility, has_docs, has_forms


def _case_deadlines(case: Case, action_code: str | None) -> dict[str, object] | None:
    """Derive the deadline profile from the residence-card expiry intake answer.

    Returns ``None`` when no expiry is known yet (the applicant has not reached that intake
    branch). ``action_code`` (e.g. ``extend`` / ``change`` / ``new_application``) decides
    whether the 特例期間 grace period applies.
    """
    expiry = (case.intake_answers or {}).get("residence_card_expiry")
    procedure = (action_code or "").replace("_", "").lower()
    if expiry is None:
        return None
    return compute_deadlines(str(expiry), procedure).to_dict()


async def _case_guidance(session: AsyncSession, case: Case) -> GuidanceOut:
    j_code, v_code, a_code, label = await _scope_label(session, case)
    has_intake, has_eligibility, has_docs, has_forms = await _def_flags(session, case)
    research = await _research_for_case(session, case)
    research_status = _effective_research_status(research)
    # A usable research snapshot provides the definitions for a research-driven scope.
    # Only flip flags true when the corresponding slice is present so missing form
    # templates do not lock the applicant on a forms step that will 500/404.
    if research_status == "completed" and research is not None:
        payload = research.payload or {}
        has_intake = has_intake or bool(research_questions(payload))
        has_eligibility = has_eligibility or bool(research_rules(payload))
        has_docs = has_docs or bool(research_documents(payload))
        has_research_forms = bool(research_forms(payload))
        has_forms = has_forms or has_research_forms
        # Forms are optional when the rest of the research pack is usable —
        # allow the workflow past checklist without a dead-end forms phase.
        if has_intake and has_eligibility and has_docs and not has_forms:
            has_forms = True

    intake_questions: list[dict[str, Any]] | None = None
    if has_intake:
        action_ids = [case.case_action_id] if case.case_action_id is not None else []
        case_act = (
            await session.get(CaseAction, case.case_action_id)
            if case.case_action_id is not None
            else None
        )
        if case_act is not None:
            alt_code = (
                "new_application"
                if case_act.code == "new"
                else ("new" if case_act.code == "new_application" else None)
            )
            if alt_code:
                alt_act = await session.scalar(
                    select(CaseAction).where(
                        CaseAction.jurisdiction_id == case.jurisdiction_id,
                        CaseAction.code == alt_code,
                    )
                )
                if alt_act is not None:
                    action_ids.append(alt_act.id)

        definition = await session.scalar(
            select(IntakeDefinition).where(
                IntakeDefinition.jurisdiction_id == case.jurisdiction_id,
                IntakeDefinition.visa_category_id == case.visa_category_id,
                IntakeDefinition.case_action_id.in_(action_ids),
                IntakeDefinition.is_live.is_(True),
            )
        )
        if definition is not None and definition.questions:
            intake_questions = list(definition.questions)
        elif research is not None and research_questions(research.payload):
            intake_questions = research_questions(research.payload)

    checklist = (
        (
            await session.execute(
                select(CaseChecklistItem)
                .where(CaseChecklistItem.case_id == case.id)
                .order_by(CaseChecklistItem.id)
            )
        )
        .scalars()
        .all()
    )
    forms = (
        (
            await session.execute(
                select(CaseGeneratedForm)
                .where(CaseGeneratedForm.case_id == case.id)
                .order_by(CaseGeneratedForm.id)
            )
        )
        .scalars()
        .all()
    )

    guidance = compute_guidance(
        intake_questions=intake_questions,
        answers=dict(case.intake_answers or {}),
        eligibility_snapshot=case.eligibility_snapshot,
        checklist_items=[
            {
                "code": item.code,
                "is_required": item.is_required,
                "status": item.status,
            }
            for item in checklist
        ],
        generated_forms=[{"id": form.id} for form in forms],
        review_flags_acknowledged=bool(case.review_flags_acknowledged),
        packet_snapshot=case.packet_snapshot,
        status=case.status,
        has_intake_def=has_intake,
        has_eligibility_def=has_eligibility,
        has_document_def=has_docs,
        has_form_def=has_forms,
        research_status=research_status,
        scope_label=label,
        deadlines=_case_deadlines(case, a_code),
    )
    steps = research_progress_steps(research.payload if research is not None else None)
    _ = (j_code, v_code, a_code)
    return GuidanceOut.model_validate(
        {
            **guidance.model_dump(),
            "research_status": research_status,
            "research_steps": steps,
        }
    )


async def _enrich_case(session: AsyncSession, case: Case) -> CaseOut:
    j_code, v_code, a_code, label = await _scope_label(session, case)
    guidance = await _case_guidance(session, case)
    base = CaseOut.model_validate(case)
    return base.model_copy(
        update={
            "jurisdiction_code": j_code,
            "visa_category_code": v_code,
            "case_action_code": a_code,
            "scope_label": label,
            "next_phase": guidance.phase,
            "next_title": guidance.title,
        }
    )


# ── List / intake / get / save ────────────────────────────────────────────────


@router.get("", response_model=list[CaseOut])
async def list_cases(
    session: SessionDep,
    user: CurrentUserDep,
) -> list[CaseOut]:
    """List the current user's cases (US-03.3, US-03.4)."""
    result = await session.execute(
        select(Case).where(Case.user_id == user.id).order_by(Case.created_at.desc())
    )
    cases = list(result.scalars().all())
    return [await _enrich_case(session, case) for case in cases]


@router.get("/{case_id}/intake", response_model=IntakeStateOut)
async def get_intake(
    case_id: int,
    session: SessionDep,
    user: CurrentUserDep,
) -> IntakeStateOut:
    """Return visible intake questions, answers, and progress for a case (US-02)."""
    case = await _owned_case(session, case_id, user)
    questions = await _intake_questions_for_case(session, case)
    j_code, v_code, _, _ = await _scope_label(session, case)

    # Pre-fill any missing answers from the user's global profile
    profile_prefill = _prefill_from_profile(user)
    current_answers = dict(case.intake_answers or {})
    needs_flush = False
    for k, v in profile_prefill.items():
        if (
            k not in current_answers or current_answers[k] is None or current_answers[k] == ""
        ) and v:
            current_answers[k] = v
            needs_flush = True
    if needs_flush:
        parsed_q = parse_questions(questions, jurisdiction_code=j_code, visa_category=v_code)
        case.intake_answers = prune_answers(parsed_q, current_answers)
        await session.flush()

    return _intake_state(case, questions, jurisdiction_code=j_code, visa_category=v_code)


INTAKE_KEY_ALIASES: dict[str, list[str]] = {
    "corporate_number": ["employer_corporate_number", "company_number", "organization_number"],
    "employer_corporate_number": ["corporate_number", "company_number", "organization_number"],
    "employer_name": ["company_name", "sponsoring_organization", "host_company_name"],
    "company_name": ["employer_name", "sponsoring_organization"],
    "monthly_salary": ["salary_monthly", "income_monthly", "salary"],
    "salary_monthly": ["monthly_salary", "income_monthly", "salary"],
    "salary": ["monthly_salary", "salary_monthly", "annual_salary_jpy", "income_monthly"],
    "annual_salary_jpy": ["salary", "monthly_salary", "salary_monthly"],
    "attendance_rate": ["attendance_percentage", "school_attendance_rate"],
    "attendance_percentage": ["attendance_rate", "school_attendance_rate"],
    "purpose_of_visit": ["main_purpose", "purpose", "visit_purpose"],
    "main_purpose": ["purpose_of_visit", "purpose", "visit_purpose"],
    "intended_length_of_stay_days": ["stay_duration_days", "length_of_stay_days", "stay_days"],
    "stay_duration_days": ["intended_length_of_stay_days", "length_of_stay_days", "stay_days"],
    "passport_number": ["passport_no", "passport"],
    "passport_no": ["passport_number", "passport"],
    "birth_date": ["date_of_birth", "dob"],
    "date_of_birth": ["birth_date", "dob"],
}


@router.put("/{case_id}/intake/answer", response_model=IntakeStateOut)
async def answer_intake(
    case_id: int,
    payload: IntakeAnswerIn,
    session: SessionDep,
    user: CurrentUserDep,
) -> IntakeStateOut:
    """Validate and store one intake answer; re-branch and clear stale answers (US-02.3–02.5)."""
    case = await _owned_case(session, case_id, user)
    j_code, v_code, _, _ = await _scope_label(session, case)
    questions = parse_questions(
        await _intake_questions_for_case(session, case),
        jurisdiction_code=j_code,
        visa_category=v_code,
    )
    by_key = {q.key: q for q in questions}

    target_key = payload.key
    question = by_key.get(target_key)
    if question is None:
        # Check aliases
        for alias in INTAKE_KEY_ALIASES.get(target_key, []):
            if alias in by_key:
                target_key = alias
                question = by_key[alias]
                break

    if question is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"unknown question '{payload.key}'",
        )

    val = payload.value
    if question.type == "integer" and isinstance(val, str) and val.strip().isdigit():
        val = int(val.strip())

    current = dict(case.intake_answers or {})
    if not is_visible(question, current):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"question '{payload.key}' is not applicable on the current branch",
        )

    error = validate_answer(question, val)
    if error is not None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=error)

    merged = {**current, target_key: val}
    case.intake_answers = prune_answers(questions, merged)
    case.intake_step = target_key
    case.review_flags_acknowledged = False
    case.eligibility_snapshot = None
    _sync_prior_application(case)

    # Auto-sync answer to user global profile if it maps to a profile field
    profile_field = INTAKE_TO_PROFILE_MAP.get(payload.key)
    if profile_field and payload.value and isinstance(payload.value, str):
        val = payload.value.strip()
        if val:
            setattr(user, profile_field, val)
            required_fields = ["full_name", "nationality", "passport_number", "current_country"]
            user.profile_complete = all(bool(getattr(user, f, None)) for f in required_fields)

    state = _intake_state(
        case, [q.model_dump() for q in questions], jurisdiction_code=j_code, visa_category=v_code
    )
    if state.progress.complete:
        new_status = next_status_for_phase("eligibility", case.status)
        if new_status is not None:
            case.status = new_status
    await session.flush()
    await session.refresh(case)
    return _intake_state(
        case, [q.model_dump() for q in questions], jurisdiction_code=j_code, visa_category=v_code
    )


@router.get("/{case_id}/guidance", response_model=GuidanceOut)
async def get_case_guidance(
    case_id: int,
    session: SessionDep,
    user: CurrentUserDep,
) -> GuidanceOut:
    """Return the single next action for this case."""
    case = await _owned_case(session, case_id, user)
    return await _case_guidance(session, case)


@router.post("/{case_id}/research")
async def re_research_case(
    case_id: int, session: SessionDep, user: CurrentUserDep
) -> dict[str, str]:
    """Force a fresh live-research run for a research-driven case (or no-op on a live scope).

    Resets any stale/failed snapshot to ``queued`` and enqueues ``case.research.queued``.
    """
    case = await _owned_case(session, case_id, user)
    if case.visa_category_id is None or case.case_action_id is None:
        raise HTTPException(status_code=400, detail="case is not fully scoped")
    jurisdiction = await session.get(Jurisdiction, case.jurisdiction_id)
    visa_category = await session.get(VisaCategory, case.visa_category_id)
    case_action = await session.get(CaseAction, case.case_action_id)
    if jurisdiction is None or visa_category is None or case_action is None:
        raise HTTPException(status_code=400, detail="case scope is incomplete")
    status_value = await _enqueue_research_if_needed(
        session, case, jurisdiction, visa_category, case_action
    )
    if status_value is None:
        return {
            "status": "live_scope",
            "message": "this scope uses seeded content, no research needed",
        }
    return {"status": status_value, "message": "research queued"}


@router.get("/{case_id}", response_model=CaseOut)
async def get_case(
    case_id: int,
    session: SessionDep,
    user: CurrentUserDep,
) -> CaseOut:
    """Return a saved case with answers and position so the applicant can resume (US-03.2)."""
    case = await _owned_case(session, case_id, user)
    return await _enrich_case(session, case)


@router.patch("/{case_id}", response_model=CaseOut)
async def save_case_progress(
    case_id: int,
    payload: CaseProgressIn,
    session: SessionDep,
    user: CurrentUserDep,
) -> CaseOut:
    """Persist intake answers and flow position for later resume (US-03.1).

    Omitted fields are left unchanged. Passing ``intake_answers`` replaces the whole map
    (callers merge client-side); clear progress with an empty object.
    """
    case = await _owned_case(session, case_id, user)
    data = payload.model_dump(exclude_unset=True)
    if "intake_answers" in data and data["intake_answers"] is not None:
        case.intake_answers = data["intake_answers"]
        case.review_flags_acknowledged = False
    if "intake_step" in data:
        case.intake_step = data["intake_step"]
    if "notes" in data:
        case.notes = data["notes"]
    await session.flush()
    await session.refresh(case)
    return await _enrich_case(session, case)


@router.delete(
    "/{case_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_case(case_id: int, session: SessionDep, user: CurrentUserDep):
    """Delete a case owned by the applicant (draft/in-progress only)."""
    case = await _owned_case(session, case_id, user)
    if case.status == "submitted":
        raise HTTPException(status_code=409, detail="cannot delete a submitted case")
    await session.delete(case)
    await session.flush()
