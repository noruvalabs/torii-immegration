"""Agentic per-stage research API (docs/plan/03_corridor_bd_jp.md, Decisions §2).

POST /ai/agentic/research-stage — run one pipeline stage's live LLM+search research for a case
(or, for ``"admissibility"``, a bare scope + nationality + residence — no case exists yet).
Called by ``apps/api``'s worker; never directly by the applicant's browser.
"""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from torii_ai.config import Settings, get_settings
from torii_ai.llm.groq import FakeChatClient, GroqChatClient
from torii_ai.llm.nvidia import NvidiaChatClient
from torii_ai.services.agentic_research import AgenticStageResearcher, Stage, StageResearchRequest
from torii_ai.services.case_plan import AICasePlanner, CasePlanRequest
from torii_ai.services.doc_drafter import AIDocDrafter, AIDraftRequest
from torii_ai.services.eligibility_evaluator import (
    AIElegibilityEvaluator,
    AIEvaluationRequest,
)
from torii_ai.tools.tavily import FakeSearchClient, TavilyClient

log = structlog.get_logger()

router = APIRouter(prefix="/ai/agentic", tags=["agentic"])


class StageResearchIn(BaseModel):
    stage: Stage
    destination_code: str = Field(min_length=2, max_length=16, examples=["JP"])
    purpose_code: str = Field(min_length=1, max_length=32, examples=["tourist"])
    action_code: str = Field(min_length=1, max_length=32, examples=["new_application"])
    nationality: str | None = Field(default=None, max_length=64, examples=["BD"])
    residence_country: str | None = Field(default=None, max_length=64, examples=["BD"])
    # Stage-defined accumulated context — see agentic_research.StageResearchRequest.
    context: dict[str, Any] = Field(default_factory=dict)


class StageResearchOut(BaseModel):
    stage: Stage
    items: dict[str, Any]
    source_pages: list[dict[str, Any]]
    insufficient: bool
    researched_at: str


class AIEvaluateEligibilityIn(BaseModel):
    destination_code: str = Field(min_length=2, max_length=16, examples=["JP"])
    purpose_code: str = Field(min_length=1, max_length=32, examples=["tourist"])
    action_code: str = Field(min_length=1, max_length=32, examples=["new_application"])
    nationality: str | None = Field(default=None, max_length=64, examples=["BD"])
    residence_country: str | None = Field(default=None, max_length=64, examples=["BD"])
    answers: dict[str, Any] = Field(default_factory=dict)
    rules: list[dict[str, Any]] = Field(default_factory=list)
    context: dict[str, Any] = Field(default_factory=dict)


class AIEvaluateEligibilityOut(BaseModel):
    result: str
    findings: list[dict[str, Any]]
    disclaimer: str
    summary: str | None = None


class DraftDocumentIn(BaseModel):
    doc_type: str = Field(min_length=1, max_length=64)
    jurisdiction_code: str = Field(default="JP", max_length=16)
    scope_label: str = Field(default="Immigration Visa Application", max_length=255)
    case_reference: str = Field(default="CASE-1", max_length=64)
    intake_answers: dict[str, Any] = Field(default_factory=dict)
    checklist: list[dict[str, Any]] = Field(default_factory=list)
    custom_instructions: str | None = None
    locale: str = Field(default="en", max_length=16)


class DraftDocumentOut(BaseModel):
    doc_type: str
    title: str
    content: str
    model_used: str
    generated_at: str


class CasePlanIn(BaseModel):
    scope_label: str = Field(default="Immigration application", max_length=255)
    destination_code: str = Field(default="", max_length=16)
    nationality: str | None = Field(default=None, max_length=64)
    residence_country: str | None = Field(default=None, max_length=64)
    case_reference: str = Field(default="", max_length=64)
    intake_answers: dict[str, Any] = Field(default_factory=dict)
    checklist: list[dict[str, Any]] = Field(default_factory=list)
    # The requirements that come from a bank, an airline, an employer or another
    # government — their lead times are what the plan is ordered by.
    external_tasks: list[dict[str, Any]] = Field(default_factory=list)
    stages: list[dict[str, Any]] = Field(default_factory=list)
    office: str | None = Field(default=None, max_length=500)
    filed_by: str | None = Field(default=None, max_length=500)
    fee_note: str | None = Field(default=None, max_length=500)
    notes: list[str] = Field(default_factory=list)
    submitted: bool = False
    custom_instructions: str | None = Field(default=None, max_length=2000)
    locale: str = Field(default="en", max_length=16)


class PlanAction(BaseModel):
    title: str
    detail: str = ""
    lead_time: str | None = None


class CasePlanOut(BaseModel):
    headline: str
    ready_to_file: bool
    time_to_ready: str | None = None
    start_now: list[PlanAction] = Field(default_factory=list)
    then: list[PlanAction] = Field(default_factory=list)
    risks: list[PlanAction] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)
    disclaimer: str
    model_used: str
    generated_at: str


def _build_researcher(settings: Settings) -> AgenticStageResearcher:
    """Real Tavily/LLM clients when configured, fake stand-ins otherwise (local dev/tests)."""
    search = TavilyClient(settings) if settings.tavily_api_key else FakeSearchClient()
    if settings.groq_api_key:
        chat = GroqChatClient(settings, model=settings.groq_extract_model or settings.groq_model)
    elif settings.nvidia_api_key:
        chat = NvidiaChatClient(settings)
    else:
        chat = FakeChatClient()
    return AgenticStageResearcher(search=search, chat=chat, settings=settings)


def _build_evaluator(settings: Settings) -> AIElegibilityEvaluator:
    if settings.groq_api_key:
        chat = GroqChatClient(settings, model=settings.groq_extract_model or settings.groq_model)
    elif settings.nvidia_api_key:
        chat = NvidiaChatClient(settings)
    else:
        chat = FakeChatClient()
    return AIElegibilityEvaluator(chat=chat, settings=settings)


def _build_drafter(settings: Settings) -> AIDocDrafter:
    if settings.groq_api_key:
        chat = GroqChatClient(settings, model=settings.groq_extract_model or settings.groq_model)
    elif settings.nvidia_api_key:
        chat = NvidiaChatClient(settings)
    else:
        chat = FakeChatClient()
    return AIDocDrafter(chat=chat, settings=settings)


def _build_planner(settings: Settings) -> AICasePlanner:
    if settings.groq_api_key:
        # The output budget is the whole story here. Groq counts the *reserved* budget
        # against the tokens-per-minute allowance, so the account default of 8000 reserved
        # the entire minute for one short reply — slow, and the next call comes back 429.
        #
        # It cannot go too low either: these are reasoning models that spend tokens on a
        # <think> block before the JSON, and a budget that truncates mid-deliberation
        # yields nothing parseable and silently falls back. 2500 leaves room for both.
        chat = GroqChatClient(
            settings,
            model=settings.groq_extract_model or settings.groq_model,
            max_tokens=2500,
        )
    elif settings.nvidia_api_key:
        chat = NvidiaChatClient(settings)
    else:
        chat = FakeChatClient()
    return AICasePlanner(chat=chat, settings=settings)


@router.post("/research-stage", response_model=StageResearchOut)
async def research_stage(payload: StageResearchIn) -> StageResearchOut:
    """Run one pipeline stage's live research and return its cited, stage-shaped payload."""
    settings = get_settings()
    researcher = _build_researcher(settings)
    request = StageResearchRequest(
        stage=payload.stage,
        destination_code=payload.destination_code,
        purpose_code=payload.purpose_code,
        action_code=payload.action_code,
        nationality=payload.nationality,
        residence_country=payload.residence_country,
        context=payload.context,
    )
    log.info(
        "agentic.research_stage.start",
        stage=payload.stage,
        destination=payload.destination_code,
        nationality=payload.nationality,
    )
    try:
        result = await researcher.research_stage(request)
    except Exception as exc:
        log.error("agentic.research_stage.failed", stage=payload.stage, error=str(exc))
        raise HTTPException(status_code=500, detail=f"Stage research failed: {exc}") from exc

    return StageResearchOut(
        stage=result.stage,
        items=result.items,
        source_pages=result.source_pages,
        insufficient=result.insufficient,
        researched_at=result.researched_at,
    )


@router.post("/evaluate-eligibility", response_model=AIEvaluateEligibilityOut)
async def evaluate_eligibility_endpoint(
    payload: AIEvaluateEligibilityIn,
) -> AIEvaluateEligibilityOut:
    """Run AI-assisted eligibility screening on applicant answers."""
    settings = get_settings()
    evaluator = _build_evaluator(settings)
    request = AIEvaluationRequest(
        destination_code=payload.destination_code,
        purpose_code=payload.purpose_code,
        action_code=payload.action_code,
        nationality=payload.nationality,
        residence_country=payload.residence_country,
        answers=payload.answers,
        rules=payload.rules,
        context=payload.context,
    )
    log.info(
        "agentic.evaluate_eligibility.start",
        destination=payload.destination_code,
        purpose=payload.purpose_code,
        nationality=payload.nationality,
    )
    try:
        result = await evaluator.evaluate(request)
    except Exception as exc:
        log.error("agentic.evaluate_eligibility.failed", error=str(exc))
        raise HTTPException(
            status_code=500, detail=f"AI eligibility evaluation failed: {exc}"
        ) from exc

    return AIEvaluateEligibilityOut(
        result=result.get("result", "pass"),
        findings=result.get("findings", []),
        disclaimer=result.get(
            "disclaimer",
            "This is an AI-assisted preparation check based on official published criteria, not legal advice or a government decision.",
        ),
        summary=result.get("summary"),
    )


@router.post("/draft-document", response_model=DraftDocumentOut)
async def draft_document_endpoint(payload: DraftDocumentIn) -> DraftDocumentOut:
    """Dynamically generate official customized legal documents tailored to applicant case."""
    settings = get_settings()
    drafter = _build_drafter(settings)
    req = AIDraftRequest(
        doc_type=payload.doc_type,
        jurisdiction_code=payload.jurisdiction_code,
        scope_label=payload.scope_label,
        case_reference=payload.case_reference,
        intake_answers=payload.intake_answers,
        checklist=payload.checklist,
        custom_instructions=payload.custom_instructions,
        locale=payload.locale,
    )
    log.info(
        "agentic.draft_document.start",
        doc_type=payload.doc_type,
        case=payload.case_reference,
        jurisdiction=payload.jurisdiction_code,
    )
    try:
        result = await drafter.draft_document(req)
    except Exception as exc:
        log.error("agentic.draft_document.failed", error=str(exc))
        raise HTTPException(
            status_code=500, detail=f"AI document drafting failed: {exc}"
        ) from exc

    return DraftDocumentOut(**result)


@router.post("/case-plan", response_model=CasePlanOut)
async def case_plan_endpoint(payload: CasePlanIn) -> CasePlanOut:
    """Reduce a whole case to a short action plan: what to start today, then, and the risks.

    The applicant's step view can draw every stage of the process, but sixteen numbered
    steps is a diagram of the procedure rather than advice about their application. This
    reads the same data — their answers, their outstanding documents, what has to come
    from a bank or an airline and how long each takes, the cited filing route — and
    returns the short version an adviser would actually say out loud.
    """
    settings = get_settings()
    planner = _build_planner(settings)
    request = CasePlanRequest(
        scope_label=payload.scope_label,
        destination_code=payload.destination_code,
        nationality=payload.nationality,
        residence_country=payload.residence_country,
        case_reference=payload.case_reference,
        intake_answers=payload.intake_answers,
        checklist=payload.checklist,
        external_tasks=payload.external_tasks,
        stages=payload.stages,
        office=payload.office,
        filed_by=payload.filed_by,
        fee_note=payload.fee_note,
        notes=payload.notes,
        submitted=payload.submitted,
        custom_instructions=payload.custom_instructions,
        locale=payload.locale,
    )
    log.info("agentic.case_plan.start", case=payload.case_reference, scope=payload.scope_label)
    try:
        result = await planner.plan(request)
    except Exception as exc:
        log.error("agentic.case_plan.failed", error=str(exc))
        raise HTTPException(status_code=500, detail=f"AI case planning failed: {exc}") from exc

    return CasePlanOut(**result)
