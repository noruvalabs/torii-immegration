"""Cases — the core resource applicants and staff interact with.

US-01: Scoping a case to jurisdiction + visa category + action.
US-02: Branching intake questionnaire with validation and progress.
US-03: Persist progress so an applicant can stop and resume.
"""

from __future__ import annotations

from typing import Annotated, Any, cast

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
    UserRole,
    VisaCategory,
)
from torii_api.db.session import get_session
from torii_api.services.agentic import find_case_stage, stage_is_usable, stage_items
from torii_api.services.deadlines import compute_deadlines
from torii_api.services.guidance import compute_guidance, next_status_for_phase
from torii_api.services.submission_track import resolve_submission_track
from torii_api.services.intake import (
    IntakeProgress,
    IntakeQuestion,
    QuestionType,
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
from torii_api.services.scope_availability import scope_is_available

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
    is_archived: bool | None = None
    submission_reference: str | None = Field(default=None, max_length=128)
    status: str | None = Field(default=None, max_length=64)


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
    is_archived: bool = False
    is_entitled: bool = False
    packet_snapshot: dict[str, Any] | None = None
    submission_track: str = "consular"
    track_summary: dict[str, Any] | None = None


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
    submission_track: str = "consular"
    track_summary: dict[str, Any] | None = None


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
    """List visa categories for a jurisdiction, optionally only the switched-on, backed ones.

    ``live_only`` is a per-row filter, not the applicant's offer: a route only reaches
    the visa-type step when a procedure with matching flags exists too — see
    ``torii_api.services.scope_availability``.
    """
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
    """List case actions for a jurisdiction, optionally only the switched-on, backed ones.

    ``live_only`` is a per-row filter, not the applicant's offer: a route only reaches
    the visa-type step when a procedure with matching flags exists too — see
    ``torii_api.services.scope_availability``.
    """
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
) -> CaseOut:
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

    # Checked here and not only in the listing: an applicant who kept a tab open, or posted
    # the scope directly, must not get a case on a route ops has since switched off. The
    # test itself lives in one place so the listing endpoints cannot offer a scope this
    # then refuses — see torii_api.services.scope_availability.
    if not scope_is_available(jurisdiction, visa_category, case_action):
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
        if parts:
            try:
                seq = int(parts[-1]) + 1
            except ValueError:
                pass
    v_slug = visa_category.code.upper().replace("_", "")
    a_slug = case_action.code.upper().replace("_", "")
    reference = f"{jurisdiction.code}-{v_slug}-{a_slug}-{year}-{seq:06d}"

    case = Case(
        reference=reference,
        jurisdiction_id=jurisdiction.id,
        visa_category_id=visa_category.id,
        case_action_id=case_action.id,
        user_id=user.id,
        status="draft",
        applicant_email=user.email,
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

    _, _, _, label = await _scope_label(session, case)
    track_meta = resolve_submission_track(
        jurisdiction_code=jurisdiction.code,
        visa_category_code=visa_category.code,
        explicit_category_track=getattr(visa_category, "submission_track", None),
        explicit_jurisdiction_track=getattr(jurisdiction, "submission_track", None),
    )
    base = CaseOut.model_validate(case)
    return base.model_copy(
        update={
            "jurisdiction_code": jurisdiction.code,
            "visa_category_code": visa_category.code,
            "case_action_code": case_action.code,
            "scope_label": label,
            "submission_track": track_meta.track.value,
            "track_summary": track_meta.model_dump(),
        }
    )


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
    """Load a case owned by ``user`` (or any case if user is admin/ops), or raise 404."""
    if user.role in (UserRole.ADMIN, UserRole.OPS):
        case = await session.scalar(select(Case).where(Case.id == case_id))
    else:
        case = await session.scalar(select(Case).where(Case.id == case_id, Case.user_id == user.id))
    if case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"case {case_id} not found",
        )
    return case


UNIVERSAL_BASELINE_QUESTIONS: list[dict[str, Any]] = [
    {
        "key": "applicant.full_name",
        "prompt": "Full Legal Name (as printed in passport)",
        "type": "string",
        "required": True,
        "section": "1. Personal Information",
        "hint": "Given name(s) and surname exactly as shown in your passport machine-readable zone.",
    },
    {
        "key": "date_of_birth",
        "prompt": "Date of Birth",
        "type": "date",
        "required": True,
        "section": "1. Personal Information",
    },
    {
        "key": "gender",
        "prompt": "Gender",
        "type": "enum",
        "options": ["Male", "Female", "Other"],
        "required": True,
        "section": "1. Personal Information",
    },
    {
        "key": "marital_status",
        "prompt": "Marital Status",
        "type": "enum",
        "options": ["Single", "Married", "Divorced", "Widowed"],
        "required": False,
        "section": "1. Personal Information",
    },
    {
        "key": "nationality",
        "prompt": "Current Nationality / Citizenship",
        "type": "string",
        "required": True,
        "section": "2. Passport & Nationality",
    },
    {
        "key": "passport_number",
        "prompt": "Passport Number",
        "type": "string",
        "required": True,
        "section": "2. Passport & Nationality",
        "hint": "Primary international travel passport number.",
    },
    {
        "key": "passport_country",
        "prompt": "Passport Issuing Country",
        "type": "string",
        "required": True,
        "section": "2. Passport & Nationality",
    },
    {
        "key": "passport_issue_date",
        "prompt": "Passport Date of Issue",
        "type": "date",
        "required": True,
        "section": "2. Passport & Nationality",
    },
    {
        "key": "passport_expiry_date",
        "prompt": "Passport Expiry Date",
        "type": "date",
        "required": True,
        "section": "2. Passport & Nationality",
        "hint": "Must be valid for at least 6 months after intended arrival.",
    },
    {
        "key": "email",
        "prompt": "Contact Email Address",
        "type": "string",
        "required": True,
        "section": "3. Contact & Address",
    },
    {
        "key": "phone",
        "prompt": "Primary Mobile Phone Number (with country code)",
        "type": "string",
        "required": True,
        "section": "3. Contact & Address",
    },
    {
        "key": "home_address",
        "prompt": "Permanent Residential Address",
        "type": "string",
        "required": True,
        "section": "3. Contact & Address",
    },
    {
        "key": "arrival_date",
        "prompt": "Intended Date of Arrival",
        "type": "date",
        "required": True,
        "section": "4. Planned Travel",
    },
    {
        "key": "stay_duration_days",
        "prompt": "Intended Duration of Stay (in days)",
        "type": "integer",
        "required": True,
        "section": "4. Planned Travel",
    },
    {
        "key": "arrival_city",
        "prompt": "Port of Entry / Destination City",
        "type": "string",
        "required": False,
        "section": "4. Planned Travel",
    },
]


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

    # Next check CaseStageResearch (newer agentic pipeline) for this specific case
    stage_res = await find_case_stage(session, case.id, "intake")
    if stage_res is not None and stage_is_usable(stage_res):
        questions = stage_items(stage_res, "intake")
        if questions:
            return await _with_official_form_questions(session, case, questions)

    research = await _research_for_case(session, case)
    if research is not None and _effective_research_status(research) == "completed":
        questions = research_questions(research.payload)
        if questions:
            return await _with_official_form_questions(session, case, questions)

    # When research is running in the background or no specific pack exists yet,
    # provide the universal baseline questionnaire so the user can immediately fill out
    # personal & passport data with zero perceived delay!
    return list(UNIVERSAL_BASELINE_QUESTIONS)


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


def _clean_scope_part(text: str | None) -> str | None:
    """Shorten verbose route/procedure names to concise, meaningful labels."""
    if not text:
        return None
    import re

    # Remove parenthetical details: (Engineer / Specialist...) or (Study at...)
    cleaned = re.sub(r"\s*\([^)]*\)", "", text).strip()
    # Remove secondary glosses after " - "
    if " - " in cleaned:
        cleaned = cleaned.split(" - ")[0].strip()
    return cleaned or text


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
            _clean_scope_part(jurisdiction.name if jurisdiction else None),
            _clean_scope_part(visa.name if visa else None),
            _clean_scope_part(action.name if action else None),
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


def _case_deadlines(
    case: Case, action_code: str | None, jurisdiction_code: str | None
) -> dict[str, object] | None:
    """Derive the deadline profile from the residence-card expiry intake answer.

    Returns ``None`` when no expiry is known yet (the applicant has not reached that intake
    branch). ``action_code`` (e.g. ``extend`` / ``change`` / ``new_application``) decides
    whether a grace period applies, and ``jurisdiction_code`` decides whose statute says so
    — Japan's 特例期間 is Japan's, and a case in another country gets its own rules or none.
    """
    expiry = (case.intake_answers or {}).get("residence_card_expiry")
    procedure = (action_code or "").replace("_", "").lower()
    if expiry is None:
        return None
    return compute_deadlines(str(expiry), procedure, jurisdiction=jurisdiction_code).to_dict()


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
        else:
            intake_questions = list(UNIVERSAL_BASELINE_QUESTIONS)
    else:
        has_intake = True
        intake_questions = list(UNIVERSAL_BASELINE_QUESTIONS)

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
        deadlines=_case_deadlines(case, a_code, j_code),
    )
    steps = research_progress_steps(research.payload if research is not None else None)
    _ = (j_code, v_code, a_code)
    track_meta = resolve_submission_track(
        jurisdiction_code=j_code,
        visa_category_code=v_code,
        research_route=(
            (research.payload or {}).get("admission", {}).get("route")
            if research and research.payload
            else None
        ),
    )
    return GuidanceOut.model_validate(
        {
            **guidance.model_dump(),
            "research_status": research_status,
            "research_steps": steps,
            "submission_track": track_meta.track.value,
            "track_summary": track_meta.model_dump(),
        }
    )


async def _enrich_case(session: AsyncSession, case: Case) -> CaseOut:
    j_code, v_code, a_code, label = await _scope_label(session, case)
    guidance = await _case_guidance(session, case)
    email = case.applicant_email
    if not email and case.user_id:
        owner = await session.get(User, case.user_id)
        if owner:
            email = owner.email
    base = CaseOut.model_validate(case)
    return base.model_copy(
        update={
            "jurisdiction_code": j_code,
            "visa_category_code": v_code,
            "case_action_code": a_code,
            "scope_label": label,
            "next_phase": guidance.phase,
            "next_title": guidance.title,
            "applicant_email": email,
            "submission_track": guidance.submission_track,
            "track_summary": guidance.track_summary,
        }
    )


# ── List / intake / get / save ────────────────────────────────────────────────


@router.get("", response_model=list[CaseOut])
async def list_cases(
    session: SessionDep,
    user: CurrentUserDep,
) -> list[CaseOut]:
    """List the current user's cases (or all cases if staff/admin) (US-03.3, US-03.4)."""
    if user.role in (UserRole.ADMIN, UserRole.OPS):
        stmt = select(Case).order_by(Case.created_at.desc())
    else:
        stmt = select(Case).where(Case.user_id == user.id).order_by(Case.created_at.desc())
    result = await session.execute(stmt)
    cases = list(result.scalars().all())
    if not cases:
        return []

    jurisdiction_ids = {c.jurisdiction_id for c in cases if c.jurisdiction_id}
    visa_category_ids = {c.visa_category_id for c in cases if c.visa_category_id}
    case_action_ids = {c.case_action_id for c in cases if c.case_action_id}

    jurisdictions = (
        {
            j.id: j
            for j in (
                await session.scalars(
                    select(Jurisdiction).where(Jurisdiction.id.in_(jurisdiction_ids))
                )
            ).all()
        }
        if jurisdiction_ids
        else {}
    )
    visa_categories = (
        {
            v.id: v
            for v in (
                await session.scalars(
                    select(VisaCategory).where(VisaCategory.id.in_(visa_category_ids))
                )
            ).all()
        }
        if visa_category_ids
        else {}
    )
    case_actions = (
        {
            a.id: a
            for a in (
                await session.scalars(select(CaseAction).where(CaseAction.id.in_(case_action_ids)))
            ).all()
        }
        if case_action_ids
        else {}
    )

    out: list[CaseOut] = []
    for case in cases:
        j = jurisdictions.get(case.jurisdiction_id)
        v = visa_categories.get(case.visa_category_id) if case.visa_category_id else None
        a = case_actions.get(case.case_action_id) if case.case_action_id else None
        j_code = j.code if j else None
        v_code = v.code if v else None
        a_code = a.code if a else None
        parts = [
            p
            for p in (
                _clean_scope_part(j.name if j else None),
                _clean_scope_part(v.name if v else None),
                _clean_scope_part(a.name if a else None),
            )
            if p
        ]
        label = " · ".join(parts) if parts else None

        next_phase = "intake"
        next_title = "Answer the intake questions"
        if case.status == "submitted":
            next_phase = "done"
            next_title = "Application submitted"
        elif case.status == "packet_ready":
            next_phase = "packet"
            next_title = "Review and download your packet"
        elif case.status == "forms_generated":
            next_phase = "review"
            next_title = "Review your case"
        elif case.status == "checklist_ready":
            next_phase = "forms"
            next_title = "Generate your application forms"
        elif case.status == "intake_complete":
            next_phase = "eligibility"
            next_title = "Check eligibility"
        elif case.intake_answers and len(case.intake_answers) > 0:
            next_phase = "intake"
            next_title = "Continue intake"

        track_meta = resolve_submission_track(
            jurisdiction_code=j_code,
            visa_category_code=v_code,
        )
        base = CaseOut.model_validate(case)
        out.append(
            base.model_copy(
                update={
                    "jurisdiction_code": j_code,
                    "visa_category_code": v_code,
                    "case_action_code": a_code,
                    "scope_label": label,
                    "next_phase": next_phase,
                    "next_title": next_title,
                    "submission_track": track_meta.track.value,
                    "track_summary": track_meta.model_dump(),
                }
            )
        )
    return out


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
        parsed_q = parse_questions(
            questions, jurisdiction_code=j_code or "", visa_category=v_code or ""
        )
        case.intake_answers = prune_answers(parsed_q, current_answers)
        await session.flush()

    return _intake_state(
        case, questions, jurisdiction_code=j_code or "JP", visa_category=v_code or ""
    )


INTAKE_KEY_ALIASES: dict[str, list[str]] = {
    "corporate_number": ["employer_corporate_number", "company_number", "organization_number"],
    "employer_corporate_number": ["corporate_number", "company_number", "organization_number"],
    "employer_name": [
        "company_name",
        "sponsoring_organization",
        "host_company_name",
        "sponsor_name",
    ],
    "company_name": ["employer_name", "sponsoring_organization", "sponsor_name"],
    "sponsor_name": ["employer_name", "company_name", "sponsoring_organization"],
    "monthly_salary": ["salary_monthly", "income_monthly", "salary"],
    "salary_monthly": ["monthly_salary", "income_monthly", "salary"],
    "salary": ["monthly_salary", "salary_monthly", "annual_salary_jpy", "income_monthly"],
    "annual_salary_jpy": ["salary", "monthly_salary", "salary_monthly"],
    "attendance_rate": ["attendance_percentage", "school_attendance_rate"],
    "attendance_percentage": ["attendance_rate", "school_attendance_rate"],
    "purpose_of_visit": ["main_purpose", "purpose", "visit_purpose"],
    "main_purpose": ["purpose_of_visit", "purpose", "visit_purpose"],
    "intended_length_of_stay_days": [
        "stay_duration_days",
        "length_of_stay_days",
        "stay_days",
        "duration_of_stay",
    ],
    "stay_duration_days": [
        "intended_length_of_stay_days",
        "length_of_stay_days",
        "stay_days",
        "duration_of_stay",
    ],
    "length_of_stay_days": [
        "intended_length_of_stay_days",
        "stay_duration_days",
        "stay_days",
        "duration_of_stay",
    ],
    "stay_days": [
        "intended_length_of_stay_days",
        "stay_duration_days",
        "length_of_stay_days",
        "duration_of_stay",
    ],
    "support_type": [
        "financial_support_type",
        "visitor_has_sufficient_funds",
        "has_sufficient_funds",
    ],
    "financial_support_type": [
        "support_type",
        "visitor_has_sufficient_funds",
        "has_sufficient_funds",
    ],
    "visitor_has_sufficient_funds": [
        "has_sufficient_funds",
        "support_type",
        "financial_support_type",
    ],
    "has_sufficient_funds": [
        "visitor_has_sufficient_funds",
        "support_type",
        "financial_support_type",
    ],
    "passport_number": ["passport_no", "passport"],
    "passport_no": ["passport_number", "passport"],
    "birth_date": ["date_of_birth", "dob"],
    "date_of_birth": ["birth_date", "dob"],
    "current_japan_address": [
        "registered_address_japan",
        "address_in_japan",
        "japan_address",
        "residential_address_japan",
    ],
    "registered_address_japan": [
        "current_japan_address",
        "address_in_japan",
        "japan_address",
        "residential_address_japan",
    ],
    "address_in_japan": ["current_japan_address", "registered_address_japan", "japan_address"],
    "telephone_japan": ["phone_number", "contact_phone", "phone_japan", "telephone_number"],
    "phone_number": ["telephone_japan", "mobile_phone", "contact_phone", "phone_japan"],
    "mobile_phone": ["mobile_phone_japan", "phone_number", "cell_phone"],
    "mobile_phone_japan": ["mobile_phone", "phone_number"],
    "current_status_of_residence": [
        "current_visa_status",
        "current_residence_status",
        "status_of_residence",
    ],
    "current_visa_status": ["current_status_of_residence", "current_residence_status"],
    "current_period_of_stay": ["current_period_of_stay_years", "period_of_stay"],
    "current_period_of_stay_years": ["current_period_of_stay", "period_of_stay"],
    "current_status_expiry_date": [
        "current_stay_expiry_date",
        "residence_card_expiry",
        "expiry_date_stay",
    ],
    "current_stay_expiry_date": ["current_status_expiry_date", "residence_card_expiry"],
    "residence_card_expiry": ["current_status_expiry_date", "current_stay_expiry_date"],
    "residence_card_number": ["residence_card_no", "alien_registration_number"],
    "place_of_birth": ["birth_place", "city_of_birth"],
    "home_town_city": ["home_city", "hometown", "city_in_home_country"],
    "desired_period_of_stay": ["desired_period", "desired_extension_days", "desired_stay_duration"],
    "reason_for_extension": [
        "extension_explanation_details",
        "reason_for_change",
        "reason_for_application",
    ],
    "criminal_record": ["criminal_record_any", "criminal_disclosures", "has_criminal_record"],
    "has_family_in_japan": ["family_in_japan", "relatives_in_japan"],
    "employer_address": ["place_of_employment_address", "company_address"],
    "employer_phone": ["place_of_employment_tel", "company_phone", "employer_telephone"],
    "education_level": ["final_education", "highest_education"],
    "school_name": ["institution_name", "last_school_attended"],
    "major_field": ["field_of_study", "major"],
    "graduation_date": ["graduation_year_month", "date_of_graduation"],
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
        jurisdiction_code=j_code or "",
        visa_category=v_code or "",
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
        # Check statutory form questions from _form_questions.yml
        try:
            from torii_api.services.jp_official_forms import _load_question_specs

            specs = _load_question_specs()
            spec = specs.get(target_key)
            if spec is None:
                for alias in INTAKE_KEY_ALIASES.get(target_key, []):
                    if alias in specs:
                        spec = specs[alias]
                        break
            if spec is not None:
                from torii_api.services.intake import IntakeQuestion

                question = IntakeQuestion(
                    key=target_key,
                    prompt=spec.prompt,
                    type=cast(QuestionType, spec.type),
                    section=spec.section or "Official Form Details",
                    options=list(spec.options) if spec.options else None,
                    required=False,
                )
                questions.append(question)
                by_key[target_key] = question
        except Exception:
            pass

    if question is None:
        # Form field or statutory answer submitted directly from Forms step
        val = payload.value
        current = dict(case.intake_answers or {})
        current[target_key] = val
        case.intake_answers = current
        case.intake_step = target_key
        case.review_flags_acknowledged = False
        await session.flush()
        return _intake_state(
            case,
            [q.model_dump() for q in questions],
            jurisdiction_code=j_code or "JP",
            visa_category=v_code or "",
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

    merged = {**current, target_key: val, payload.key: val}
    for alias in INTAKE_KEY_ALIASES.get(payload.key, []):
        if alias not in merged:
            merged[alias] = val
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
        case,
        [q.model_dump() for q in questions],
        jurisdiction_code=j_code or "JP",
        visa_category=v_code or "",
    )
    if state.progress.complete:
        new_status = next_status_for_phase("eligibility", case.status)
        if new_status is not None:
            case.status = new_status
    await session.flush()
    await session.refresh(case)
    return _intake_state(
        case,
        [q.model_dump() for q in questions],
        jurisdiction_code=j_code or "JP",
        visa_category=v_code or "",
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
    if "is_archived" in data and data["is_archived"] is not None:
        case.is_archived = data["is_archived"]
    if "submission_reference" in data:
        case.submission_reference = data["submission_reference"]
    if "status" in data and data["status"]:
        if data["status"] == "submitted":
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
                    detail=f"Cannot submit application: {len(missing_required)} required document(s) must be uploaded first.",
                )
        case.status = data["status"]
    await session.flush()
    await session.refresh(case)
    return await _enrich_case(session, case)


@router.post("/{case_id}/archive", response_model=CaseOut)
async def archive_case(
    case_id: int,
    session: SessionDep,
    user: CurrentUserDep,
) -> CaseOut:
    """Archive a case so it is hidden from the active view without deleting records."""
    case = await _owned_case(session, case_id, user)
    case.is_archived = True
    await session.flush()
    await session.refresh(case)
    return await _enrich_case(session, case)


@router.post("/{case_id}/unarchive", response_model=CaseOut)
async def unarchive_case(
    case_id: int,
    session: SessionDep,
    user: CurrentUserDep,
) -> CaseOut:
    """Restore an archived case to the active cases view."""
    case = await _owned_case(session, case_id, user)
    case.is_archived = False
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
