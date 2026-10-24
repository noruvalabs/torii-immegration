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
# until this TTL elapses (30 days); past it, the scope endpoint enqueues a fresh run.
RESEARCH_TTL_DAYS = 30

# Payload slices — same vocabulary as the seeded definition tables.
PAYLOAD_QUESTIONS = "intake_questions"
PAYLOAD_RULES = "eligibility_rules"
PAYLOAD_DOCUMENTS = "document_requirements"
PAYLOAD_FORMS = "form_templates"

# Slices the pre-case ``admissibility`` stage researches. These were produced by the agent
# and never read: the filing route, its steps and its fees were hardcoded per country
# instead, which is the NF-2 breach docs/plan/03_corridor_bd_jp.md records as G2.
PAYLOAD_PROCESS = "process"
PAYLOAD_FEES = "fees"
PAYLOAD_FILING_CHANNEL = "filing_channel"
PAYLOAD_ADMISSION = "admission"


def research_expiry() -> datetime:
    """Default ``expires_at`` for a freshly completed research run."""
    return datetime.now(UTC) + timedelta(days=RESEARCH_TTL_DAYS)


def research_is_usable(research: ScopeResearch | None, now: datetime | None = None) -> bool:
    """True when a completed snapshot is still within its freshness window."""
    if research is None or research.status != ScopeResearchStatus.COMPLETED:
        return False
    if research.expires_at is None:
        return False
    current = now or datetime.now(UTC)
    expires = research.expires_at
    if expires.tzinfo is None and current.tzinfo is not None:
        expires = expires.replace(tzinfo=UTC)
    elif expires.tzinfo is not None and current.tzinfo is None:
        current = current.replace(tzinfo=UTC)
    return current < expires


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


def _cited(item: dict[str, Any]) -> bool:
    """True when an item carries an official-source citation (NF-2).

    Discovered content reaches an applicant only if it says where it came from. An
    uncited step is dropped rather than shown, because a filing instruction nobody can
    check against a government page is the thing this gate exists to stop.
    """
    citation = item.get("citation")
    if not isinstance(citation, dict):
        return False
    return str(citation.get("url") or "").startswith("http")


def research_process_steps(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Ordered filing steps the agent discovered, cited and sorted.

    The step's own citation is used when it has one, else the ``process`` block's, since
    the agent cites the process as a whole and the individual steps come from that page.
    """
    if not isinstance(payload, dict):
        return []
    process = payload.get(PAYLOAD_PROCESS)
    if not isinstance(process, dict):
        return []
    block_citation = process.get("citation") if isinstance(process.get("citation"), dict) else None
    if not (_cited(process) or block_citation):
        return []

    steps: list[dict[str, Any]] = []
    for raw in process.get("steps") or []:
        if not isinstance(raw, dict):
            continue
        title = str(raw.get("title") or "").strip()
        if not title:
            continue
        step = dict(raw)
        step["title"] = title
        if not isinstance(step.get("citation"), dict) and block_citation:
            step["citation"] = block_citation
        if _cited(step):
            steps.append(step)
    steps.sort(key=lambda step: int(step.get("order") or 0))
    return steps


def research_processing_days(payload: dict[str, Any]) -> tuple[int | None, int | None]:
    """The processing window the agent found, as ``(min, max)`` days."""
    if not isinstance(payload, dict):
        return (None, None)
    process = payload.get(PAYLOAD_PROCESS)
    if not isinstance(process, dict):
        return (None, None)

    def _days(key: str) -> int | None:
        value = process.get(key)
        return value if isinstance(value, int) and value >= 0 else None

    return (_days("processing_time_days_min"), _days("processing_time_days_max"))


def research_fees(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Fees the agent discovered. Only cited entries with a real amount are returned."""
    fees: list[dict[str, Any]] = []
    for fee in research_slice(payload, PAYLOAD_FEES):
        amount = fee.get("amount")
        if not isinstance(amount, (int, float)):
            continue
        if _cited(fee):
            fees.append(fee)
    return fees


def research_filing_channel(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Where and by whom the application is filed, or ``None`` if uncited."""
    if not isinstance(payload, dict):
        return None
    channel = payload.get(PAYLOAD_FILING_CHANNEL)
    if not isinstance(channel, dict) or not _cited(channel):
        return None
    return dict(channel)


def research_admission(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Whether a visa is required for this corridor and by which route, or ``None``."""
    if not isinstance(payload, dict):
        return None
    admission = payload.get(PAYLOAD_ADMISSION)
    if not isinstance(admission, dict) or not _cited(admission):
        return None
    return dict(admission)


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
    "PAYLOAD_ADMISSION",
    "PAYLOAD_DOCUMENTS",
    "PAYLOAD_FEES",
    "PAYLOAD_FILING_CHANNEL",
    "PAYLOAD_PROCESS",
    "PAYLOAD_FORMS",
    "PAYLOAD_QUESTIONS",
    "PAYLOAD_RULES",
    "RESEARCH_TTL_DAYS",
    "find_research",
    "research_admission",
    "research_documents",
    "research_fees",
    "research_filing_channel",
    "research_expiry",
    "research_for_case",
    "research_forms",
    "research_is_usable",
    "research_process_steps",
    "research_processing_days",
    "research_payload",
    "research_progress_steps",
    "research_questions",
    "research_rules",
    "research_slice",
]
