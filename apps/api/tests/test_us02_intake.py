"""Tests for US-02 — branching intake questionnaire."""

from __future__ import annotations

import json

from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from torii_api.services.intake import JP_WORK_RENEWAL_QUESTIONS


async def _seed_jp_work_renewal_with_intake(engine: AsyncEngine) -> None:
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
                text(
                    "SELECT id FROM visa_categories"
                    f" WHERE jurisdiction_id = {jid} AND code = 'work'"
                )
            )
        ).scalar_one()
        ca_id = (
            await conn.execute(
                text(
                    "SELECT id FROM case_actions"
                    f" WHERE jurisdiction_id = {jid} AND code = 'renewal'"
                )
            )
        ).scalar_one()
        questions_json = json.dumps(JP_WORK_RENEWAL_QUESTIONS)
        await conn.execute(
            text(
                "INSERT INTO intake_definitions"
                " (jurisdiction_id, visa_category_id, case_action_id, questions, is_live)"
                f" VALUES ({jid}, {vc_id}, {ca_id}, :questions, 1)"
            ),
            {"questions": questions_json},
        )


async def _register_and_scope(client: AsyncClient, email: str) -> tuple[str, int]:
    register = await client.post(
        "/v1/auth/register",
        json={"email": email, "password": "secure-pass"},
    )
    assert register.status_code == 201
    token = register.json()["access_token"]
    scoped = await client.post(
        "/v1/cases/scope",
        json={
            "jurisdiction_code": "JP",
            "visa_category_code": "work",
            "action_code": "renewal",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert scoped.status_code == 201
    return token, scoped.json()["id"]


async def test_intake_hides_sponsor_until_needed(client: AsyncClient, engine: AsyncEngine) -> None:
    await _seed_jp_work_renewal_with_intake(engine)
    token, case_id = await _register_and_scope(client, "intake1@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    state = await client.get(f"/v1/cases/{case_id}/intake", headers=headers)
    assert state.status_code == 200
    body = state.json()
    keys = [q["key"] for q in body["questions"]]
    assert "full_name" in keys
    assert "sponsor_name" not in keys
    assert body["progress"]["answered"] == 0
    assert body["progress"]["complete"] is False

    await client.put(
        f"/v1/cases/{case_id}/intake/answer",
        json={"key": "full_name", "value": "Ada Lovelace"},
        headers=headers,
    )
    await client.put(
        f"/v1/cases/{case_id}/intake/answer",
        json={"key": "passport_number", "value": "AB1234567"},
        headers=headers,
    )
    await client.put(
        f"/v1/cases/{case_id}/intake/answer",
        json={"key": "years_in_japan", "value": 3},
        headers=headers,
    )
    with_sponsor = await client.put(
        f"/v1/cases/{case_id}/intake/answer",
        json={"key": "has_sponsor", "value": True},
        headers=headers,
    )
    assert with_sponsor.status_code == 200
    keys_after = [q["key"] for q in with_sponsor.json()["questions"]]
    assert "sponsor_name" in keys_after


async def test_intake_validates_answers(client: AsyncClient, engine: AsyncEngine) -> None:
    await _seed_jp_work_renewal_with_intake(engine)
    token, case_id = await _register_and_scope(client, "intake2@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    bad = await client.put(
        f"/v1/cases/{case_id}/intake/answer",
        json={"key": "years_in_japan", "value": -1},
        headers=headers,
    )
    assert bad.status_code == 422
    assert "at least" in bad.json()["detail"]

    bad_type = await client.put(
        f"/v1/cases/{case_id}/intake/answer",
        json={"key": "has_sponsor", "value": "yes"},
        headers=headers,
    )
    assert bad_type.status_code == 422


async def test_changing_branch_clears_stale_answers(
    client: AsyncClient, engine: AsyncEngine
) -> None:
    await _seed_jp_work_renewal_with_intake(engine)
    token, case_id = await _register_and_scope(client, "intake3@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    for key, value in [
        ("full_name", "Grace Hopper"),
        ("passport_number", "CD9999999"),
        ("years_in_japan", 5),
        ("has_sponsor", True),
        ("sponsor_name", "Acme K.K."),
        ("employment_status", "employed"),
        ("employer_name", "Acme K.K."),
    ]:
        resp = await client.put(
            f"/v1/cases/{case_id}/intake/answer",
            json={"key": key, "value": value},
            headers=headers,
        )
        assert resp.status_code == 200, resp.text

    flipped = await client.put(
        f"/v1/cases/{case_id}/intake/answer",
        json={"key": "has_sponsor", "value": False},
        headers=headers,
    )
    assert flipped.status_code == 200
    answers = flipped.json()["answers"]
    assert answers["has_sponsor"] is False
    assert "sponsor_name" not in answers
    assert answers["employer_name"] == "Acme K.K."
    keys = [q["key"] for q in flipped.json()["questions"]]
    assert "sponsor_name" not in keys


async def test_cannot_answer_hidden_question(client: AsyncClient, engine: AsyncEngine) -> None:
    await _seed_jp_work_renewal_with_intake(engine)
    token, case_id = await _register_and_scope(client, "intake4@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.put(
        f"/v1/cases/{case_id}/intake/answer",
        json={"key": "sponsor_name", "value": "Hidden Co"},
        headers=headers,
    )
    assert resp.status_code == 400
    assert "not applicable" in resp.json()["detail"]
