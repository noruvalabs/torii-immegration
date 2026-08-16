"""Shared official-page fetching — used by ``ops_scraper.py`` and ``agentic_research.py``.

One implementation of "read a government page's readable text" so both the legacy per-scope
scraper and the per-stage agentic engine scrape identically (gov.uk content-API handling,
HTML stripping, dedup by content hash).
"""

from __future__ import annotations

import hashlib
import re

import httpx
import structlog

log = structlog.get_logger()


def is_govuk(url: str) -> bool:
    """True when a URL is served by the JS-rendered gov.uk frontend."""
    try:
        host = httpx.URL(url).host or ""
    except Exception:
        return False
    return host == "www.gov.uk" or host.endswith(".gov.uk")


def strip_html(raw: str) -> str:
    """Strip script/style blocks and tags, collapse whitespace."""
    text = re.sub(r"<script[^>]*>.*?</script>", "", raw, flags=re.DOTALL)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


async def fetch_govuk_text(client: httpx.AsyncClient, page_url: str) -> str:
    """Read a gov.uk article via its public content API (``/api/content/<path>``).

    The published HTML is a JS-rendered shell; the content API returns the full body as
    JSON (``details.parts[].body`` for guides, ``details.body`` otherwise). Handles the
    ``redirect`` content type by following the declared destination.
    """
    try:
        parsed = httpx.URL(page_url)
        host = str(parsed.host)
        api_url = f"{parsed.scheme}://{host}/api/content{parsed.path}"
        resp = await client.get(api_url)
        if resp.status_code != 200:
            return ""
        data = resp.json()
        if not isinstance(data, dict):
            return ""
        if data.get("document_type") == "redirect":
            redirects = data.get("redirects") or []
            if redirects:
                dest = redirects[0].get("destination")
                if dest:
                    next_url = f"{parsed.scheme}://{host}{dest}"
                    return await fetch_govuk_text(client, next_url)
            return ""
        details = data.get("details") or {}
        parts = details.get("parts") or []
        if parts:
            bodies = [p.get("body") or "" for p in parts]
            return strip_html("\n".join(bodies))
        return strip_html(details.get("body") or "")
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        log.warning("web_fetch.govuk_api_failed", url=page_url, error=str(exc))
        return ""


async def fetch_page_text(client: httpx.AsyncClient, url: str) -> str:
    """Return readable page text for one URL ('' on failure)."""
    try:
        if is_govuk(url):
            text = await fetch_govuk_text(client, url)
            if text:
                return text
        resp = await client.get(url)
        if resp.status_code != 200:
            return ""
        ctype = resp.headers.get("content-type", "")
        if ctype and not ctype.startswith("text/") and "html" not in ctype:
            log.info("web_fetch.page_skipped", url=url, content_type=ctype)
            return ""
        return strip_html(resp.text[:8000])
    except (httpx.HTTPError, ValueError) as exc:
        log.warning("web_fetch.page_failed", url=url, error=str(exc))
        return ""


import asyncio

async def scrape_pages(
    urls: list[str], *, timeout_seconds: float, page_chars: int
) -> list[dict[str, str]]:
    """Fetch page content for each URL concurrently, deduplicating identical bodies by content hash."""
    content: list[dict[str, str]] = []
    seen: set[str] = set()
    semaphore = asyncio.Semaphore(6)

    async with httpx.AsyncClient(
        timeout=timeout_seconds,
        follow_redirects=True,
        headers={"User-Agent": "Torii-OPS-Worker/1.0"},
    ) as client:
        async def _fetch(u: str) -> tuple[str, str]:
            async with semaphore:
                t = await fetch_page_text(client, u)
                return u, t

        results = await asyncio.gather(*[_fetch(u) for u in urls], return_exceptions=True)
        for res in results:
            if isinstance(res, tuple):
                u, text = res
                if not text:
                    continue
                digest = hashlib.sha256(text.encode("utf-8", "ignore")).hexdigest()
                if digest in seen:
                    log.info("web_fetch.page_duplicate", url=u)
                    continue
                seen.add(digest)
                content.append({"url": u, "text": text[:page_chars]})
                log.info("web_fetch.page_scraped", url=u, chars=len(text))
    return content
