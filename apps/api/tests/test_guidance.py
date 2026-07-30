"""Tests for next-step guidance and US H-1B beachhead path."""

from __future__ import annotations

import json

from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from torii_api.services.checklist import US_H1B_DOCUMENT_REQUIREMENTS
from torii_api.services.eligibility import US_H1B_ELIGIBILITY_RULES
from torii_api.services.forms import US_H1B_FORM_TEMPLATE
from torii_api.services.guidance import compute_guidance
from torii_api.services.intake import JP_WORK_RENEWAL_QUESTIONS, US_H1B_QUESTIONS
from torii_api.services.ops_ingest import validated_for_promote


def test_compute_guidance_starts_at_intake() -> None:
    guidance = compute_guidance(
        intake_questions=JP_WORK_RENEWAL_QUESTIONS,
        answers={},
        eligibility_snapshot=None,
        checklist_items=[],
        generated_forms=[],
        review_flags_acknowledged=False,
        packet_snapshot=None,
        status="draft",
        has_intake_def=True,
        has_eligibility_def=True,
        has_document_def=True,
        has_form_def=True,
        scope_label="Japan · Work · Renewal",
    )
    assert guidance.phase == "intake"
    assert guidance.progress is not None
    assert guidance.progress.complete is False


def test_compute_guidance_blocked_without_defs() -> None:
    guidance = compute_guidance(
        intake_questions=None,
        answers={},
        eligibility_snapshot=None,
        checklist_items=[],
        generated_forms=[],
        review_flags_acknowledged=False,
        packet_snapshot=None,
        status="draft",
        has_intake_def=False,
        has_eligibility_def=False,
        has_document_def=False,
        has_form_def=False,
    )
    assert guidance.phase == "blocked"
    assert guidance.blocked_reason == "missing_live_workflow_definitions"


def test_validated_for_promote_requires_citations() -> None:
    assert not validated_for_promote(rules=[], documents=[], questions=[])
    assert validated_for_promote(
        rules=US_H1B_ELIGIBILITY_RULES,
        documents=US_H1B_DOCUMENT_REQUIREMENTS,
        questions=US_H1B_QUESTIONS,
    )


async def _seed_us(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO jurisdictions (code, name, is_live) VALUES ('US', 'United States', 1)"
            )
        )
        jid = (
            await conn.execute(text("SELECT id FROM jurisdictions WHERE code = 'US'"))
        ).scalar_one()
        await conn.execute(
            text(
                "INSERT INTO visa_categories (jurisdiction_id, code, name, is_live)"
                f" VALUES ({jid}, 'h1b', 'H-1B', 1)"
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
                    f"SELECT id FROM visa_categories WHERE jurisdiction_id = {jid} AND code = 'h1b'"
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
            {"q": json.dumps(US_H1B_QUESTIONS)},
        )
        await conn.execute(
            text(
                "INSERT INTO eligibility_rule_sets"
                " (jurisdiction_id, visa_category_id, case_action_id, rules, is_live)"
                f" VALUES ({jid}, {vc_id}, {ca_id}, :r, 1)"
            ),
            {"r": json.dumps(US_H1B_ELIGIBILITY_RULES)},
        )
        await conn.execute(
            text(
                "INSERT INTO document_requirement_sets"
                " (jurisdiction_id, visa_category_id, case_action_id, items, is_live)"
                f" VALUES ({jid}, {vc_id}, {ca_id}, :i, 1)"
            ),
            {"i": json.dumps(US_H1B_DOCUMENT_REQUIREMENTS)},
        )
        tpl = US_H1B_FORM_TEMPLATE
        await conn.execute(
            text(
                "INSERT INTO form_templates"
                " (jurisdiction_id, visa_category_id, case_action_id, code, version,"
                " official_title, citation, field_mappings, is_live)"
                f" VALUES ({jid}, {vc_id}, {ca_id}, :code, :version, :title, :citation, :fields, 1)"
            ),
            {
                "code": tpl["code"],
                "version": tpl["version"],
                "title": tpl["official_title"],
                "citation": json.dumps(tpl["citation"]),
                "fields": json.dumps(tpl["field_mappings"]),
            },
        )


async def test_us_h1b_guidance_and_intake(client: AsyncClient, engine: AsyncEngine) -> None:
    await _seed_us(engine)
    register = await client.post(
        "/v1/auth/register",
        json={"email": "us-guidance@example.com", "password": "secure-pass"},
    )
    assert register.status_code == 201
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    create = await client.post(
        "/v1/cases/scope",
        headers=headers,
        json={
            "jurisdiction_code": "US",
            "visa_category_code": "h1b",
            "action_code": "renewal",
        },
    )
    assert create.status_code == 201, create.text
    case_id = create.json()["id"]

    guidance = await client.get(f"/v1/cases/{case_id}/guidance", headers=headers)
    assert guidance.status_code == 200
    body = guidance.json()
    assert body["phase"] == "intake"
    assert "intake" in body["title"].lower() or "answer" in body["title"].lower()

    intake = await client.get(f"/v1/cases/{case_id}/intake", headers=headers)
    assert intake.status_code == 200
    questions = intake.json()["questions"]
    assert any(q["key"] == "full_name" and "prompt" in q for q in questions)

    answered = await client.put(
        f"/v1/cases/{case_id}/intake/answer",
        headers=headers,
        json={"key": "full_name", "value": "Ada Lovelace"},
    )
    assert answered.status_code == 200
    assert answered.json()["progress"]["answered"] >= 1

    detail = await client.get(f"/v1/cases/{case_id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["scope_label"]
    assert detail.json()["next_phase"] == "intake"
