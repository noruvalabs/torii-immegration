"""On-demand live-research content (ScopeResearch) resolution helpers.

A scope with no live content pack is researched live (``case.research.queued`` outbox →
``POST /ai/ops/scrape`` → validated) and cached in :class:`ScopeResearch`, keyed by
scope + origin_country + residence_country. The deterministic engine consumes the cached
payload exactly as it would seeded definitions; the LLM proposes, this engine never infers
(NF-1), and every item must already carry an official-source citation (NF-2).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from torii_api.db.models import ScopeResearch, ScopeResearchStatus

# A completed research snapshot is reused for new cases of the same scope+origin+residence
# until this TTL elapses; past it, the scope endpoint enqueues a fresh run.
RESEARCH_TTL_DAYS = 7

# Payload slices — same vocabulary as the seeded definition tables.
PAYLOAD_QUESTIONS = "intake_questions"
PAYLOAD_RULES = "eligibility_rules"
PAYLOAD_DOCUMENTS = "document_requirements"
PAYLOAD_FORMS = "form_templates"


def research_expiry() -> datetime:
    """Default ``expires_at`` for a freshly completed research run."""
    return datetime.now(UTC) + timedelta(days=RESEARCH_TTL_DAYS)


def research_is_usable(research: ScopeResearch | None, now: datetime | None = None) -> bool:
    """True when a completed snapshot is still within its freshness window."""
    if research is None or research.status != ScopeResearchStatus.COMPLETED:
        return False
    if research.expires_at is None:
        return False
    return (now or datetime.now(UTC)) < research.expires_at


def research_slice(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    """Return one cached slice (safe against a missing/empty payload)."""
    if not isinstance(payload, dict):
        return []
    value = payload.get(key)
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def research_questions(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return research_slice(payload, PAYLOAD_QUESTIONS)


def research_rules(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return research_slice(payload, PAYLOAD_RULES)


def research_documents(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return research_slice(payload, PAYLOAD_DOCUMENTS)


def research_forms(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return research_slice(payload, PAYLOAD_FORMS)


async def research_for_case(
    session: AsyncSession, case_id: int, research_id: int | None
) -> ScopeResearch | None:
    """Load the research snapshot attached to a case, if any."""
    if research_id is None:
        return None
    return await session.get(ScopeResearch, research_id)


async def find_research(
    session: AsyncSession,
    *,
    jurisdiction_id: int,
    visa_category_id: int,
    case_action_id: int,
    origin_country: str | None,
    residence_country: str | None,
) -> ScopeResearch | None:
    """Resolve the cache row for a scope+origin+residence key (any status)."""
    stmt = select(ScopeResearch).where(
        ScopeResearch.jurisdiction_id == jurisdiction_id,
        ScopeResearch.visa_category_id == visa_category_id,
        ScopeResearch.case_action_id == case_action_id,
    )
    # SQL NULL-safe comparison: build equality that treats None and '' as absent.
    def _match(column: Any, value: str | None) -> Any:
        if value:
            return column == value
        return column.is_(None)

    stmt = stmt.where(
        _match(ScopeResearch.origin_country, origin_country),
        _match(ScopeResearch.residence_country, residence_country),
    )
    return await session.scalar(stmt)


def research_payload(
    *,
    intake_questions: list[dict[str, Any]],
    eligibility_rules: list[dict[str, Any]],
    document_requirements: list[dict[str, Any]],
    form_templates: list[dict[str, Any]],
) -> dict[str, Any]:
    """Normalize scraped slices into the ScopeResearch payload shape."""
    return {
        PAYLOAD_QUESTIONS: intake_questions,
        PAYLOAD_RULES: eligibility_rules,
        PAYLOAD_DOCUMENTS: document_requirements,
        PAYLOAD_FORMS: form_templates,
    }


def research_progress_steps(payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Return progressive step log written while research is running (for the UI)."""
    if not isinstance(payload, dict):
        return []
    raw = payload.get("_progress")
    if not isinstance(raw, list):
        return []
    steps: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        key = item.get("key")
        label = item.get("label")
        if not key or not label:
            continue
        steps.append(
            {
                "key": str(key),
                "label": str(label),
                "detail": str(item.get("detail") or ""),
                "at": str(item.get("at") or ""),
            }
        )
    return steps


__all__ = [
    "PAYLOAD_DOCUMENTS",
    "PAYLOAD_FORMS",
    "PAYLOAD_QUESTIONS",
    "PAYLOAD_RULES",
    "RESEARCH_TTL_DAYS",
    "find_research",
    "research_documents",
    "research_expiry",
    "research_for_case",
    "research_forms",
    "research_is_usable",
    "research_payload",
    "research_progress_steps",
    "research_questions",
    "research_rules",
    "research_slice",
]
