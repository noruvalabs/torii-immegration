"""Scope discovery — read a country's published visa routes off its own immigration pages.

An admin adding a country should not have to know what that country offers. This searches
the destination's official domains, reads the pages that list its visa types and its
application procedures, and returns them as candidate routes for the admin to switch on.

Nothing here decides what an applicant sees: every route comes back as a candidate carrying
the official page it was read off, and a route with no such page is dropped rather than
returned (NF-2). Turning one on is a human decision made in the admin panel.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlsplit

import structlog

from torii_ai.config import Settings
from torii_ai.llm.groq import ChatClient
from torii_ai.services.ops_scraper import (
    country_label,
    extract_json,
    official_domains_for,
)
from torii_ai.services.web_fetch import scrape_pages
from torii_ai.tools.tavily import SearchClient

log = structlog.get_logger()

# A country publishes a few dozen statuses of residence at most, and a handful of things you
# can do with one. These caps stop a mis-parsed page turning into hundreds of candidate rows
# an admin then has to read through.
MAX_CATEGORIES = 40
MAX_ACTIONS = 12

# Discovery reads wider and shallower than the requirement scraper does. A route list is what
# an index page opens with, so what pays here is seeing more index pages rather than reading
# any one of them further down — and the shallower read keeps the prompt inside a modest
# tokens-per-minute allowance. A floor under the general scrape budget: a deployment that
# configures less gets less.
DISCOVERY_MAX_PAGES = 6
DISCOVERY_PAGE_CHARS = 2000

DISCOVER_SYSTEM = """You are an immigration data extractor. You are given the text of official
government immigration pages for ONE destination country. List the visa / residence routes that
country publishes, and the application procedures available for them.

Return JSON only, no markdown fences:
{
  "visa_categories": [
    {
      "code": "snake_case_handle",
      "name": "The official name of the route, as the government writes it",
      "description": "One plain-language line: who this route is for",
      "citation": {"authority": "...", "title": "...", "url": "the official page this came from"}
    }
  ],
  "case_actions": [
    {
      "code": "snake_case_handle",
      "name": "The official name of the procedure",
      "description": "One plain-language line: what this procedure does",
      "citation": {"authority": "...", "title": "...", "url": "the official page this came from"}
    }
  ]
}

Rules:
- Only list routes and procedures the supplied pages actually state. Do not add routes you
  happen to know about, and do not carry over routes from another country.
- Every item MUST carry a citation whose "url" is one of the supplied source URLs. An item
  without one is discarded, so leaving it out loses the item.
- "code" is a short stable handle: lowercase, words joined by underscores, no punctuation
  (e.g. "skilled_worker", "student", "highly_skilled_professional", "change_of_status").
  Reuse the conventional handle when one fits: work, student, tourist, dependent, spouse,
  permanent_resident.
- "name" is what an applicant would recognise on the government's own page. Keep the local
  term alongside the English one where the page gives both.
- "description" is one line, plain language, not a bureaucratic restatement of the name.
- Common procedures are: new (first application from outside the country), renewal (extend an
  existing permission), change_of_status (switch to a different route from inside the
  country), permanent_residence. Only list the ones these pages state are available.
- Do not list individual forms, fees, offices, or document names. Routes and procedures only.
"""


@dataclass
class DiscoveryResult:
    """Candidate routes and procedures for one destination, each with its source page."""

    jurisdiction_code: str
    visa_categories: list[dict[str, Any]] = field(default_factory=list)
    case_actions: list[dict[str, Any]] = field(default_factory=list)
    source_pages: list[dict[str, Any]] = field(default_factory=list)
    discovered_at: str = ""


def build_discovery_queries(destination: str) -> list[str]:
    """Search queries that land on the pages listing a country's routes and procedures."""
    dest = country_label(destination) or destination.upper()
    return [
        f"{dest} list of visa types official immigration",
        f"{dest} statuses of residence categories official government",
        f"{dest} visa application procedures extension change of status official",
        f"{dest} immigration routes eligibility overview official government",
    ]


def _slug(value: str) -> str:
    """A short stable handle from whatever the model returned as a code."""
    slug = re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")
    return slug[:32]


def _hosts(urls: list[str]) -> set[str]:
    return {urlsplit(u).netloc.lower().removeprefix("www.") for u in urls if u}


def official_citation(citation: Any, allowed_hosts: set[str]) -> dict[str, str] | None:
    """The citation, normalized, when it points at a page we read or one of its own domains.

    A model asked for a URL will produce a plausible one whether or not it saw it. Checking
    the host against the pages that were fetched is the difference between a citation and a
    guess, and an uncited route is exactly what NF-2 exists to keep out.
    """
    if not isinstance(citation, dict):
        return None
    url = str(citation.get("url") or "").strip()
    if not url.startswith("http"):
        return None
    host = urlsplit(url).netloc.lower().removeprefix("www.")
    if not host:
        return None
    if not any(host == allowed or host.endswith(f".{allowed}") for allowed in allowed_hosts):
        return None
    return {
        "authority": str(citation.get("authority") or "").strip(),
        "title": str(citation.get("title") or "").strip(),
        "url": url,
    }


def normalize_scopes(
    raw: Any,
    *,
    allowed_hosts: set[str],
    limit: int,
) -> list[dict[str, Any]]:
    """Keep the well-formed, officially cited items; drop the rest, first code wins."""
    if not isinstance(raw, list):
        return []
    kept: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, dict):
            continue
        code = _slug(item.get("code") or item.get("name") or "")
        name = str(item.get("name") or "").strip()
        if not code or not name or code in seen:
            continue
        citation = official_citation(item.get("citation"), allowed_hosts)
        if citation is None:
            log.info("discovery.dropped_uncited", code=code)
            continue
        seen.add(code)
        kept.append(
            {
                "code": code,
                "name": name[:128],
                "description": str(item.get("description") or "").strip()[:512],
                "citation": citation,
            }
        )
        if len(kept) >= limit:
            break
    return kept


class ScopeDiscovery:
    """Discovers the visa routes and application procedures a destination publishes."""

    def __init__(
        self,
        *,
        search: SearchClient,
        chat: ChatClient,
        settings: Settings,
    ) -> None:
        self._search = search
        self._chat = chat
        self._settings = settings

    async def discover(
        self,
        jurisdiction_code: str,
        origin_country: str | None = None,
    ) -> DiscoveryResult:
        """Search, read, and extract the routes for one destination.

        Returns an empty result rather than raising when nothing official can be reached:
        the admin panel offers adding routes by hand, and an empty discovery says the
        sources were unreadable, not that the country has no routes.
        """
        now = datetime.now(UTC)
        code = jurisdiction_code.upper()
        domains = official_domains_for(code, origin_country)

        hits = []
        for query in build_discovery_queries(code):
            hits.extend(await self._search.search(query, domains=domains))

        seen_urls: set[str] = set()
        urls: list[str] = []
        for hit in hits:
            if hit.url and hit.url not in seen_urls:
                seen_urls.add(hit.url)
                urls.append(hit.url)
        urls = urls[: min(DISCOVERY_MAX_PAGES, self._settings.scrape_max_pages)]

        if not urls:
            log.warning("discovery.no_sources", jurisdiction=code)
            return DiscoveryResult(jurisdiction_code=code, discovered_at=now.isoformat())

        content = await scrape_pages(
            urls,
            timeout_seconds=self._settings.tavily_timeout_seconds,
            page_chars=min(DISCOVERY_PAGE_CHARS, self._settings.scrape_page_chars),
        )
        if not content:
            log.warning("discovery.no_content", jurisdiction=code, urls=len(urls))
            return DiscoveryResult(jurisdiction_code=code, discovered_at=now.isoformat())

        read_urls = [c["url"] for c in content]
        # The host allowlist is what was actually read, widened by the destination's known
        # official domains so a route cited to a sibling government page still counts.
        allowed_hosts = _hosts(read_urls) | {d.lower().removeprefix("www.") for d in domains or []}

        data = await self._extract(content=content, jurisdiction_code=code, now=now)
        if data is None:
            log.warning("discovery.extraction_failed", jurisdiction=code)
            return DiscoveryResult(
                jurisdiction_code=code,
                source_pages=[{"url": u, "retrieved_at": now.isoformat()} for u in read_urls],
                discovered_at=now.isoformat(),
            )

        categories = normalize_scopes(
            data.get("visa_categories"), allowed_hosts=allowed_hosts, limit=MAX_CATEGORIES
        )
        actions = normalize_scopes(
            data.get("case_actions"), allowed_hosts=allowed_hosts, limit=MAX_ACTIONS
        )

        log.info(
            "discovery.extracted",
            jurisdiction=code,
            categories=len(categories),
            actions=len(actions),
            pages=len(read_urls),
        )
        return DiscoveryResult(
            jurisdiction_code=code,
            visa_categories=categories,
            case_actions=actions,
            source_pages=[{"url": u, "retrieved_at": now.isoformat()} for u in read_urls],
            discovered_at=now.isoformat(),
        )

    async def _extract(
        self,
        *,
        content: list[dict[str, str]],
        jurisdiction_code: str,
        now: datetime,
    ) -> dict[str, Any] | None:
        content_block = "\n\n".join(
            f"=== Source {i + 1}: {c['url']} ===\n{c['text']}" for i, c in enumerate(content)
        )
        source_list = "\n".join(f"- {c['url']}" for c in content)
        dest = country_label(jurisdiction_code) or jurisdiction_code

        user_prompt = f"""Destination country: {dest} ({jurisdiction_code})
Read date: {now.strftime("%Y-%m-%d")}

Supplied source URLs (a citation must use one of these):
{source_list}

Official page content:

{content_block}

List the visa / residence routes and the application procedures {dest} publishes on these
pages. Return JSON only."""

        try:
            raw = await self._chat.complete(system=DISCOVER_SYSTEM, user=user_prompt)
        except Exception as exc:
            log.warning("discovery.llm_failed", error=str(exc))
            return None
        return extract_json(raw)
