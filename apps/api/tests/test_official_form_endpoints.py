"""API surface for the official government forms: catalogue, download, and intake merge."""

from __future__ import annotations

import base64
import json

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from torii_api.services.intake import JP_WORK_RENEWAL_QUESTIONS
from torii_api.services.official_form_store import cache_dir


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


async def test_official_forms_endpoint_names_the_exact_sheet(
    client: AsyncClient, engine: AsyncEngine
) -> None:
    await _seed_scope(engine)
    token, case_id = await _register_and_scope(client, "forms@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.get(f"/v1/cases/{case_id}/official-forms", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["jurisdiction"] == "JP"
    assert body["visa_category"] == "work"
    assert body["action"] == "renewal"

    form = body["forms"][0]
    assert form["code"] == "jp_work_extension"
    assert form["title_ja"] == "在留期間更新許可申請書（技術・人文知識・国際業務）"
    assert form["series"] == "別記第三十号の二様式（第二十一条関係）"
    assert form["pdf_url"] == "https://www.moj.go.jp/isa/content/930004094.pdf"
    assert form["citation"]["url"].startswith("https://www.moj.go.jp/")
    # Nothing answered yet, so every item that applies is still outstanding. The
    # conditional detail line under the 有 / 無 disclosure is not one of them.
    assert form["missing_answer_keys"]
    assert form["total_items"] == len(form["missing_answer_keys"]) + 1
    assert "criminal_record_detail" not in form["missing_answer_keys"]


async def test_intake_asks_the_questions_the_official_form_needs(
    client: AsyncClient, engine: AsyncEngine
) -> None:
    await _seed_scope(engine)
    token, case_id = await _register_and_scope(client, "intake-forms@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.get(f"/v1/cases/{case_id}/intake", headers=headers)
    assert response.status_code == 200
    questions = {question["key"]: question for question in response.json()["questions"]}

    # Items that exist only because the ministry's form has a box for them.
    for key in ("sex", "marital_status", "home_town_city", "current_period_of_stay"):
        assert key in questions, f"intake does not ask for official-form item '{key}'"
        assert questions[key]["citation"]["url"].startswith("http")

    # A pack-authored question keeps the pack's own wording and gating.
    pack_keys = {question["key"] for question in JP_WORK_RENEWAL_QUESTIONS}
    for key in pack_keys & set(questions):
        assert questions[key]["prompt"]


async def test_answers_reach_the_form_and_unknown_codes_are_rejected(
    client: AsyncClient, engine: AsyncEngine
) -> None:
    await _seed_scope(engine)
    token, case_id = await _register_and_scope(client, "download@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    for key, value in (
        ("full_name", "Md Hojayfa Rahman"),
        ("nationality", "BD"),
        ("passport_number", "A05421997"),
    ):
        answered = await client.put(
            f"/v1/cases/{case_id}/intake/answer",
            json={"key": key, "value": value},
            headers=headers,
        )
        assert answered.status_code == 200, answered.text

    catalogue = await client.get(f"/v1/cases/{case_id}/official-forms", headers=headers)
    outstanding = catalogue.json()["forms"][0]["missing_answer_keys"]
    assert "full_name" not in outstanding
    assert "passport_number" not in outstanding

    unknown = await client.get(f"/v1/cases/{case_id}/export/official-form/us_i129", headers=headers)
    assert unknown.status_code == 404
    assert "not an official form" in unknown.json()["detail"]

    if not (cache_dir() / "jp_work_extension.pdf").is_file():
        pytest.skip("jp_work_extension not cached — run torii-fetch-forms")

    download = await client.get(
        f"/v1/cases/{case_id}/export/official-form/jp_work_extension?format=base64",
        headers=headers,
    )
    assert download.status_code == 200
    payload = download.json()
    assert payload["filename"].endswith("_jp_work_extension.pdf")
    assert base64.b64decode(payload["data_base64"]).startswith(b"%PDF-")
    assert payload["form"]["layout_verified"] is True
    assert payload["form"]["provenance"]["matches_pinned_revision"] is True
    assert "3 Passport number" not in payload["form"]["missing"]


async def test_application_form_download_serves_the_official_template(
    client: AsyncClient, engine: AsyncEngine
) -> None:
    """The generic download route routes a Japanese case to its ministry form."""
    if not (cache_dir() / "jp_work_extension.pdf").is_file():
        pytest.skip("jp_work_extension not cached — run torii-fetch-forms")
    await _seed_scope(engine)
    token, case_id = await _register_and_scope(client, "appform@example.com")
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
    content = base64.b64decode(response.json()["data_base64"])
    assert content.startswith(b"%PDF-")
    assert response.json()["filename"].endswith("_jp_work_extension.pdf")
