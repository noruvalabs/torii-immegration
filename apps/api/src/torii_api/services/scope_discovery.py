"""Scope discovery — ask the AI service what a country offers, and record it as candidates.

Adding a country used to mean also knowing what that country offers: the create endpoint
wrote three generic routes (work / student / tourist) and switched them on, whatever the
country actually publishes. This asks the destination's own immigration pages instead
(``POST /ai/ops/discover-scopes``) and writes what comes back as **candidates** — rows an
admin can see, read the source page for, and switch on one at a time.

Two things this deliberately does not do. It never switches anything on: a discovered route
arrives with ``is_enabled=False``, so nothing reaches an applicant because a search ran.
And it never overwrites what a pack or an admin already said — an existing route keeps its
name and its switches, and only gains a description or a citation it was missing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from torii_api.config import get_settings
from torii_api.db.models import CaseAction, Jurisdiction, VisaCategory

log = structlog.get_logger()

# Where a row came from. ``pack`` is seeded from docs/jurisdictions, ``discovered`` was read
# off an official page by this service, ``manual`` was typed in by an admin.
SOURCE_PACK = "pack"
SOURCE_DISCOVERED = "discovered"
SOURCE_MANUAL = "manual"


class ScopeDiscoveryUnavailable(RuntimeError):
    """The AI service could not be reached, or answered with something unusable.

    Raised rather than returning an empty result, because "the country publishes nothing"
    and "we could not ask" are different answers and the admin needs to be told which.
    """


@dataclass
class DiscoveredScope:
    """One candidate route or procedure, with the official page it was read off."""

    code: str
    name: str
    description: str = ""
    citation: dict[str, Any] = field(default_factory=dict)


@dataclass
class DiscoveryResult:
    jurisdiction_code: str
    visa_categories: list[DiscoveredScope] = field(default_factory=list)
    case_actions: list[DiscoveredScope] = field(default_factory=list)
    source_pages: list[dict[str, Any]] = field(default_factory=list)
    discovered_at: str = ""


@dataclass
class AppliedScope:
    """What happened to one candidate when it met the database."""

    code: str
    name: str
    description: str
    citation: dict[str, Any]
    # "created" — a new candidate, switched off, awaiting an admin.
    # "enriched" — already known, and gained a description or citation it was missing.
    # "unchanged" — already known and already complete.
    outcome: str


@dataclass
class DiscoveryApplied:
    visa_categories: list[AppliedScope] = field(default_factory=list)
    case_actions: list[AppliedScope] = field(default_factory=list)
    source_pages: list[dict[str, Any]] = field(default_factory=list)
    discovered_at: str = ""

    @property
    def created_count(self) -> int:
        return sum(
            1 for item in (*self.visa_categories, *self.case_actions) if item.outcome == "created"
        )


def _scope_from_payload(raw: Any) -> DiscoveredScope | None:
    if not isinstance(raw, dict):
        return None
    code = str(raw.get("code") or "").strip().lower()
    name = str(raw.get("name") or "").strip()
    citation = raw.get("citation")
    # The AI service already drops uncited items; this is the boundary check that keeps an
    # uncited route out of the database even if that ever stops being true (NF-2).
    if not code or not name or not isinstance(citation, dict):
        return None
    if not str(citation.get("url") or "").startswith("http"):
        return None
    return DiscoveredScope(
        code=code[:32],
        name=name[:128],
        description=str(raw.get("description") or "").strip()[:512],
        citation={
            "authority": str(citation.get("authority") or ""),
            "title": str(citation.get("title") or ""),
            "url": str(citation.get("url")),
        },
    )


async def discover_scopes(
    jurisdiction_code: str,
    origin_country: str | None = None,
) -> DiscoveryResult:
    """Ask the AI service which routes and procedures a destination publishes.

    Raises :class:`ScopeDiscoveryUnavailable` when the service cannot be reached or answers
    with something that is not a discovery payload.
    """
    settings = get_settings()
    if not settings.ai_service_url:
        raise ScopeDiscoveryUnavailable("AI service URL is not configured")

    url = f"{settings.ai_service_url.rstrip('/')}/ai/ops/discover-scopes"
    payload = {
        "jurisdiction_code": jurisdiction_code.upper(),
        "origin_country": origin_country.upper() if origin_country else None,
    }
    try:
        timeout = httpx.Timeout(settings.scope_discovery_timeout_seconds, connect=5.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=payload)
    except httpx.HTTPError as exc:
        log.warning("discovery.unreachable", jurisdiction=jurisdiction_code, error=str(exc))
        raise ScopeDiscoveryUnavailable("the research service could not be reached") from exc

    if response.status_code != 200:
        log.warning(
            "discovery.rejected",
            jurisdiction=jurisdiction_code,
            status=response.status_code,
        )
        raise ScopeDiscoveryUnavailable(f"the research service answered {response.status_code}")

    try:
        data = response.json()
    except ValueError as exc:
        raise ScopeDiscoveryUnavailable("the research service answered with non-JSON") from exc
    if not isinstance(data, dict):
        raise ScopeDiscoveryUnavailable("the research service answered with an unexpected shape")

    categories = [_scope_from_payload(item) for item in data.get("visa_categories") or []]
    actions = [_scope_from_payload(item) for item in data.get("case_actions") or []]
    source_pages = [p for p in data.get("source_pages") or [] if isinstance(p, dict)]

    return DiscoveryResult(
        jurisdiction_code=str(data.get("jurisdiction_code") or jurisdiction_code).upper(),
        visa_categories=[c for c in categories if c is not None],
        case_actions=[a for a in actions if a is not None],
        source_pages=source_pages,
        discovered_at=str(data.get("discovered_at") or ""),
    )


async def apply_discovery(
    session: AsyncSession,
    jurisdiction: Jurisdiction,
    result: DiscoveryResult,
) -> DiscoveryApplied:
    """Write discovered routes as candidates under ``jurisdiction``, switched off.

    Idempotent: running discovery again on a country the admin has already curated adds
    only the routes that are genuinely new, and leaves every switch exactly as the admin
    left it.
    """
    categories = await _apply(
        session,
        jurisdiction=jurisdiction,
        model=VisaCategory,
        scopes=result.visa_categories,
    )
    actions = await _apply(
        session,
        jurisdiction=jurisdiction,
        model=CaseAction,
        scopes=result.case_actions,
    )
    await session.flush()

    applied = DiscoveryApplied(
        visa_categories=categories,
        case_actions=actions,
        source_pages=result.source_pages,
        discovered_at=result.discovered_at,
    )
    log.info(
        "discovery.applied",
        jurisdiction=jurisdiction.code,
        created=applied.created_count,
        categories=len(categories),
        actions=len(actions),
    )
    return applied


async def _apply(
    session: AsyncSession,
    *,
    jurisdiction: Jurisdiction,
    model: type[VisaCategory] | type[CaseAction],
    scopes: list[DiscoveredScope],
) -> list[AppliedScope]:
    if not scopes:
        return []

    codes = [scope.code for scope in scopes]
    rows = (
        await session.scalars(
            select(model)
            .where(model.jurisdiction_id == jurisdiction.id)
            .where(model.code.in_(codes))
        )
    ).all()
    by_code = {row.code: row for row in rows}

    applied: list[AppliedScope] = []
    for scope in scopes:
        existing = by_code.get(scope.code)
        if existing is None:
            session.add(
                model(
                    jurisdiction_id=jurisdiction.id,
                    code=scope.code,
                    name=scope.name,
                    # Off until an admin says otherwise — a search result is a proposal.
                    is_enabled=False,
                    # No seeded pack backs a discovered route, so its requirements come
                    # from the live-research pipeline once it is switched on.
                    is_live=False,
                    research_enabled=True,
                    description=scope.description,
                    source=SOURCE_DISCOVERED,
                    citation=scope.citation,
                )
            )
            applied.append(
                AppliedScope(
                    code=scope.code,
                    name=scope.name,
                    description=scope.description,
                    citation=scope.citation,
                    outcome="created",
                )
            )
            continue

        # An existing row's name and switches belong to whoever set them. Only fill gaps.
        enriched = False
        if not existing.description and scope.description:
            existing.description = scope.description
            enriched = True
        if not existing.citation and scope.citation:
            existing.citation = scope.citation
            enriched = True
        applied.append(
            AppliedScope(
                code=existing.code,
                name=existing.name,
                description=existing.description,
                citation=dict(existing.citation or {}),
                outcome="enriched" if enriched else "unchanged",
            )
        )
    return applied
