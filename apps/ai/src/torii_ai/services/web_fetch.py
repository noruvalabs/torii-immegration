"""Shared official-page fetching — used by ``ops_scraper.py`` and ``agentic_research.py``.

One implementation of "read a government page's readable text" so both the legacy per-scope
scraper and the per-stage agentic engine scrape identically (gov.uk content-API handling,
HTML stripping, dedup by content hash).
"""

from __future__ import annotations

import asyncio
import hashlib
import re
from html import unescape

import httpx
import structlog

log = structlog.get_logger()

# How much raw markup to read before extracting text. Bounded for memory, but generously:
# a government page's <head> alone can run well past 8KB of meta tags, inline CSS and
# schema.org JSON, and slicing the markup before the tags come out is how a real page ends
# up yielding sixty characters of text. Callers cap the *extracted* text
# (``scrape_pages(page_chars=...)``); this cap only stops a pathological download.
RAW_HTML_LIMIT = 400_000


def is_govuk(url: str) -> bool:
    """True when a URL is served by the JS-rendered gov.uk frontend."""
    try:
        host = httpx.URL(url).host or ""
    except Exception:
        return False
    return host == "www.gov.uk" or host.endswith(".gov.uk")


# Regions that are never the page's own content. Stripped before the tags come out, because
# a government page leads with a skip link, a language switcher and a site-wide menu, and a
# reader given only the first couple of thousand characters would otherwise see just those.
_CHROME = ("script", "style", "noscript", "nav", "header", "footer", "aside", "form")


def strip_html(raw: str) -> str:
    """Extract a page's readable text: its content region, minus site chrome, entities decoded.

    Three narrowings, each because a real government page needed it. Everything before
    ``<body>`` is metadata, inline styling and structured-data JSON, and on some sites is
    larger than the body itself. A declared ``<main>`` region is the content, so it wins over
    the whole body. And the chrome elements around it are dropped by name. An HTML fragment
    with none of these markers (the gov.uk content API returns such fragments) is used whole.
    """
    section = re.search(r"<main\b[^>]*>(.*?)</main>", raw, flags=re.DOTALL | re.IGNORECASE)
    if section is None:
        section = re.search(r"<body\b[^>]*>(.*)", raw, flags=re.DOTALL | re.IGNORECASE)
    text = section.group(1) if section else raw

    for element in _CHROME:
        text = re.sub(
            rf"<{element}\b[^>]*>.*?</{element}>", " ", text, flags=re.DOTALL | re.IGNORECASE
        )
    text = re.sub(r"<[^>]+>", " ", text)
    # Decoded, because a requirement the model reads as "&pound;1,334" is a requirement it
    # can misread.
    text = unescape(text)
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
        return strip_html(resp.text[:RAW_HTML_LIMIT])
    except (httpx.HTTPError, ValueError) as exc:
        log.warning("web_fetch.page_failed", url=url, error=str(exc))
        return ""


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
