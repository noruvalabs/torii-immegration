"""Tests for applicant-driven case deletion."""

from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


async def _seed_minimal_us_scope(engine: AsyncEngine) -> tuple[int, int, int]:
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
                "INSERT INTO visa_categories (jurisdiction_id, code, name, is_live) "
                "VALUES (:jid, 'h1b', 'H-1B Specialty Worker', 1)"
            ),
            {"jid": jid},
        )
        vc_id = (
            await conn.execute(
                text(
                    "SELECT id FROM visa_categories WHERE jurisdiction_id = :jid AND code = 'h1b'"
                ),
                {"jid": jid},
            )
        ).scalar_one()

        await conn.execute(
            text(
                "INSERT INTO case_actions (jurisdiction_id, code, name, is_live) "
                "VALUES (:jid, 'renewal', 'Renewal', 1)"
            ),
            {"jid": jid},
        )
        ca_id = (
            await conn.execute(
                text(
                    "SELECT id FROM case_actions WHERE jurisdiction_id = :jid AND code = 'renewal'"
                ),
                {"jid": jid},
            )
        ).scalar_one()

    return jid, vc_id, ca_id


async def test_delete_case_removes_it(client: AsyncClient, engine: AsyncEngine) -> None:
    await _seed_minimal_us_scope(engine)

    register = await client.post(
        "/v1/auth/register",
        json={"email": "delete@example.com", "password": "secure-pass"},
    )
    assert register.status_code == 201
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    scoped = await client.post(
        "/v1/cases/scope",
        headers=headers,
        json={
            "jurisdiction_code": "US",
            "visa_category_code": "h1b",
            "action_code": "renewal",
            "locale": "en",
        },
    )
    assert scoped.status_code == 201
    case_id = scoped.json()["id"]

    resp = await client.delete(f"/v1/cases/{case_id}", headers=headers)
    assert resp.status_code == 204

    get_resp = await client.get(f"/v1/cases/{case_id}", headers=headers)
    assert get_resp.status_code == 404


async def test_delete_case_rejects_submitted(client: AsyncClient, engine: AsyncEngine) -> None:
    await _seed_minimal_us_scope(engine)

    register = await client.post(
        "/v1/auth/register",
        json={"email": "delete-submitted@example.com", "password": "secure-pass"},
    )
    assert register.status_code == 201
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    scoped = await client.post(
        "/v1/cases/scope",
        headers=headers,
        json={
            "jurisdiction_code": "US",
            "visa_category_code": "h1b",
            "action_code": "renewal",
            "locale": "en",
        },
    )
    assert scoped.status_code == 201
    case_id = scoped.json()["id"]

    async with engine.begin() as conn:
        await conn.execute(
            text("UPDATE cases SET status = 'submitted' WHERE id = :id"), {"id": case_id}
        )

    resp = await client.delete(f"/v1/cases/{case_id}", headers=headers)
    assert resp.status_code == 409


async def test_archive_and_unarchive_submitted_case(client: AsyncClient, engine: AsyncEngine) -> None:
    await _seed_minimal_us_scope(engine)

    register = await client.post(
        "/v1/auth/register",
        json={"email": "archive-submitted@example.com", "password": "secure-pass"},
    )
    assert register.status_code == 201
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    scoped = await client.post(
        "/v1/cases/scope",
        headers=headers,
        json={
            "jurisdiction_code": "US",
            "visa_category_code": "h1b",
            "action_code": "renewal",
            "locale": "en",
        },
    )
    assert scoped.status_code == 201
    case_id = scoped.json()["id"]

    # Mark as submitted
    async with engine.begin() as conn:
        await conn.execute(
            text("UPDATE cases SET status = 'submitted' WHERE id = :id"), {"id": case_id}
        )

    # Archive the submitted case
    arch_resp = await client.post(f"/v1/cases/{case_id}/archive", headers=headers)
    assert arch_resp.status_code == 200
    assert arch_resp.json()["is_archived"] is True

    # Check listing returns is_archived=True
    list_resp = await client.get("/v1/cases", headers=headers)
    assert list_resp.status_code == 200
    cases = list_resp.json()
    assert any(c["id"] == case_id and c["is_archived"] is True for c in cases)

    # Unarchive the submitted case
    unarch_resp = await client.post(f"/v1/cases/{case_id}/unarchive", headers=headers)
    assert unarch_resp.status_code == 200
    assert unarch_resp.json()["is_archived"] is False

