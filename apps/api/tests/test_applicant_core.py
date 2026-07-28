"""Smoke tests for the applicant-core workflow WIP (US-04/05/16)."""

from __future__ import annotations

import json

from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from torii_api.services.checklist import JP_WORK_RENEWAL_DOCUMENT_REQUIREMENTS
from torii_api.services.eligibility import JP_WORK_RENEWAL_ELIGIBILITY_RULES
from torii_api.services.forms import JP_WORK_RENEWAL_FORM_TEMPLATE
from torii_api.services.intake import JP_WORK_RENEWAL_QUESTIONS


async def _seed(engine: AsyncEngine) -> None:
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
                    "SELECT id FROM visa_categories WHERE jurisdiction_id ="
                    f" {jid} AND code = 'work'"
                )
            )
        ).scalar_one()
        ca_id = (
            await conn.execute(
                text(
                    "SELECT id FROM case_actions WHERE jurisdiction_id ="
                    f" {jid} AND code = 'renewal'"
                )
            )
        ).scalar_one()
        await conn.execute(
            text(
                "INSERT INTO intake_definitions"
                " (jurisdiction_id, visa_category_id, case_action_id, questions, is_live)"
                f" VALUES ({jid}, {vc_id}, {ca_id}, :q, 1)"
            ),
            {"q": json.dumps(JP_WORK_RENEWAL_QUESTIONS)},
        )
        await conn.execute(
            text(
                "INSERT INTO eligibility_rule_sets"
                " (jurisdiction_id, visa_category_id, case_action_id, rules, is_live)"
                f" VALUES ({jid}, {vc_id}, {ca_id}, :r, 1)"
            ),
            {"r": json.dumps(JP_WORK_RENEWAL_ELIGIBILITY_RULES)},
        )
        await conn.execute(
            text(
                "INSERT INTO document_requirement_sets"
                " (jurisdiction_id, visa_category_id, case_action_id, items, is_live)"
                f" VALUES ({jid}, {vc_id}, {ca_id}, :i, 1)"
            ),
            {"i": json.dumps(JP_WORK_RENEWAL_DOCUMENT_REQUIREMENTS)},
        )
        tpl = JP_WORK_RENEWAL_FORM_TEMPLATE
        await conn.execute(
            text(
                "INSERT INTO form_templates"
                " (jurisdiction_id, visa_category_id, case_action_id, code, version,"
                " is_live, official_title, citation, field_mappings)"
                f" VALUES ({jid}, {vc_id}, {ca_id}, :code, :version, 1, :title, :cit, :maps)"
            ),
            {
                "code": tpl["code"],
                "version": tpl["version"],
                "title": tpl["official_title"],
                "cit": json.dumps(tpl["citation"]),
                "maps": json.dumps(tpl["field_mappings"]),
            },
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
            "locale": "en",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert scoped.status_code == 201
    return token, scoped.json()["id"]


async def test_eligibility_checklist_and_locale(client: AsyncClient, engine: AsyncEngine) -> None:
    await _seed(engine)
    token, case_id = await _register_and_scope(client, "core@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    await client.put(
        f"/v1/cases/{case_id}/intake/answer",
        json={"key": "years_in_japan", "value": 0},
        headers=headers,
    )
    fail = await client.post(f"/v1/cases/{case_id}/eligibility/evaluate", headers=headers)
    assert fail.status_code == 200
    assert fail.json()["result"] == "fail"

    await client.put(
        f"/v1/cases/{case_id}/intake/answer",
        json={"key": "years_in_japan", "value": 2},
        headers=headers,
    )
    await client.put(
        f"/v1/cases/{case_id}/intake/answer",
        json={"key": "employment_status", "value": "employed"},
        headers=headers,
    )
    ok = await client.post(f"/v1/cases/{case_id}/eligibility/evaluate", headers=headers)
    assert ok.status_code == 200
    assert ok.json()["result"] == "pass"

    checklist = await client.post(f"/v1/cases/{case_id}/checklist/refresh", headers=headers)
    assert checklist.status_code == 200
    codes = {item["code"] for item in checklist.json()}
    assert "passport" in codes
    assert "employment_contract" in codes

    locale = await client.patch(
        f"/v1/cases/{case_id}/locale",
        json={"locale": "ja", "host_locale": "ja"},
        headers=headers,
    )
    assert locale.status_code == 200
    assert locale.json()["locale"] == "ja"
