"""Tests for US-03 — save case progress and resume later."""

from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


async def _seed_live_scope(engine: AsyncEngine, code: str = "JP") -> None:
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO jurisdictions (code, name, is_live)"
                f" VALUES ('{code}', 'Country {code}', 1)"
            )
        )
        row = await conn.execute(text(f"SELECT id FROM jurisdictions WHERE code = '{code}'"))
        jurisdiction_id = row.scalar_one()
        await conn.execute(
            text(
                "INSERT INTO visa_categories (jurisdiction_id, code, name, is_live)"
                f" VALUES ({jurisdiction_id}, 'work', 'Work', 1)"
            )
        )
        await conn.execute(
            text(
                "INSERT INTO case_actions (jurisdiction_id, code, name, is_live)"
                f" VALUES ({jurisdiction_id}, 'renewal', 'Renewal', 1)"
            )
        )


async def _register(client: AsyncClient, email: str) -> str:
    resp = await client.post(
        "/v1/auth/register",
        json={"email": email, "password": "secure-pass"},
    )
    assert resp.status_code == 201
    return resp.json()["access_token"]


async def _scope_case(client: AsyncClient, token: str, jurisdiction_code: str = "JP") -> dict:
    resp = await client.post(
        "/v1/cases/scope",
        json={
            "jurisdiction_code": jurisdiction_code,
            "visa_category_code": "work",
            "action_code": "renewal",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    return resp.json()


async def test_save_and_resume_case_progress(client: AsyncClient, engine: AsyncEngine) -> None:
    await _seed_live_scope(engine, "JP")
    token = await _register(client, "resume@example.com")
    created = await _scope_case(client, token)
    case_id = created["id"]
    assert created["intake_answers"] == {}
    assert created["intake_step"] is None

    save = await client.patch(
        f"/v1/cases/{case_id}",
        json={
            "intake_answers": {"passport_number": "AB1234567", "years_in_country": 3},
            "intake_step": "employment",
            "notes": "paused mid-intake",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert save.status_code == 200
    body = save.json()
    assert body["intake_answers"]["passport_number"] == "AB1234567"
    assert body["intake_step"] == "employment"
    assert body["notes"] == "paused mid-intake"

    resume = await client.get(
        f"/v1/cases/{case_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resume.status_code == 200
    resumed = resume.json()
    assert resumed["intake_answers"] == {
        "passport_number": "AB1234567",
        "years_in_country": 3,
    }
    assert resumed["intake_step"] == "employment"
    assert resumed["notes"] == "paused mid-intake"


async def test_patch_leaves_omitted_fields_unchanged(
    client: AsyncClient, engine: AsyncEngine
) -> None:
    await _seed_live_scope(engine, "KR")
    token = await _register(client, "partial@example.com")
    created = await _scope_case(client, token, "KR")
    case_id = created["id"]

    await client.patch(
        f"/v1/cases/{case_id}",
        json={"intake_answers": {"name": "Ada"}, "intake_step": "identity"},
        headers={"Authorization": f"Bearer {token}"},
    )
    step_only = await client.patch(
        f"/v1/cases/{case_id}",
        json={"intake_step": "documents"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert step_only.status_code == 200
    body = step_only.json()
    assert body["intake_answers"] == {"name": "Ada"}
    assert body["intake_step"] == "documents"


async def test_get_case_not_visible_to_other_user(client: AsyncClient, engine: AsyncEngine) -> None:
    await _seed_live_scope(engine, "TW")
    owner = await _register(client, "owner@example.com")
    other = await _register(client, "other@example.com")
    created = await _scope_case(client, owner, "TW")

    resp = await client.get(
        f"/v1/cases/{created['id']}",
        headers={"Authorization": f"Bearer {other}"},
    )
    assert resp.status_code == 404


async def test_list_cases_returns_multiple_for_same_user(
    client: AsyncClient, engine: AsyncEngine
) -> None:
    """US-03.4 — an applicant can maintain more than one case."""
    await _seed_live_scope(engine, "SG")
    token = await _register(client, "multi@example.com")
    first = await _scope_case(client, token, "SG")
    second = await _scope_case(client, token, "SG")
    assert first["id"] != second["id"]

    listed = await client.get("/v1/cases", headers={"Authorization": f"Bearer {token}"})
    assert listed.status_code == 200
    ids = {c["id"] for c in listed.json()}
    assert ids == {first["id"], second["id"]}


async def test_get_case_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/v1/cases/1")
    assert resp.status_code == 401
