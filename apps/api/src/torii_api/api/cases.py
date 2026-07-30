"""Cases — the core resource applicants and staff interact with.

US-01: Scoping a case to jurisdiction + visa category + action.
US-02: Branching intake questionnaire with validation and progress.
US-03: Persist progress so an applicant can stop and resume.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from torii_api.auth.deps import CurrentUserDep
from torii_api.db.models import (
    Case,
    CaseAction,
    IntakeDefinition,
    Jurisdiction,
    User,
    VisaCategory,
)
from torii_api.db.session import get_session
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
    locale: str = Field(default="en", min_length=2, max_length=16)


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


class IntakeAnswerIn(BaseModel):
    key: str = Field(min_length=1, max_length=64)
    value: bool | str | int | None = None


class IntakeStateOut(BaseModel):
    case_id: int
    questions: list[IntakeQuestion]
    answers: dict[str, Any]
    progress: IntakeProgress
    intake_step: str | None = None


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
    jurisdiction = await session.scalar(
        select(Jurisdiction).where(Jurisdiction.code == payload.jurisdiction_code.upper())
    )
    if jurisdiction is None or not jurisdiction.is_live:
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
    if visa_category is None or not visa_category.is_live:
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
    if case_action is None or not case_action.is_live:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"action '{payload.action_code}' is not available in {jurisdiction.code}",
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


# ── Shared helpers ────────────────────────────────────────────────────────────


async def _owned_case(session: AsyncSession, case_id: int, user: User) -> Case:
    """Load a case owned by ``user``, or raise 404 (no existence leak across owners)."""
    case = await session.scalar(select(Case).where(Case.id == case_id, Case.user_id == user.id))
    if case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"case {case_id} not found",
        )
    return case


async def _live_intake_definition(session: AsyncSession, case: Case) -> IntakeDefinition:
    """Resolve the live intake questionnaire for the case's scope."""
    if case.visa_category_id is None or case.case_action_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="case is not fully scoped for intake",
        )
    definition = await session.scalar(
        select(IntakeDefinition).where(
            IntakeDefinition.jurisdiction_id == case.jurisdiction_id,
            IntakeDefinition.visa_category_id == case.visa_category_id,
            IntakeDefinition.case_action_id == case.case_action_id,
            IntakeDefinition.is_live.is_(True),
        )
    )
    if definition is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="no live intake definition for this case scope",
        )
    return definition


def _intake_state(case: Case, definition: IntakeDefinition) -> IntakeStateOut:
    questions = parse_questions(definition.questions)
    answers = dict(case.intake_answers or {})
    return IntakeStateOut(
        case_id=case.id,
        questions=visible_questions(questions, answers),
        answers=answers,
        progress=progress_for(questions, answers),
        intake_step=case.intake_step,
    )


# ── List / intake / get / save ────────────────────────────────────────────────


@router.get("", response_model=list[CaseOut])
async def list_cases(
    session: SessionDep,
    user: CurrentUserDep,
) -> list[Case]:
    """List the current user's cases (US-03.3, US-03.4)."""
    result = await session.execute(
        select(Case).where(Case.user_id == user.id).order_by(Case.created_at.desc())
    )
    return list(result.scalars().all())


@router.get("/{case_id}/intake", response_model=IntakeStateOut)
async def get_intake(
    case_id: int,
    session: SessionDep,
    user: CurrentUserDep,
) -> IntakeStateOut:
    """Return visible intake questions, answers, and progress for a case (US-02)."""
    case = await _owned_case(session, case_id, user)
    definition = await _live_intake_definition(session, case)
    return _intake_state(case, definition)


@router.put("/{case_id}/intake/answer", response_model=IntakeStateOut)
async def answer_intake(
    case_id: int,
    payload: IntakeAnswerIn,
    session: SessionDep,
    user: CurrentUserDep,
) -> IntakeStateOut:
    """Validate and store one intake answer; re-branch and clear stale answers (US-02.3–02.5)."""
    case = await _owned_case(session, case_id, user)
    definition = await _live_intake_definition(session, case)
    questions = parse_questions(definition.questions)
    by_key = {q.key: q for q in questions}
    question = by_key.get(payload.key)
    if question is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"unknown question '{payload.key}'",
        )

    current = dict(case.intake_answers or {})
    if not is_visible(question, current):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"question '{payload.key}' is not applicable on the current branch",
        )

    error = validate_answer(question, payload.value)
    if error is not None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=error)

    merged = {**current, payload.key: payload.value}
    case.intake_answers = prune_answers(questions, merged)
    case.intake_step = payload.key
    case.review_flags_acknowledged = False
    await session.flush()
    await session.refresh(case)
    return _intake_state(case, definition)


@router.get("/{case_id}", response_model=CaseOut)
async def get_case(
    case_id: int,
    session: SessionDep,
    user: CurrentUserDep,
) -> Case:
    """Return a saved case with answers and position so the applicant can resume (US-03.2)."""
    return await _owned_case(session, case_id, user)


@router.patch("/{case_id}", response_model=CaseOut)
async def save_case_progress(
    case_id: int,
    payload: CaseProgressIn,
    session: SessionDep,
    user: CurrentUserDep,
) -> Case:
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
    return case
