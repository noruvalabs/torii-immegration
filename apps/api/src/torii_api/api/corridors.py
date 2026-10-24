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

import re
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from torii_api.auth.deps import OptionalUserDep, SessionDep
from torii_api.db.models import CaseStageResearch, OutboxEvent, ScopeResearchStatus
from torii_api.services.agentic import find_admissibility, scope_key, stage_is_usable

router = APIRouter(prefix="/v1/corridors", tags=["corridors"])


class CorridorCheckIn(BaseModel):
    destination_code: str = Field(min_length=2, max_length=8, examples=["JP"])
    purpose_code: str = Field(min_length=1, max_length=32, examples=["tourist"])
    action_code: str = Field(min_length=1, max_length=32, examples=["new_application"])
    nationality: Annotated[str | None, Field(max_length=8, examples=["BD"])] = None
    residence_country: Annotated[str | None, Field(max_length=8, examples=["BD"])] = None
    force_refresh: bool = False


class CorridorCheckOut(BaseModel):
    id: int
    status: str
    items: dict[str, Any] = Field(default_factory=dict)
    source_pages: list[dict[str, Any]] = Field(default_factory=list)
    researched_at: str | None = None
    expires_at: str | None = None
    review_required: bool = False
    verification_status: str | None = None
    retrieval_status: str | None = None
    source_domains: list[str] = Field(default_factory=list)
    error_diagnostics: str | None = None
    failure_reason: str | None = None


def _normalize(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip().upper()
    return value or None


def _sanitize_diagnostics(error: str | None, is_anonymous: bool = False) -> str | None:
    if not error:
        return None
    err_lower = error.lower()
    # Mask stack traces, sql, secrets
    if any(k in err_lower for k in ("traceback", "file \"", "select ", "insert ", "update ", "delete ")):
        return "Internal retrieval diagnostic error (sanitized)"
    if any(k in err_lower for k in ("api_key", "secret", "token", "password", "bearer")):
        return "Authentication or authorization failure on external provider"
    if "127.0.0.1" in error or "localhost" in error:
        error = re.sub(r"http://[a-zA-Z0-9_\-\.:]+", "http://[internal-host]", error)
    if is_anonymous:
        if "inaccessible" in err_lower or "403" in err_lower:
            return "Official source pages were inaccessible (HTTP 403 or timeout)"
        if "conflict" in err_lower:
            return "Official sources reported conflicting or ambiguous visa requirements"
        if "incomplete" in err_lower:
            return "Official source evidence was incomplete and requires review"
        if "insufficient" in err_lower or "no readable" in err_lower:
            return "Insufficient evidence found on official authority pages"
        return "Unable to verify requirements from official government sources"
    return error[:300]


def _out(research: CaseStageResearch, user: OptionalUserDep = None) -> CorridorCheckOut:
    effective_status = research.status
    is_stale = False
    if research.status == ScopeResearchStatus.COMPLETED and not stage_is_usable(research):
        effective_status = "stale"
        is_stale = True

    meta = (research.payload or {}).get("_meta") or {}
    source_pages = research.source_pages or []
    extracted_domains = {
        urlparse(p.get("url", "")).hostname
        for p in source_pages
        if isinstance(p, dict) and p.get("url") and urlparse(p.get("url", "")).hostname
    }
    source_domains = meta.get("source_domains") or sorted(list(extracted_domains))

    is_anon = user is None
    raw_error = research.error or meta.get("error_diagnostics") or meta.get("failure_reason")
    sanitized_error = _sanitize_diagnostics(raw_error, is_anonymous=is_anon)

    if effective_status == ScopeResearchStatus.COMPLETED and not is_stale:
        default_verif = "verified"
        default_review = False
    elif is_stale:
        default_verif = "unverified"
        default_review = True
    elif effective_status == ScopeResearchStatus.FAILED:
        default_verif = "failed"
        default_review = True
    else:
        default_verif = "unverified"
        default_review = False

    verification_status = meta.get("verification_status") or default_verif
    if is_stale:
        verification_status = "unverified"

    review_required = bool(
        meta.get(
            "review_required",
            default_review or effective_status in (ScopeResearchStatus.FAILED, "stale"),
        )
    )

    retrieval_status = meta.get("retrieval_status") or (
        "direct_scrape" if effective_status == ScopeResearchStatus.COMPLETED else "failed"
    )

    clean_items = {k: v for k, v in (research.payload or {}).items() if k != "_meta"}

    return CorridorCheckOut(
        id=research.id,
        status=effective_status,
        items=clean_items if (research.status == ScopeResearchStatus.COMPLETED and not is_stale) else {},
        source_pages=source_pages,
        researched_at=research.researched_at.isoformat() if research.researched_at else None,
        expires_at=research.expires_at.isoformat() if research.expires_at else None,
        review_required=review_required,
        verification_status=verification_status,
        retrieval_status=retrieval_status,
        source_domains=source_domains,
        error_diagnostics=sanitized_error,
        failure_reason=sanitized_error,
    )


@router.post("/check", response_model=CorridorCheckOut)
async def check_corridor(
    payload: CorridorCheckIn, session: SessionDep, user: OptionalUserDep = None
) -> CorridorCheckOut:
    """Resolve (or enqueue) the admissibility check for one corridor.

    Reuses a fresh cached result across every applicant on the same
    destination+purpose+action+nationality+residence combination; a stale, failed, or missing
    result (or when force_refresh=True) is (re)enqueued via the ``case.stage_research.queued``
    outbox topic and returned as ``"queued"`` for the client to poll ``GET /v1/corridors/{id}``.
    """
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
    if not payload.force_refresh:
        if research is not None and stage_is_usable(research):
            return _out(research, user=user)
        if research is not None and research.status in (
            ScopeResearchStatus.QUEUED,
            ScopeResearchStatus.RUNNING,
        ):
            return _out(research, user=user)

    current_meta = (research.payload or {}).get("_meta") or {} if research else {}
    new_generation = int(current_meta.get("generation", 0)) + 1

    if research is None:
        research = CaseStageResearch(
            stage="admissibility",
            scope_key=key,
            status=ScopeResearchStatus.QUEUED,
            payload={"_meta": {"generation": new_generation}},
            source_pages=[],
        )
        session.add(research)
    else:
        research.status = ScopeResearchStatus.QUEUED
        # Preserve existing payload and source_pages with incremented generation for concurrency guard
        new_payload = dict(research.payload or {})
        new_meta = dict(current_meta)
        new_meta["generation"] = new_generation
        new_payload["_meta"] = new_meta
        research.payload = new_payload
        research.error = None
    await session.flush()

    session.add(
        OutboxEvent(
            topic="case.stage_research.queued",
            payload={
                "stage_research_id": research.id,
                "job_generation": new_generation,
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
    return _out(research, user=user)


@router.get("/{corridor_id}", response_model=CorridorCheckOut)
async def get_corridor(
    corridor_id: int, session: SessionDep, user: OptionalUserDep = None
) -> CorridorCheckOut:
    """Poll a previously requested admissibility check by id."""
    research = await session.get(CaseStageResearch, corridor_id)
    if research is None or research.stage != "admissibility":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="corridor check not found"
        )
    return _out(research, user=user)

