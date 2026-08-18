"""Tests for the live-research case scope (ScopeResearch) pipeline."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from torii_api.services.ops_ingest import validated_for_promote
from torii_api.services.research import (
    research_expiry,
    research_payload,
)

RESEARCH_QUESTIONS = [
    {"key": "purpose", "prompt": "Why are you visiting the UK?", "type": "string"}
]
RESEARCH_RULES = [
    {
        "key": "purpose",
        "operator": "in",
        "value": "visit",
        "failure_status": "fail",
        "message": "Must be a permitted purpose.",
        "citation": {
            "authority": "gov.uk",
            "title": "Standard Visitor",
            "url": "https://www.gov.uk/standard-visitor",
        },
    }
]
RESEARCH_DOCS = [
    {
        "code": "passport",
        "name": {"en": "Passport"},
        "how_to_obtain": {"en": "Apply in your country"},
        "why_required": {"en": "Proves identity"},
        "is_required": True,
        "citation": {
            "authority": "gov.uk",
            "title": "Documents",
            "url": "https://www.gov.uk/standard-visitor/documents",
        },
    }
]
RESEARCH_FORMS = [
    {
        "code": "visa4",
        "version": "2026-08",
        "official_title": "Visa application",
        "field_mappings": [],
        "citation": {
            "authority": "gov.uk",
            "title": "Form",
            "url": "https://www.gov.uk/visa4",
        },
    }
]


def _payload() -> dict[str, Any]:
    return research_payload(
        intake_questions=RESEARCH_QUESTIONS,
        eligibility_rules=RESEARCH_RULES,
        document_requirements=RESEARCH_DOCS,
        form_templates=RESEARCH_FORMS,
    )


async def _register(client: AsyncClient, email: str) -> dict[str, str]:
    resp = await client.post("/v1/auth/register", json={"email": email, "password": "secure-pass"})
    assert resp.status_code == 201, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _seed_research_scope(
    engine: AsyncEngine,
    *,
    code: str = "UK",
    vc_research: int = 1,
    action_research: int = 1,
) -> tuple[int, int, int]:
    """Seed a research-enabled scope (no live definitions) and return (jid, vc_id, ca_id)."""
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO jurisdictions (code, name, is_live)"
                " VALUES (:code, 'United Kingdom', 1)"
            ),
            {"code": code},
        )
        jid = (
            await conn.execute(
                text("SELECT id FROM jurisdictions WHERE code = :code"), {"code": code}
            )
        ).scalar_one()
        await conn.execute(
            text(
                "INSERT INTO visa_categories (jurisdiction_id, code, name, is_live,"
                " research_enabled) VALUES (:j, 'visitor', 'Standard Visitor', 0, :r)"
            ),
            {"j": jid, "r": vc_research},
        )
        await conn.execute(
            text(
                "INSERT INTO case_actions (jurisdiction_id, code, name, is_live,"
                " research_enabled) VALUES (:j, 'apply', 'Apply', 0, :r)"
            ),
            {"j": jid, "r": action_research},
        )
        vc_id = (
            await conn.execute(
                text(
                    "SELECT id FROM visa_categories WHERE jurisdiction_id = :j AND code = 'visitor'"
                ),
                {"j": jid},
            )
        ).scalar_one()
        ca_id = (
            await conn.execute(
                text("SELECT id FROM case_actions WHERE jurisdiction_id = :j AND code = 'apply'"),
                {"j": jid},
            )
        ).scalar_one()
        return jid, vc_id, ca_id


async def _insert_research(
    engine: AsyncEngine,
    *,
    jid: int,
    vc_id: int,
    ca_id: int,
    origin: str | None = "BD",
    residence: str | None = "JP",
    status: str = "completed",
    payload: dict[str, Any] | None = None,
    expires_at: datetime | None = None,
) -> int:
    async with engine.begin() as conn:
        row = await conn.execute(
            text(
                "INSERT INTO scope_research"
                " (jurisdiction_id, visa_category_id, case_action_id, origin_country,"
                " residence_country, status, payload, source_pages, researched_at, expires_at)"
                " VALUES (:j, :v, :c, :o, :r, :s, :p, :sp, :ra, :e)"
            ),
            {
                "j": jid,
                "v": vc_id,
                "c": ca_id,
                "o": origin,
                "r": residence,
                "s": status,
                "p": json.dumps(payload or {}),
                "sp": json.dumps([]),
                "ra": datetime.now(UTC).isoformat(),
                "e": (expires_at or research_expiry()).isoformat(),
            },
        )
        return row.lastrowid


async def _outbox_topics(engine: AsyncEngine) -> list[str]:
    async with engine.begin() as conn:
        rows = await conn.execute(text("SELECT topic FROM outbox_events"))
        return [r[0] for r in rows.fetchall()]


async def _research_rows(
    engine: AsyncEngine, *, jid: int, vc_id: int, ca_id: int
) -> list[dict[str, Any]]:
    async with engine.begin() as conn:
        rows = await conn.execute(
            text(
                "SELECT status, origin_country, residence_country, payload"
                " FROM scope_research WHERE jurisdiction_id = :j AND visa_category_id = :v"
                " AND case_action_id = :c"
            ),
            {"j": jid, "v": vc_id, "c": ca_id},
        )
        return [dict(r._mapping) for r in rows.fetchall()]


async def test_scope_research_enqueues_when_no_live_defs(
    client: AsyncClient, engine: AsyncEngine
) -> None:
    jid, vc_id, ca_id = await _seed_research_scope(engine)
    headers = await _register(client, "research1@example.com")

    resp = await client.post(
        "/v1/cases/scope",
        headers=headers,
        json={
            "jurisdiction_code": "UK",
            "visa_category_code": "visitor",
            "action_code": "apply",
            "origin_country": "bd",
            "residence_country": "jp",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["origin_country"] == "BD"
    assert body["residence_country"] == "JP"
    assert body["research_id"] is not None

    rows = await _research_rows(engine, jid=jid, vc_id=vc_id, ca_id=ca_id)
    assert len(rows) == 1
    assert rows[0]["status"] == "queued"
    assert rows[0]["origin_country"] == "BD"
    assert rows[0]["residence_country"] == "JP"

    assert "case.research.queued" in await _outbox_topics(engine)

    guidance = await client.get(f"/v1/cases/{body['id']}/guidance", headers=headers)
    assert guidance.status_code == 200
    assert guidance.json()["phase"] == "research"


async def test_scope_research_reuses_completed_snapshot(
    client: AsyncClient, engine: AsyncEngine
) -> None:
    jid, vc_id, ca_id = await _seed_research_scope(engine)
    snapshot_id = await _insert_research(
        engine, jid=jid, vc_id=vc_id, ca_id=ca_id, payload=_payload()
    )
    headers = await _register(client, "research2@example.com")

    resp = await client.post(
        "/v1/cases/scope",
        headers=headers,
        json={
            "jurisdiction_code": "UK",
            "visa_category_code": "visitor",
            "action_code": "apply",
            "origin_country": "BD",
            "residence_country": "JP",
        },
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["research_id"] == snapshot_id

    # Reuse must not enqueue another research run.
    assert "case.research.queued" not in await _outbox_topics(engine)
    rows = await _research_rows(engine, jid=jid, vc_id=vc_id, ca_id=ca_id)
    assert len(rows) == 1
    assert rows[0]["status"] == "completed"

    # The research snapshot feeds intake and guidance straight away.
    case_id = resp.json()["id"]
    intake = await client.get(f"/v1/cases/{case_id}/intake", headers=headers)
    assert intake.status_code == 200
    keys = [q["key"] for q in intake.json()["questions"]]
    assert keys == ["purpose"]

    guidance = await client.get(f"/v1/cases/{case_id}/guidance", headers=headers)
    assert guidance.json()["phase"] == "intake"


async def test_scope_research_requires_research_enabled_on_both(
    client: AsyncClient, engine: AsyncEngine
) -> None:
    jid, _, _ = await _seed_research_scope(engine, vc_research=1, action_research=0)
    headers = await _register(client, "research3@example.com")

    resp = await client.post(
        "/v1/cases/scope",
        headers=headers,
        json={
            "jurisdiction_code": "UK",
            "visa_category_code": "visitor",
            "action_code": "apply",
        },
    )
    assert resp.status_code == 400
    assert "not available" in resp.json()["detail"]


async def test_scope_research_failed_leads_to_human_help_guidance(
    client: AsyncClient, engine: AsyncEngine
) -> None:
    jid, vc_id, ca_id = await _seed_research_scope(engine)
    headers = await _register(client, "research4@example.com")

    create = await client.post(
        "/v1/cases/scope",
        headers=headers,
        json={
            "jurisdiction_code": "UK",
            "visa_category_code": "visitor",
            "action_code": "apply",
            "origin_country": "BD",
            "residence_country": "JP",
        },
    )
    case_id = create.json()["id"]
    research_id = create.json()["research_id"]

    # Simulate the worker failing the run.
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "UPDATE scope_research SET status = 'failed', error = 'scrape errored'"
                " WHERE id = :i"
            ),
            {"i": research_id},
        )

    guidance = await client.get(f"/v1/cases/{case_id}/guidance", headers=headers)
    assert guidance.status_code == 200
    assert guidance.json()["phase"] == "research"
    assert guidance.json()["blocked_reason"] == "research_failed"


async def test_re_research_resets_stale_snapshot(client: AsyncClient, engine: AsyncEngine) -> None:
    jid, vc_id, ca_id = await _seed_research_scope(engine)
    headers = await _register(client, "research5@example.com")

    create = await client.post(
        "/v1/cases/scope",
        headers=headers,
        json={
            "jurisdiction_code": "UK",
            "visa_category_code": "visitor",
            "action_code": "apply",
            "origin_country": "BD",
            "residence_country": "JP",
        },
    )
    case_id = create.json()["id"]
    research_id = create.json()["research_id"]

    # Simulate a completed snapshot that has since expired (stale).
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "UPDATE scope_research SET status = 'completed', payload = :p,"
                " expires_at = :e WHERE id = :i"
            ),
            {
                "p": json.dumps(_payload()),
                "e": (datetime.now(UTC) - timedelta(days=1)).isoformat(),
                "i": research_id,
            },
        )

    resp = await client.post(f"/v1/cases/{case_id}/research", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "queued"

    rows = await _research_rows(engine, jid=jid, vc_id=vc_id, ca_id=ca_id)
    assert rows[0]["status"] == "queued"
    assert json.loads(rows[0]["payload"]) == {}
    assert "case.research.queued" in await _outbox_topics(engine)


async def test_validated_for_promote_gate_drops_uncited_payloads() -> None:
    # Complete + cited payload passes.
    assert validated_for_promote(
        rules=RESEARCH_RULES, documents=RESEARCH_DOCS, questions=RESEARCH_QUESTIONS
    )
    # A single uncited document fails the whole gate (NF-2: nothing uncited goes live).
    bad_docs = [
        {
            "code": "bank",
            "name": {"en": "Bank statement"},
            "is_required": True,
            "citation": {"authority": "unknown", "title": "No source", "url": ""},
        }
    ]
    assert not validated_for_promote(
        rules=RESEARCH_RULES, documents=bad_docs, questions=RESEARCH_QUESTIONS
    )
    # Missing categories fail.
    assert not validated_for_promote(
        rules=[], documents=RESEARCH_DOCS, questions=RESEARCH_QUESTIONS
    )
