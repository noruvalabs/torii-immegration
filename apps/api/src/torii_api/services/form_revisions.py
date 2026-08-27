"""What the ministry publishes right now, and whether the layout was verified against it.

The catalogue pins a content id and a SHA-256 per (status, procedure), and the layouts are
authored against those exact PDFs. When the Immigration Services Agency revises a sheet it
does not announce it: the id may stay the same while the bytes change, or the id may be
renumbered and the old one 404. Either way an applicant would be the one to find out.

The store already self-heals a renumbered id by re-reading the status page. This module
promotes that from a fallback into a scheduled check, and records the answer as versioned
content beside the packs (``_form_revisions.yml``) so a revision becomes a queued review
rather than a silent break or a red suite.

It deliberately does **not** adopt a revision. A revised sheet may have moved a field, so
the layout has to be re-verified by hand; until it is, the fill gate leaves the page blank
rather than writing into stale coordinates, which is the behaviour that makes a queued
review safe in the first place.
"""

from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
import structlog
import yaml

from torii_api.services.content_packs import resolve_packs_dir
from torii_api.services.jp_official_forms import OfficialForm
from torii_api.services.official_form_store import (
    PDF_MAGIC,
    discover_pdf_url,
)

log = structlog.get_logger(__name__)

REVISIONS_FILENAME = "_form_revisions.yml"

# What a check concluded about one form.
STATUS_CURRENT = "current"
STATUS_REVISED = "revised"
STATUS_UNREACHABLE = "unreachable"
STATUS_UNPINNED = "unpinned"

REQUEST_TIMEOUT = 30.0
_HEADERS = {"User-Agent": "torii-form-revision-check/1.0 (+https://torii.app)"}


@dataclass(frozen=True)
class RevisionRecord:
    """One form, as the ministry publishes it at the moment of the check."""

    code: str
    pdf_url: str
    sha256: str
    pages: int
    verified_sha256: str | None
    status: str
    note: str = ""

    @property
    def needs_review(self) -> bool:
        """Whether a human has to look at this before the form can be trusted again."""
        return self.status in (STATUS_REVISED, STATUS_UNREACHABLE)

    def as_dict(self) -> dict[str, Any]:
        entry: dict[str, Any] = {
            "pdf_url": self.pdf_url,
            "sha256": self.sha256,
            "pages": self.pages,
            "verified_sha256": self.verified_sha256,
            "status": self.status,
        }
        if self.note:
            entry["note"] = self.note
        return entry


def revisions_path() -> Path:
    return resolve_packs_dir() / "jp" / REVISIONS_FILENAME


def load_revisions() -> dict[str, RevisionRecord]:
    """The last recorded check, or empty if none has run."""
    path = revisions_path()
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    forms = raw.get("forms")
    if not isinstance(forms, dict):
        return {}
    records: dict[str, RevisionRecord] = {}
    for code, entry in forms.items():
        if not isinstance(entry, dict):
            continue
        records[str(code)] = RevisionRecord(
            code=str(code),
            pdf_url=str(entry.get("pdf_url") or ""),
            sha256=str(entry.get("sha256") or ""),
            pages=int(entry.get("pages") or 0),
            verified_sha256=(
                str(entry["verified_sha256"]) if entry.get("verified_sha256") else None
            ),
            status=str(entry.get("status") or STATUS_UNREACHABLE),
            note=str(entry.get("note") or ""),
        )
    return records


def pending_reviews() -> list[RevisionRecord]:
    """The queue: forms the last check found revised or unreachable."""
    return sorted(
        (record for record in load_revisions().values() if record.needs_review),
        key=lambda record: record.code,
    )


def write_revisions(records: list[RevisionRecord], *, checked_at: datetime) -> Path:
    """Record a check beside the packs, so the queue is versioned like other content."""
    header = (
        "# Written by `torii-check-form-revisions`. One entry per official form, saying\n"
        "# what the ministry publishes right now and whether it is the revision the\n"
        "# authored layout was verified against.\n"
        "#\n"
        "# A `revised` or `unreachable` entry is a review, not a break: the fill gate\n"
        "# leaves a page blank rather than writing into coordinates that may have moved,\n"
        "# so nothing reaches an applicant until somebody re-verifies the layout and\n"
        "# repins the digest in `jp_official_forms.py`.\n"
        "#\n"
        "# Do not hand-edit the digests. Re-run the check.\n"
    )
    body = yaml.safe_dump(
        {
            "checked_at": checked_at.isoformat(),
            "forms": {record.code: record.as_dict() for record in sorted(records, key=lambda r: r.code)},
        },
        allow_unicode=True,
        sort_keys=False,
    )
    path = revisions_path()
    path.write_text(header + body, encoding="utf-8")
    return path


def _page_count(content: bytes) -> int:
    try:
        import io

        import pypdf

        return len(pypdf.PdfReader(io.BytesIO(content)).pages)
    except Exception:  # pragma: no cover - a malformed download
        return 0


async def _fetch(client: httpx.AsyncClient, url: str) -> bytes | None:
    try:
        response = await client.get(url)
    except httpx.HTTPError as exc:
        log.warning("form_revision.fetch_failed", url=url, error=str(exc))
        return None
    if response.status_code != 200 or not response.content.startswith(PDF_MAGIC):
        return None
    return response.content


async def check_form(client: httpx.AsyncClient, form: OfficialForm) -> RevisionRecord:
    """Read what the ministry serves for ``form`` and compare it to the pinned revision."""
    if not form.pdf_url:
        return RevisionRecord(
            code=form.code,
            pdf_url="",
            sha256="",
            pages=form.pages,
            verified_sha256=form.sha256,
            status=STATUS_UNPINNED,
            note="The ministry does not serve this form to automated clients; it ships bundled.",
        )

    url = form.pdf_url
    content = await _fetch(client, url)
    note = ""
    if content is None:
        # The pinned id stopped resolving. The status page lists the current one.
        try:
            page = await client.get(form.source_page_url)
            discovered = (
                discover_pdf_url(page.text, form.procedure) if page.status_code == 200 else None
            )
        except httpx.HTTPError as exc:
            log.warning("form_revision.discovery_failed", form=form.code, error=str(exc))
            discovered = None
        if discovered and discovered != url:
            note = f"The pinned URL stopped resolving; the status page now lists {discovered}."
            url = discovered
            content = await _fetch(client, url)

    if content is None:
        return RevisionRecord(
            code=form.code,
            pdf_url=url,
            sha256="",
            pages=0,
            verified_sha256=form.sha256,
            status=STATUS_UNREACHABLE,
            note=note or "Neither the pinned URL nor the status page yielded a PDF.",
        )

    digest = hashlib.sha256(content).hexdigest()
    if form.sha256 is None:
        status = STATUS_UNPINNED
        note = note or "No revision is pinned for this form, so nothing can be compared."
    elif digest == form.sha256:
        status = STATUS_CURRENT
    else:
        status = STATUS_REVISED
        note = note or (
            "The published bytes differ from the revision the layout was verified against. "
            "Re-verify the layout against the new sheet before repinning the digest."
        )
    return RevisionRecord(
        code=form.code,
        pdf_url=url,
        sha256=digest,
        pages=_page_count(content),
        verified_sha256=form.sha256,
        status=status,
        note=note,
    )


async def check_all(forms: list[OfficialForm]) -> list[RevisionRecord]:
    """Check every form, sequentially, so the ministry sees one polite client."""
    records: list[RevisionRecord] = []
    async with httpx.AsyncClient(
        timeout=REQUEST_TIMEOUT, follow_redirects=True, headers=_HEADERS
    ) as client:
        for form in forms:
            records.append(await check_form(client, form))
            # The status pages are slow and this runs unattended; no reason to hurry.
            await asyncio.sleep(0.5)
    return records
