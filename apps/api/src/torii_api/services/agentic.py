"""Per-stage agentic research resolution (docs/plan/03_corridor_bd_jp.md, Decisions §2).

Replaces pack/DB-first content resolution: intake questions, eligibility rules, checklist
items, and form templates are resolved through :class:`CaseStageResearch` — live LLM+search
content for this exact case — rather than the seeded ``IntakeDefinition`` /
``EligibilityRuleSet`` / ``DocumentRequirementSet`` / ``FormTemplate`` tables. Citations are
still gated (NF-2) before a stage counts as usable; the deterministic engine
(``evaluate_eligibility``, ``fill_form``, checklist visibility) is unchanged and evaluates
whatever this module resolves, exactly as it evaluated pack-seeded content before (NF-1).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from torii_api.db.models import CaseStageResearch, ScopeResearchStatus
from torii_api.services.intake import parse_questions
from torii_api.services.ops_ingest import has_citation

Stage = Literal["admissibility", "intake", "eligibility", "documents", "forms"]

STAGES: tuple[Stage, ...] = ("admissibility", "intake", "eligibility", "documents", "forms")

# admissibility is shared across applicants on the same corridor and changes far slower than
# per-case content (routes/fees rarely change week to week); per-case stages match the existing
# ScopeResearch TTL so a case's own content refreshes on the same cadence research already does.
ADMISSIBILITY_TTL_DAYS = 30
CASE_STAGE_TTL_DAYS = 7

_STAGE_ITEM_KEY: dict[Stage, str] = {
    "intake": "questions",
    "eligibility": "rules",
    "documents": "documents",
    "forms": "forms",
}


def scope_key(
    *,
    destination_code: str,
    purpose_code: str,
    action_code: str,
    nationality: str | None,
    residence_country: str | None,
) -> str:
    """Deterministic cache key for the pre-case ``admissibility`` stage."""
    parts = [
        destination_code.upper(),
        purpose_code.lower(),
        action_code.lower(),
        (nationality or "").upper(),
        (residence_country or "").upper(),
    ]
    return "|".join(parts)


def stage_expiry(stage: Stage) -> datetime:
    days = ADMISSIBILITY_TTL_DAYS if stage == "admissibility" else CASE_STAGE_TTL_DAYS
    return datetime.now(UTC) + timedelta(days=days)


def stage_is_usable(research: CaseStageResearch | None, now: datetime | None = None) -> bool:
    """True when a completed stage result is still within its freshness window."""
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


async def find_case_stage(
    session: AsyncSession, case_id: int, stage: Stage
) -> CaseStageResearch | None:
    """Resolve the cache row for one case's stage (any status)."""
    stmt = select(CaseStageResearch).where(
        CaseStageResearch.case_id == case_id, CaseStageResearch.stage == stage
    )
    return await session.scalar(stmt)


async def find_admissibility(session: AsyncSession, key: str) -> CaseStageResearch | None:
    """Resolve the cached ``admissibility`` row for a scope+nationality+residence key."""
    stmt = select(CaseStageResearch).where(
        CaseStageResearch.scope_key == key, CaseStageResearch.stage == "admissibility"
    )
    return await session.scalar(stmt)


def stage_items(research: CaseStageResearch | None, stage: Stage) -> list[dict[str, Any]]:
    """The stage's list-shaped item slice (empty when not usable). Not for ``admissibility``,
    whose payload is object-shaped — read its keys directly off ``research.payload``.
    """
    if research is None or not stage_is_usable(research):
        return []
    key = _STAGE_ITEM_KEY.get(stage)
    if key is None:
        return []
    value = (research.payload or {}).get(key)
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def admissibility_is_valid(payload: dict[str, Any]) -> bool:
    """NF-2 gate for the ``admissibility`` stage: at least one substantive fact, each cited.

    Unlike the list-shaped stages, admissibility's payload is a handful of objects
    (admission/filing_channel/process/fees/faq) that may be partially unknown — the gate is
    "whatever is stated carries a citation", not "everything must be filled in".
    """
    objects = [payload.get("admission"), payload.get("filing_channel"), payload.get("process")]
    lists = [payload.get("fees") or [], payload.get("faq") or []]
    substantive = [obj for obj in objects if isinstance(obj, dict) and obj]
    substantive += [item for lst in lists for item in lst if isinstance(item, dict)]
    if not substantive:
        return False
    return all(has_citation(item) for item in substantive)


def stage_is_valid(stage: Stage, payload: dict[str, Any]) -> bool:
    """NF-2 (+ shape) gate deciding whether a stage's research result may be persisted as
    ``completed`` rather than ``failed``.
    """
    if stage == "admissibility":
        return admissibility_is_valid(payload)

    key = _STAGE_ITEM_KEY[stage]
    items = payload.get(key)
    if not isinstance(items, list) or not items:
        return False
    if not all(isinstance(item, dict) and has_citation(item) for item in items):
        return False
    if stage == "intake":
        try:
            parse_questions(items)
        except (TypeError, ValueError):
            return False
    if stage == "forms":
        has_mappings = all(
            isinstance(f.get("field_mappings"), list) and f["field_mappings"] for f in items
        )
        if not has_mappings:
            return False
    return True
