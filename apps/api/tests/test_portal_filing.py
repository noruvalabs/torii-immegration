"""Jurisdictions that are filed online get an answer pack, not a form.

The UK publishes no application form — every route is completed on gov.uk — so a
document styled as a UK application form misrepresents the process to the applicant.
"""

from __future__ import annotations

import base64
import json

from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from torii_api.services.content_packs import load_jurisdiction_meta, load_pack_by_scope
from torii_api.services.pdf_generator import generate_portal_application_pack_pdf
from torii_api.services.portal_pack import build_portal_pack

UK_WORK = "uk/work.new_application"


def _pdf_text(content: bytes) -> str:
    """Text as a reader sees it. ReportLab compresses its streams, so scanning the raw
    bytes silently matches nothing and every assertion over it passes vacuously."""
    import io

    import pypdf

    reader = pypdf.PdfReader(io.BytesIO(content))
    return " ".join(page.extract_text() or "" for page in reader.pages)


def _uk_forms() -> list[dict]:
    pack = load_pack_by_scope(UK_WORK)
    return [form.as_template_row() for form in pack.forms]


# ── Filing mode is declared in the packs, not in code ──────────────────────────────


def test_filing_mode_comes_from_the_jurisdiction_pack() -> None:
    assert load_jurisdiction_meta("JP").filing_mode == "official_form_pdf"  # type: ignore[union-attr]
    assert load_jurisdiction_meta("UK").filing_mode == "online_portal"  # type: ignore[union-attr]


def test_an_online_jurisdiction_declares_where_to_apply() -> None:
    meta = load_jurisdiction_meta("UK")
    assert meta is not None
    assert meta.apply_url and meta.apply_url.startswith("https://")


def test_filing_mode_defaults_to_a_published_form() -> None:
    """A pack that says nothing keeps the existing behaviour."""
    from torii_api.services.content_packs import JurisdictionMeta

    assert JurisdictionMeta(code="ZZ", name="Nowhere").filing_mode == "official_form_pdf"


# ── The pack itself ────────────────────────────────────────────────────────────────


def test_pack_groups_answers_into_the_portal_sections() -> None:
    pack = build_portal_pack(
        _uk_forms(),
        {"full_name": "Md Hojayfa Rahman", "passport_number": "A05421997"},
        jurisdiction="UK",
        scope_label="United Kingdom · Skilled Worker",
    )
    keys = [section.key for section in pack.sections]
    assert "personal" in keys
    assert "passport" in keys
    # Sections come out in the order the service asks for them, not alphabetically.
    assert keys.index("personal") < keys.index("passport") < keys.index("declarations")


def test_pack_separates_answered_from_outstanding_and_invents_nothing() -> None:
    pack = build_portal_pack(
        _uk_forms(),
        {"full_name": "Md Hojayfa Rahman"},
        jurisdiction="UK",
        scope_label="United Kingdom · Skilled Worker",
    )
    answered = {item.answer_key: item.value for item in pack.answered}
    assert answered == {"full_name": "Md Hojayfa Rahman"}

    outstanding = {item.answer_key for item in pack.outstanding}
    assert "cos_reference" in outstanding
    assert "annual_salary_gbp" in outstanding
    # An unanswered question carries no value at all — not a placeholder that reads as one.
    assert all(item.value is None for item in pack.outstanding)


def test_pack_renders_booleans_as_the_portal_words_them() -> None:
    pack = build_portal_pack(
        _uk_forms(),
        {"criminal_record": False, "sponsor_certifies_maintenance": True},
        jurisdiction="UK",
        scope_label="UK",
    )
    values = {item.answer_key: item.value for item in pack.all_fields if item.answered}
    assert values["criminal_record"] == "No"
    assert values["sponsor_certifies_maintenance"] == "Yes"


def test_pack_carries_the_official_apply_url() -> None:
    pack = build_portal_pack(_uk_forms(), {}, jurisdiction="UK", scope_label="UK")
    assert pack.apply_url == "https://www.gov.uk/skilled-worker-visa/apply"
    assert pack.citations and pack.citations[0]["url"].startswith("https://www.gov.uk/")


def test_rendered_pack_says_it_is_not_an_application_form() -> None:
    content = generate_portal_application_pack_pdf(
        "UK-1",
        {"full_name": "Md Hojayfa Rahman"},
        _uk_forms(),
        scope_label="United Kingdom · Skilled Worker Visa",
        apply_url="https://www.gov.uk/skilled-worker-visa/apply",
    )
    assert content.startswith(b"%PDF-")
    rendered = _pdf_text(content)
    assert "not an application form" in rendered
    assert "gov.uk/skilled-worker-visa/apply" in rendered
    assert "Md Hojayfa Rahman" in rendered


# ── End to end ─────────────────────────────────────────────────────────────────────


async def _seed_uk(engine: AsyncEngine) -> None:
    pack = load_pack_by_scope(UK_WORK)
    async with engine.begin() as conn:
        await conn.execute(
            text("INSERT INTO jurisdictions (code, name, is_live) VALUES ('UK', 'UK', 1)")
        )
        jid = (
            await conn.execute(text("SELECT id FROM jurisdictions WHERE code = 'UK'"))
        ).scalar_one()
        await conn.execute(
            text(
                "INSERT INTO visa_categories (jurisdiction_id, code, name, is_live)"
                f" VALUES ({jid}, 'work', 'Skilled Worker', 1)"
            )
        )
        await conn.execute(
            text(
                "INSERT INTO case_actions (jurisdiction_id, code, name, is_live)"
                f" VALUES ({jid}, 'new_application', 'New application', 1)"
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
            {"q": json.dumps(pack.questions)},
        )
        template = pack.primary_form
        await conn.execute(
            text(
                "INSERT INTO form_templates"
                " (jurisdiction_id, visa_category_id, case_action_id, code, version,"
                " is_live, official_title, citation, field_mappings)"
                f" VALUES ({jid}, {vc_id}, {ca_id}, :code, :version, 1, :title, :cit, :maps)"
            ),
            {
                "code": template["code"],
                "version": template["version"],
                "title": template["official_title"],
                "cit": json.dumps(template["citation"]),
                "maps": json.dumps(template["field_mappings"]),
            },
        )


async def _register_uk_case(client: AsyncClient, email: str) -> tuple[str, int]:
    register = await client.post(
        "/v1/auth/register", json={"email": email, "password": "secure-pass"}
    )
    token = register.json()["access_token"]
    scoped = await client.post(
        "/v1/cases/scope",
        json={
            "jurisdiction_code": "UK",
            "visa_category_code": "work",
            "action_code": "new_application",
            "locale": "en",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert scoped.status_code == 201, scoped.text
    return token, scoped.json()["id"]


async def test_filing_endpoint_returns_the_portal_pack(
    client: AsyncClient, engine: AsyncEngine
) -> None:
    await _seed_uk(engine)
    token, case_id = await _register_uk_case(client, "uk-filing@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.get(f"/v1/cases/{case_id}/filing", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["filing_mode"] == "online_portal"
    assert body["apply_url"]
    pack = body["portal_pack"]
    assert pack["outstanding_count"] > 0
    assert [section["key"] for section in pack["sections"]][:2] == ["personal", "passport"]


async def test_uk_download_is_an_answer_pack_not_a_form(
    client: AsyncClient, engine: AsyncEngine
) -> None:
    await _seed_uk(engine)
    token, case_id = await _register_uk_case(client, "uk-download@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    await client.put(
        f"/v1/cases/{case_id}/intake/answer",
        json={"key": "full_name", "value": "Md Hojayfa Rahman"},
        headers=headers,
    )
    response = await client.get(
        f"/v1/cases/{case_id}/export/application-form?format=base64", headers=headers
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["filename"].endswith("_Online_Application_Pack.pdf")
    content = base64.b64decode(payload["data_base64"])
    assert content.startswith(b"%PDF-")
    assert "not an application form" in _pdf_text(content)


def test_a_japanese_case_still_gets_its_official_form() -> None:
    """Filing mode must not have changed the Japanese path."""
    from torii_api.api.case_workflow import _filing_mode

    assert _filing_mode("JP") == "official_form_pdf"
    assert _filing_mode(None) == "official_form_pdf"
    assert _filing_mode("ZZ") == "official_form_pdf"
