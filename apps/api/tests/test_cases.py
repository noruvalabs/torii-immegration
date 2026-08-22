"""Tests for US-01 — case scoping to jurisdiction + visa category + action."""

from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


async def test_visa_categories_list_empty(client: AsyncClient, engine: AsyncEngine) -> None:
    """No categories before seeding."""
    async with engine.begin() as conn:
        await conn.execute(
            text("INSERT INTO jurisdictions (code, name, is_live) VALUES ('JP', 'Japan', 1)")
        )
    resp = await client.get("/v1/cases/visa-categories", params={"jurisdiction_code": "JP"})
    assert resp.status_code == 200
    assert resp.json() == []


async def test_visa_categories_404_for_unknown_jurisdiction(
    client: AsyncClient,
) -> None:
    resp = await client.get("/v1/cases/visa-categories", params={"jurisdiction_code": "ZZ"})
    assert resp.status_code == 404


async def test_case_actions_list_empty(client: AsyncClient, engine: AsyncEngine) -> None:
    """No actions before seeding."""
    async with engine.begin() as conn:
        await conn.execute(
            text("INSERT INTO jurisdictions (code, name, is_live) VALUES ('JP2', 'Japan2', 1)")
        )
    resp = await client.get("/v1/cases/case-actions", params={"jurisdiction_code": "JP2"})
    assert resp.status_code == 200
    assert resp.json() == []


async def test_scope_case_rejects_unknown_jurisdiction(
    client: AsyncClient,
) -> None:
    """Scoping with a non-existent jurisdiction returns 400."""
    register = await client.post(
        "/v1/auth/register",
        json={"email": "scope@example.com", "password": "secure-pass"},
    )
    token = register.json()["access_token"]

    resp = await client.post(
        "/v1/cases/scope",
        json={
            "jurisdiction_code": "ZZ",
            "visa_category_code": "work",
            "action_code": "renewal",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400


async def test_scope_case_rejects_inactive_jurisdiction(
    client: AsyncClient, engine: AsyncEngine
) -> None:
    """Scoping with a non-live jurisdiction returns 400."""
    async with engine.begin() as conn:
        await conn.execute(
            text("INSERT INTO jurisdictions (code, name, is_live) VALUES ('DE', 'Germany', 0)")
        )
    register = await client.post(
        "/v1/auth/register",
        json={"email": "scope2@example.com", "password": "secure-pass"},
    )
    token = register.json()["access_token"]

    resp = await client.post(
        "/v1/cases/scope",
        json={
            "jurisdiction_code": "DE",
            "visa_category_code": "work",
            "action_code": "renewal",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    assert "not available" in resp.json()["detail"]


async def test_list_cases_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/v1/cases")
    assert resp.status_code == 401


async def test_scope_case_uk_change_of_status(client: AsyncClient, engine: AsyncEngine) -> None:
    """Scoping with UK + work + change_of_status succeeds."""
    async with engine.begin() as conn:
        await conn.execute(
            text("INSERT INTO jurisdictions (code, name, is_live) VALUES ('UK', 'United Kingdom', 1)")
        )
        jid = (
            await conn.execute(text("SELECT id FROM jurisdictions WHERE code = 'UK'"))
        ).scalar_one()
        await conn.execute(
            text(
                "INSERT INTO visa_categories (jurisdiction_id, code, name, is_live)"
                f" VALUES ({jid}, 'work', 'Skilled Worker Visa', 1)"
            )
        )
        await conn.execute(
            text(
                "INSERT INTO case_actions (jurisdiction_id, code, name, is_live)"
                f" VALUES ({jid}, 'change_of_status', 'Change of status', 1)"
            )
        )

    register = await client.post(
        "/v1/auth/register",
        json={"email": "uk_cos@example.com", "password": "secure-pass"},
    )
    token = register.json()["access_token"]

    resp = await client.post(
        "/v1/cases/scope",
        json={
            "jurisdiction_code": "UK",
            "visa_category_code": "work",
            "action_code": "change_of_status",
            "origin_country": "BD",
            "residence_country": "BD",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["status"] == "draft"
    assert data["reference"].startswith("UK-")


async def test_scope_case_any_global_origin(client: AsyncClient, engine: AsyncEngine) -> None:
    """Scoping a case from any country (e.g. India, Nigeria, Brazil) works cleanly."""
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
                f" VALUES ({jid}, 'work', 'Work Visa', 1)"
            )
        )
        await conn.execute(
            text(
                "INSERT INTO case_actions (jurisdiction_id, code, name, is_live)"
                f" VALUES ({jid}, 'new', 'New Visa', 1)"
            )
        )

    register = await client.post(
        "/v1/auth/register",
        json={"email": "global_user@example.com", "password": "secure-pass"},
    )
    token = register.json()["access_token"]

    for origin, residence in [("IN", "AE"), ("NG", "NG"), ("BR", "BR"), ("KE", "GB")]:
        resp = await client.post(
            "/v1/cases/scope",
            json={
                "jurisdiction_code": "JP",
                "visa_category_code": "work",
                "action_code": "new",
                "origin_country": origin,
                "residence_country": residence,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["origin_country"] == origin
        assert data["residence_country"] == residence
