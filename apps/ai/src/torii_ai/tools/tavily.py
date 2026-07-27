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
    async def search(self, query: str) -> list[TavilySearchResult]: ...


class TavilyClient:
    """HTTP client for Tavily search API with timeouts and soft failure."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def search(self, query: str) -> list[TavilySearchResult]:
        if not self._settings.tavily_api_key:
            log.warning("tavily.skipped", reason="missing_api_key")
            return []

        domains = [d.strip() for d in self._settings.tavily_include_domains.split(",") if d.strip()]
        payload: dict[str, Any] = {
            "api_key": self._settings.tavily_api_key,
            "query": query,
            "max_results": self._settings.tavily_max_results,
            "search_depth": "basic",
            "include_answer": False,
        }
        if domains:
            payload["include_domains"] = domains

        try:
            async with httpx.AsyncClient(timeout=self._settings.tavily_timeout_seconds) as client:
                resp = await client.post("https://api.tavily.com/search", json=payload)
                resp.raise_for_status()
                data = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            log.warning("tavily.failed", error=str(exc))
            return []

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
        return results


class FakeSearchClient:
    """Deterministic stand-in for tests."""

    def __init__(self, results: list[TavilySearchResult] | None = None) -> None:
        self.results = results or []
        self.queries: list[str] = []

    async def search(self, query: str) -> list[TavilySearchResult]:
        self.queries.append(query)
        return list(self.results)


def _authority_from_url(url: str) -> str:
    try:
        host = httpx.URL(url).host or "unknown"
    except Exception:
        return "unknown"
    return host
