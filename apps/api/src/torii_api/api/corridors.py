"""Corridor admissibility check (docs/plan/03_corridor_bd_jp.md) — stage zero, pre-case.

``POST /v1/corridors/check`` answers the applicant's first question — is a visa needed, what
route, who is permitted to file, where, and (if published) the fee and processing time — before
a case is created. Resolved live via the agentic ``admissibility`` stage and cached per
``scope_key`` (destination + purpose + action + nationality + residence), shared across every
applicant on the same corridor until the cache expires
(:data:`services.agentic.ADMISSIBILITY_TTL_DAYS`).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from torii_api.auth.deps import CurrentUserDep, SessionDep, SettingsDep
from torii_api.db.models import CaseStageResearch, OutboxEvent, ScopeResearchStatus
from torii_api.services.agentic import find_admissibility, scope_key, stage_is_usable
from torii_api.services.rate_limiter import ResearchBudgetTracker, check_rate_limit

router = APIRouter(prefix="/v1/corridors", tags=["corridors"])


class CorridorCheckIn(BaseModel):
    destination_code: str = Field(min_length=2, max_length=8, examples=["JP"])
    purpose_code: str = Field(min_length=1, max_length=32, examples=["tourist"])
    action_code: str = Field(min_length=1, max_length=32, examples=["new_application"])
    nationality: Annotated[str | None, Field(max_length=8, examples=["BD"])] = None
    residence_country: Annotated[str | None, Field(max_length=8, examples=["BD"])] = None


class CorridorCheckOut(BaseModel):
    id: int
    status: str
    items: dict[str, Any] = Field(default_factory=dict)
    source_pages: list[dict[str, Any]] = Field(default_factory=list)
    researched_at: str | None = None
    expires_at: str | None = None


def _normalize(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip().upper()
    return value or None


def _out(research: CaseStageResearch) -> CorridorCheckOut:
    effective_status = research.status
    if research.status == ScopeResearchStatus.COMPLETED and not stage_is_usable(research):
        effective_status = "stale"
    return CorridorCheckOut(
        id=research.id,
        status=effective_status,
        items=research.payload if research.status == ScopeResearchStatus.COMPLETED else {},
        source_pages=research.source_pages or [],
        researched_at=research.researched_at.isoformat() if research.researched_at else None,
        expires_at=research.expires_at.isoformat() if research.expires_at else None,
    )


@router.post("/check", response_model=CorridorCheckOut)
async def check_corridor(
    payload: CorridorCheckIn,
    session: SessionDep,
    user: CurrentUserDep,
    settings: SettingsDep,
    request: Request,
) -> CorridorCheckOut:
    """Resolve (or enqueue) the admissibility check for one corridor.

    Reuses a fresh cached result across every applicant on the same
    destination+purpose+action+nationality+residence combination; a stale, failed, or missing
    result is (re)enqueued via the ``case.stage_research.queued`` outbox topic and returned as
    ``"queued"`` for the client to poll ``GET /v1/corridors/{id}``.
    """
    # Abuse protection: per-user heavy rate limit on research queries (T-10)
    await check_rate_limit(
        request,
        limit=settings.rate_limit_heavy_per_minute,
        window_seconds=60,
        key_prefix="research:user",
        key_suffix=str(user.id),
        settings=settings,
    )
    # Enforce per-user monthly research budget independently of credits (T-10)
    await ResearchBudgetTracker().check_budget(user_id=user.id, settings=settings)

    destination = _normalize(payload.destination_code)
    nationality = _normalize(payload.nationality)
    residence = _normalize(payload.residence_country)
    if destination is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="destination_code is required"
        )

    key = scope_key(
        destination_code=destination,
        purpose_code=payload.purpose_code,
        action_code=payload.action_code,
        nationality=nationality,
        residence_country=residence,
    )

    research = await find_admissibility(session, key)
    if research is not None and stage_is_usable(research):
        return _out(research)
    if research is not None and research.status in (
        ScopeResearchStatus.QUEUED,
        ScopeResearchStatus.RUNNING,
    ):
        return _out(research)

    if research is None:
        research = CaseStageResearch(
            stage="admissibility",
            scope_key=key,
            status=ScopeResearchStatus.QUEUED,
            payload={},
            source_pages=[],
        )
        session.add(research)
    else:
        research.status = ScopeResearchStatus.QUEUED
        research.payload = {}
        research.source_pages = []
        research.error = None
        research.researched_at = None
        research.expires_at = None
    await session.flush()

    session.add(
        OutboxEvent(
            topic="case.stage_research.queued",
            payload={
                "stage_research_id": research.id,
                "stage": "admissibility",
                "destination_code": destination,
                "purpose_code": payload.purpose_code,
                "action_code": payload.action_code,
                "nationality": nationality,
                "residence_country": residence,
                "context": {},
                "queued_at": datetime.now(UTC).isoformat(),
            },
        )
    )
    await session.flush()
    return _out(research)


@router.get("/{corridor_id}", response_model=CorridorCheckOut)
async def get_corridor(
    corridor_id: int, session: SessionDep, user: CurrentUserDep
) -> CorridorCheckOut:
    """Poll a previously requested admissibility check by id."""
    research = await session.get(CaseStageResearch, corridor_id)
    if research is None or research.stage != "admissibility":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="corridor check not found"
        )
    return _out(research)
