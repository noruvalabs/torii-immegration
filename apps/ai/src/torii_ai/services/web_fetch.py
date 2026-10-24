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


async def fetch_govuk_text(
    client: httpx.AsyncClient, page_url: str, visited: set[str] | None = None
) -> str:
    """Read a gov.uk article via its public content API (``/api/content/<path>``).

    The published HTML is a JS-rendered shell; the content API returns the full body as
    JSON (``details.parts[].body`` for guides, ``details.body`` otherwise). Handles the
    ``redirect`` content type by following the declared destination, with redirect-loop defense.
    """
    if visited is None:
        visited = set()
    if page_url in visited or len(visited) > 5:
        log.warning("web_fetch.govuk_redirect_loop", url=page_url)
        return ""
    visited.add(page_url)

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
                    return await fetch_govuk_text(client, next_url, visited)
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


DEFAULT_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}


def _is_allowed_source_url(
    url: str,
    destination: str | None = None,
    nationality: str | None = None,
    residence: str | None = None,
) -> bool:
    from torii_ai.services.ops_scraper import is_official_source_domain

    return is_official_source_domain(
        url, destination=destination, nationality=nationality, residence=residence
    )


async def fetch_page_details(
    client: httpx.AsyncClient,
    url: str,
    *,
    destination: str | None = None,
    nationality: str | None = None,
    residence: str | None = None,
) -> tuple[str, str]:
    """Return (final_validated_url, readable_page_text) for one URL.

    Validates that the initial URL and any redirected destination remain on an authorized official source domain.
    Returns ('', '') if the fetch fails, times out, encounters a redirect loop, attempts SSRF, or redirects
    to an untrusted domain.
    """
    try:
        # Pre-validate initial URL: must be an allowed official source and cannot access private/internal targets
        if not _is_allowed_source_url(url, destination, nationality, residence):
            log.warning("web_fetch.untrusted_initial_url", url=url)
            return "", ""

        if is_govuk(url):
            text = await fetch_govuk_text(client, url)
            if text:
                return url, text

        resp = await client.get(url)
        final_url = str(resp.url)

        if resp.status_code != 200:
            log.warning("web_fetch.http_error", url=url, status_code=resp.status_code)
            return "", ""

        # Validate final URL if redirected
        if final_url != url:
            if not _is_allowed_source_url(final_url, destination, nationality, residence):
                log.warning(
                    "web_fetch.untrusted_redirect_destination",
                    initial_url=url,
                    redirected_to=final_url,
                )
                return "", ""
            log.info("web_fetch.redirect_validated", initial_url=url, final_url=final_url)

        ctype = resp.headers.get("content-type", "")
        if ctype and not ctype.startswith("text/") and "html" not in ctype:
            log.info("web_fetch.page_skipped", url=final_url, content_type=ctype)
            return "", ""

        return final_url, strip_html(resp.text[:RAW_HTML_LIMIT])
    except httpx.TooManyRedirects as exc:
        log.warning("web_fetch.redirect_loop", url=url, error=str(exc))
        return "", ""
    except httpx.TimeoutException as exc:
        log.warning("web_fetch.timeout", url=url, error=str(exc))
        return "", ""
    except (httpx.HTTPError, ValueError) as exc:
        log.warning("web_fetch.page_failed", url=url, error=str(exc))
        return "", ""


async def fetch_page_text(
    client: httpx.AsyncClient,
    url: str,
    *,
    destination: str | None = None,
    nationality: str | None = None,
    residence: str | None = None,
) -> str:
    """Return readable page text for one URL ('' on failure)."""
    _, text = await fetch_page_details(
        client, url, destination=destination, nationality=nationality, residence=residence
    )
    return text


async def scrape_pages(
    urls: list[str],
    *,
    timeout_seconds: float,
    page_chars: int,
    destination: str | None = None,
    nationality: str | None = None,
    residence: str | None = None,
) -> list[dict[str, str]]:
    """Fetch page content for each URL concurrently, deduplicating identical bodies by content hash.

    Validates redirect targets and records actual validated destination URLs in provenance.
    Blocks private and internal network targets during every hop of redirect following.
    """
    content: list[dict[str, str]] = []
    seen: set[str] = set()
    semaphore = asyncio.Semaphore(6)

    async def _validate_request_target(request: httpx.Request) -> None:
        req_url = str(request.url)
        if not _is_allowed_source_url(req_url, destination, nationality, residence):
            raise httpx.RequestError(
                f"Blocked request to unauthorized or private destination: {req_url}"
            )

    async with httpx.AsyncClient(
        timeout=timeout_seconds,
        follow_redirects=True,
        headers=DEFAULT_BROWSER_HEADERS,
        event_hooks={"request": [_validate_request_target]},
    ) as client:

        async def _fetch(u: str) -> tuple[str, str]:
            async with semaphore:
                return await fetch_page_details(
                    client,
                    u,
                    destination=destination,
                    nationality=nationality,
                    residence=residence,
                )

        results = await asyncio.gather(*[_fetch(u) for u in urls], return_exceptions=True)
        for res in results:
            if isinstance(res, tuple):
                final_u, text = res
                if not text or not final_u:
                    continue
                digest = hashlib.sha256(text.encode("utf-8", "ignore")).hexdigest()
                if digest in seen:
                    log.info("web_fetch.page_duplicate", url=final_u)
                    continue
                seen.add(digest)
                content.append({"url": final_u, "text": text[:page_chars]})
                log.info("web_fetch.page_scraped", url=final_u, chars=len(text))
    return content
