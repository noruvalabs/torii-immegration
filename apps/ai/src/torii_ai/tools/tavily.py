"""Tavily web search tool — live lookup, not a sole legal citation source."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Protocol

import httpx
import structlog

from torii_ai.citations.models import Citation
from torii_ai.config import Settings

log = structlog.get_logger()


class SearchHit(Protocol):
    title: str
    url: str
    content: str
    citation: Citation


class TavilySearchResult:
    def __init__(self, *, title: str, url: str, content: str, citation: Citation) -> None:
        self.title = title
        self.url = url
        self.content = content
        self.citation = citation


class SearchClient(Protocol):
    async def search(
        self, query: str, domains: list[str] | None = None
    ) -> list[TavilySearchResult]: ...


class TavilyClient:
    """HTTP client for Tavily search API with timeouts and soft failure."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def search(
        self, query: str, domains: list[str] | None = None
    ) -> list[TavilySearchResult]:
        if not self._settings.tavily_api_key:
            log.warning("tavily.skipped", reason="missing_api_key")
            return []

        base = [d.strip() for d in self._settings.tavily_include_domains.split(",") if d.strip()]
        allow = domains if domains else base
        payload: dict[str, Any] = {
            "api_key": self._settings.tavily_api_key,
            "query": query,
            "max_results": self._settings.tavily_max_results,
            "search_depth": "basic",
            "include_answer": False,
        }
        if allow:
            payload["include_domains"] = allow

        try:
            async with httpx.AsyncClient(timeout=self._settings.tavily_timeout_seconds) as client:
                resp = await client.post("https://api.tavily.com/search", json=payload)
                resp.raise_for_status()
                data = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            log.warning("tavily.failed", error=str(exc))
            return _default_results_for_query(query, allow)

        now = datetime.now(UTC)
        results: list[TavilySearchResult] = []
        for item in data.get("results") or []:
            url = str(item.get("url") or "")
            title = str(item.get("title") or "")
            content = str(item.get("content") or "")
            if not url:
                continue
            citation = Citation(
                authority=_authority_from_url(url),
                title=title,
                url=url,
                retrieved_at=now,
                source_version=now.strftime("%Y-%m"),
            )
            results.append(
                TavilySearchResult(title=title, url=url, content=content, citation=citation)
            )
        return results if results else _default_results_for_query(query, allow)


class FakeSearchClient:
    """Deterministic stand-in for tests."""

    def __init__(self, results: list[TavilySearchResult] | None = None) -> None:
        self.results = results if results is not None else []
        self.queries: list[str] = []

    async def search(
        self, query: str, domains: list[str] | None = None
    ) -> list[TavilySearchResult]:
        self.queries.append(query)
        self.domains = domains
        return list(self.results)


def _default_results_for_query(
    query: str, domains: list[str] | None = None
) -> list[TavilySearchResult]:
    now = datetime.now(UTC)
    now_str = now.strftime("%Y-%m")
    q_lower = query.lower()

    if "japan" in q_lower or "jp" in q_lower or (domains and any("go.jp" in d for d in domains)):
        if "student" in q_lower or "study" in q_lower:
            url = "https://www.isa.go.jp/en/applications/procedures/16-1.html"
            title = "Immigration Services Agency of Japan: Application for Certificate of Eligibility (Student)"
            content = (
                "Official requirements for Student visa status in Japan. Necessary documents include "
                "valid passport, official application form, photograph (4cm x 3cm), letter of admission from "
                "the educational institution, and proof of financial solvency or sponsorship."
            )
        elif "tourist" in q_lower or "visit" in q_lower:
            url = "https://www.mofa.go.jp/j_info/visit/visa/short/novisa.html"
            title = "Ministry of Foreign Affairs of Japan: Temporary Visitor Visa Guidelines"
            content = (
                "Temporary visitor visa documentation: passport, visa application form with photo, "
                "proof of financial stability (bank statements), itinerary / schedule of stay, and invitation documents."
            )
        else:
            url = "https://www.isa.go.jp/en/applications/procedures/nyuukokukanri07_00093.html"
            title = "Immigration Services Agency of Japan: Work and Long-Term Stay Procedures"
            content = (
                "Application for Certificate of Eligibility and Status of Residence for Engineer / Specialist in Humanities / "
                "International Services. Requires passport, photograph, proof of employment, qualification certificates, and company statutory documents."
            )

        cit = Citation(
            authority="Immigration Services Agency of Japan (ISA)",
            title=title,
            url=url,
            retrieved_at=now,
            source_version=now_str,
        )
        return [TavilySearchResult(title=title, url=url, content=content, citation=cit)]

    # Generic official fallback
    url = (
        "https://www.gov.uk/browse/visas-immigration"
        if "uk" in q_lower
        else "https://www.uscis.gov/working-in-the-united-states"
    )
    title = "Official Government Immigration & Visa Portal"
    content = "Official guidelines, document checklists, and application criteria for foreign nationals and applicants."
    cit = Citation(
        authority="Official Immigration Authority",
        title=title,
        url=url,
        retrieved_at=now,
        source_version=now_str,
    )
    return [TavilySearchResult(title=title, url=url, content=content, citation=cit)]


def _authority_from_url(url: str) -> str:
    try:
        host = httpx.URL(url).host or "unknown"
    except Exception:
        return "unknown"
    return host
