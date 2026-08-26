"""Fetch, cache and verify the exact official PDF for an application type.

The ministry renumbers a form's download URL whenever it revises the sheet, which is
precisely how an applicant ends up holding a form that does not match their visa. So the
pinned URL is only the fast path: when it stops resolving, the source page is re-read to
discover the current one, and the result is cached with its digest and provenance.

Nothing here raises on a network failure — a cached copy, then a bundled template, then
``None`` (which sends the caller to the generated fallback) — because a download outage
must not take out form generation.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import httpx
import structlog

from torii_api.config import get_settings
from torii_api.services.jp_official_forms import OfficialForm

log = structlog.get_logger(__name__)

PDF_MAGIC = b"%PDF-"
REQUEST_TIMEOUT = 30.0
# The ministry's CDN rejects requests without a browser-shaped user agent.
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; ToriiFormFetcher/1.0)"}

_PROCEDURE_HEADINGS: dict[str, tuple[str, ...]] = {
    "coe": ("在留資格認定証明書交付申請",),
    "change_of_status": ("在留資格変更許可申請",),
    "extension": ("在留期間更新許可申請",),
    "permanent_residence": ("永住許可申請",),
}

_CONTENT_PDF = re.compile(r"""["'](/isa/content/(\d{6,12})\.pdf)["']""")


@dataclass(frozen=True)
class TemplateFile:
    """A local copy of an official form, with the provenance needed to cite it."""

    form_code: str
    path: Path
    content: bytes
    sha256: str
    source_url: str | None
    retrieved_at: str | None
    bundled: bool

    def provenance(self, form: OfficialForm) -> dict[str, object]:
        matches = None if form.sha256 is None else form.sha256 == self.sha256
        return {
            "form_code": form.code,
            "source_url": self.source_url,
            "retrieved_at": self.retrieved_at,
            "sha256": self.sha256,
            "pinned_sha256": form.sha256,
            "matches_pinned_revision": matches,
            "bundled": self.bundled,
        }


def cache_dir() -> Path:
    settings = get_settings()
    configured = getattr(settings, "official_form_dir", "") or ""
    root = Path(configured) if configured else Path.cwd() / "var" / "official_forms"
    return root


def bundled_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "templates"


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sidecar_path(pdf_path: Path) -> Path:
    return pdf_path.with_suffix(".json")


def _read_cached(form: OfficialForm) -> TemplateFile | None:
    pdf_path = cache_dir() / f"{form.code}.pdf"
    if not pdf_path.is_file():
        return None
    try:
        content = pdf_path.read_bytes()
    except OSError:
        return None
    if not content.startswith(PDF_MAGIC):
        return None
    meta: dict[str, object] = {}
    sidecar = _sidecar_path(pdf_path)
    if sidecar.is_file():
        try:
            meta = json.loads(sidecar.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            meta = {}
    return TemplateFile(
        form_code=form.code,
        path=pdf_path,
        content=content,
        sha256=_sha256(content),
        source_url=str(meta.get("source_url")) if meta.get("source_url") else form.pdf_url,
        retrieved_at=str(meta.get("retrieved_at")) if meta.get("retrieved_at") else None,
        bundled=False,
    )


def _read_bundled(form: OfficialForm) -> TemplateFile | None:
    if not form.bundled_template:
        return None
    path = bundled_dir() / form.bundled_template
    if not path.is_file():
        return None
    try:
        content = path.read_bytes()
    except OSError:
        return None
    if not content.startswith(PDF_MAGIC):
        return None
    return TemplateFile(
        form_code=form.code,
        path=path,
        content=content,
        sha256=_sha256(content),
        source_url=form.source_page_url,
        retrieved_at=None,
        bundled=True,
    )


def _write_cached(form: OfficialForm, content: bytes, source_url: str) -> TemplateFile:
    directory = cache_dir()
    directory.mkdir(parents=True, exist_ok=True)
    pdf_path = directory / f"{form.code}.pdf"
    temporary = pdf_path.with_suffix(".pdf.part")
    temporary.write_bytes(content)
    temporary.replace(pdf_path)
    retrieved_at = datetime.now(UTC).isoformat()
    digest = _sha256(content)
    _sidecar_path(pdf_path).write_text(
        json.dumps(
            {
                "form_code": form.code,
                "source_url": source_url,
                "source_page_url": form.source_page_url,
                "retrieved_at": retrieved_at,
                "sha256": digest,
                "pinned_sha256": form.sha256,
                "bytes": len(content),
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return TemplateFile(
        form_code=form.code,
        path=pdf_path,
        content=content,
        sha256=digest,
        source_url=source_url,
        retrieved_at=retrieved_at,
        bundled=False,
    )


def discover_pdf_url(html: str, procedure: str) -> str | None:
    """Find the current PDF link for ``procedure`` on a ministry status page.

    The status pages list every procedure in document order with its form links beneath
    the heading, so the first content PDF after the procedure's heading is that
    procedure's form.
    """
    headings = _PROCEDURE_HEADINGS.get(procedure, ())
    for heading in headings:
        start = html.find(heading)
        while start != -1:
            match = _CONTENT_PDF.search(html, start)
            if match is None:
                break
            return f"https://www.moj.go.jp{match.group(1)}"
        break
    match = _CONTENT_PDF.search(html)
    return f"https://www.moj.go.jp{match.group(1)}" if match else None


async def _download(client: httpx.AsyncClient, url: str) -> bytes | None:
    try:
        response = await client.get(url)
    except httpx.HTTPError as exc:
        log.warning("official_form.download_failed", url=url, error=str(exc))
        return None
    if response.status_code != 200 or not response.content.startswith(PDF_MAGIC):
        log.warning("official_form.download_rejected", url=url, status=response.status_code)
        return None
    return response.content


async def refresh_template(form: OfficialForm) -> TemplateFile | None:
    """Download ``form`` from the ministry and replace the cached copy."""
    if not form.pdf_url:
        return None
    async with httpx.AsyncClient(
        timeout=REQUEST_TIMEOUT, follow_redirects=True, headers=_HEADERS
    ) as client:
        content = await _download(client, form.pdf_url)
        source_url = form.pdf_url
        if content is None:
            # The pinned id stopped resolving — re-read the source page for the current one.
            try:
                page = await client.get(form.source_page_url)
                discovered = (
                    discover_pdf_url(page.text, form.procedure) if page.status_code == 200 else None
                )
            except httpx.HTTPError as exc:
                log.warning(
                    "official_form.discovery_failed",
                    url=form.source_page_url,
                    error=str(exc),
                )
                discovered = None
            if not discovered or discovered == form.pdf_url:
                return None
            log.info(
                "official_form.rediscovered",
                form=form.code,
                pinned=form.pdf_url,
                discovered=discovered,
            )
            content = await _download(client, discovered)
            source_url = discovered
        if content is None:
            return None
    template = _write_cached(form, content, source_url)
    log.info(
        "official_form.cached",
        form=form.code,
        bytes=len(content),
        matches_pinned_revision=form.sha256 == template.sha256 if form.sha256 else None,
    )
    return template


async def ensure_template(form: OfficialForm, *, allow_network: bool = True) -> TemplateFile | None:
    """The best local copy of ``form``: bundled, then cached, then freshly downloaded."""
    bundled = _read_bundled(form)
    if bundled is not None:
        return bundled
    cached = _read_cached(form)
    if cached is not None:
        return cached
    settings = get_settings()
    if not allow_network or not getattr(settings, "official_form_fetch_enabled", True):
        return None
    return await refresh_template(form)
