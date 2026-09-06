"""Exporting the drafted documents as files a person can actually file.

Until these existed the filing kit could only leave the product as ``.txt``. The tests
assert the three things that make the export worth having: the file really is the format
it claims (a PDF that opens, a ``.docx`` that Word will not reject), the applicant's own
text — including the edits they made in the browser — survives the round trip intact, and
nothing of Torii's own is printed above it, because a consular officer reads these.
"""

from __future__ import annotations

import base64
import io
import json
import xml.etree.ElementTree as ET
import zipfile

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from torii_api.services.document_export import (
    FORMATS,
    render_document,
    render_docx,
    render_pdf,
    safe_stem,
)
from torii_api.services.intake import JP_WORK_RENEWAL_QUESTIONS

_LETTER = """APPLICATION COVER LETTER  (draft - check and sign before filing)

Reference: JP-2026-000051
Applicant: Rina Tanaka

ENCLOSED DOCUMENTS
==================
   1. Original passport
   2. Bank balance certificate

Day   Location        Contact
1     Tokyo           +81 3 0000 0000
2     Kyoto           +81 75 000 0000

Signature: ______________________________
"""


def _pdf_text(content: bytes) -> str:
    import pypdf

    reader = pypdf.PdfReader(io.BytesIO(content))
    return " ".join(page.extract_text() or "" for page in reader.pages)


async def _seed_scope(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.execute(
            text("INSERT INTO jurisdictions (code, name, is_live) VALUES ('JP', 'Japan', 1)")
        )
        jid = (
            await conn.execute(text("SELECT id FROM jurisdictions WHERE code = 'JP'"))
        ).scalar_one()
        await conn.execute(
            text(
                "INSERT INTO visa_categories (jurisdiction_id, code, name, is_live)"
                f" VALUES ({jid}, 'work', 'Work', 1)"
            )
        )
        await conn.execute(
            text(
                "INSERT INTO case_actions (jurisdiction_id, code, name, is_live)"
                f" VALUES ({jid}, 'renewal', 'Renewal', 1)"
            )
        )
        vc_id = (
            await conn.execute(
                text(f"SELECT id FROM visa_categories WHERE jurisdiction_id = {jid}")
            )
        ).scalar_one()
        ca_id = (
            await conn.execute(text(f"SELECT id FROM case_actions WHERE jurisdiction_id = {jid}"))
        ).scalar_one()
        await conn.execute(
            text(
                "INSERT INTO intake_definitions"
                " (jurisdiction_id, visa_category_id, case_action_id, questions, is_live)"
                f" VALUES ({jid}, {vc_id}, {ca_id}, :q, 1)"
            ),
            {"q": json.dumps(JP_WORK_RENEWAL_QUESTIONS)},
        )


async def _register_and_scope(client: AsyncClient, email: str) -> tuple[str, int]:
    register = await client.post(
        "/v1/auth/register", json={"email": email, "password": "secure-pass"}
    )
    assert register.status_code == 201
    token = register.json()["access_token"]
    scoped = await client.post(
        "/v1/cases/scope",
        json={
            "jurisdiction_code": "JP",
            "visa_category_code": "work",
            "action_code": "renewal",
            "locale": "en",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert scoped.status_code == 201
    return token, scoped.json()["id"]


def test_pdf_carries_the_applicants_own_text() -> None:
    content = render_pdf([("Embassy Cover Letter", _LETTER)])
    assert content.startswith(b"%PDF-")
    body = _pdf_text(content)
    assert "Rina Tanaka" in body
    assert "Bank balance certificate" in body
    # The reader is told these are drafts on every page, not finished official documents.
    assert "check every entry and sign before filing" in body
    # The reference appears exactly where the applicant's letter puts it, and nowhere
    # else. A "<reference> - <scope> - prepared <date>" line used to be printed above the
    # letter, duplicating what it already says and putting Torii's own bookkeeping on a
    # page a consular officer reads.
    assert body.count("JP-2026-000051") == 1


def test_docx_is_a_package_word_will_open() -> None:
    content = render_docx(
        [("Statement of Purpose", "理由: 日本で働きたい。\n\nName: Rina Tanaka\n")]
    )
    archive = zipfile.ZipFile(io.BytesIO(content))
    # Word rejects a package missing any of these outright.
    for part in (
        "[Content_Types].xml",
        "_rels/.rels",
        "word/_rels/document.xml.rels",
        "word/styles.xml",
        "word/document.xml",
    ):
        assert part in archive.namelist()
    for name in archive.namelist():
        ET.fromstring(archive.read(name))  # every part is well-formed XML
    document = archive.read("word/document.xml").decode("utf-8")
    assert "Rina Tanaka" in document
    # No preparation date, reference or scope label above the applicant's own words.
    assert "prepared" not in document.split("Rina Tanaka")[0]
    assert "日本で働きたい" in document


def test_markup_in_the_draft_cannot_break_the_file() -> None:
    """An applicant can type anything into the textarea, including angle brackets."""
    hostile = 'Employer: Smith & Sons <Tokyo> "branch"\n'
    document = render_docx([("T", hostile)])
    archive = zipfile.ZipFile(io.BytesIO(document))
    xml = archive.read("word/document.xml").decode("utf-8")
    ET.fromstring(xml)
    assert "&amp;" in xml and "&lt;Tokyo&gt;" in xml
    assert "Smith & Sons <Tokyo>" in _pdf_text(render_pdf([("T", hostile)]))


def test_safe_stem_never_yields_a_path() -> None:
    assert safe_stem("../../etc/passwd") == "etcpasswd"
    assert safe_stem("") == "document"
    assert safe_stem("JP-2026-000051-cover-letter") == "JP-2026-000051-cover-letter"


def test_every_offered_format_produces_bytes() -> None:
    for fmt in FORMATS:
        assert render_document([("T", _LETTER)], fmt=fmt), fmt


def test_plain_text_is_no_longer_offered() -> None:
    """A ``.txt`` file is not a document anybody files, so it is not an option."""
    assert FORMATS == ("pdf", "docx")
    with pytest.raises(ValueError):
        render_document([("T", _LETTER)], fmt="txt")


async def test_export_endpoint_returns_a_pdf_for_the_edited_draft(
    client: AsyncClient, engine: AsyncEngine
) -> None:
    await _seed_scope(engine)
    token, case_id = await _register_and_scope(client, "export-pdf@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.post(
        f"/v1/cases/{case_id}/export/documents?format=base64",
        headers={**headers, "Accept": "application/json"},
        json={
            "format": "pdf",
            "documents": [{"title": "Embassy Cover Letter", "content": _LETTER}],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["media_type"] == "application/pdf"
    assert body["filename"].endswith(".pdf")
    rendered = _pdf_text(base64.b64decode(body["data_base64"]))
    assert "Rina Tanaka" in rendered
    # The case's own reference names the file; it is not stamped onto the page.
    case_reference = body["filename"].split("-embassy")[0]
    assert case_reference.startswith("JP-")
    assert case_reference not in rendered


async def test_export_endpoint_bundles_every_document_as_a_zip(
    client: AsyncClient, engine: AsyncEngine
) -> None:
    await _seed_scope(engine)
    token, case_id = await _register_and_scope(client, "export-zip@example.com")

    response = await client.post(
        f"/v1/cases/{case_id}/export/documents?format=base64",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        json={
            "format": "docx",
            "separate": True,
            "documents": [
                {"title": "Cover Letter", "content": _LETTER, "filename_stem": "cover-letter"},
                {"title": "Schedule of Stay", "content": _LETTER, "filename_stem": "schedule"},
            ],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["media_type"] == "application/zip"
    names = zipfile.ZipFile(io.BytesIO(base64.b64decode(body["data_base64"]))).namelist()
    assert names == ["cover-letter.docx", "schedule.docx"]


async def test_export_is_scoped_to_the_owner(client: AsyncClient, engine: AsyncEngine) -> None:
    await _seed_scope(engine)
    _token, case_id = await _register_and_scope(client, "owner@example.com")
    intruder = await client.post(
        "/v1/auth/register", json={"email": "intruder@example.com", "password": "secure-pass"}
    )
    response = await client.post(
        f"/v1/cases/{case_id}/export/documents",
        headers={"Authorization": f"Bearer {intruder.json()['access_token']}"},
        json={"format": "pdf", "documents": [{"title": "T", "content": "x"}]},
    )
    assert response.status_code == 404
