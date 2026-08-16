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
from torii_ai.tools.tavily import FakeSearchClient, TavilyClient

log = structlog.get_logger()

router = APIRouter(prefix="/ai/agentic", tags=["agentic"])


class StageResearchIn(BaseModel):
    stage: Stage
    destination_code: str = Field(min_length=2, max_length=8, examples=["JP"])
    purpose_code: str = Field(min_length=1, max_length=32, examples=["tourist"])
    action_code: str = Field(min_length=1, max_length=32, examples=["new_application"])
    nationality: str | None = Field(default=None, max_length=8, examples=["BD"])
    residence_country: str | None = Field(default=None, max_length=8, examples=["BD"])
    # Stage-defined accumulated context — see agentic_research.StageResearchRequest.
    context: dict[str, Any] = Field(default_factory=dict)


class StageResearchOut(BaseModel):
    stage: Stage
    items: dict[str, Any]
    source_pages: list[dict[str, Any]]
    insufficient: bool
    researched_at: str


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
