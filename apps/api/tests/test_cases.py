"""Tests for US-01 — case scoping to jurisdiction + visa category + action."""

from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


async def test_visa_categories_list_empty(
    client: AsyncClient, engine: AsyncEngine
) -> None:
    """No categories before seeding."""
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO jurisdictions (code, name, is_live)"
                " VALUES ('JP', 'Japan', 1)"
            )
        )
    resp = await client.get(
        "/v1/cases/visa-categories", params={"jurisdiction_code": "JP"}
    )
    assert resp.status_code == 200
    assert resp.json() == []


async def test_visa_categories_404_for_unknown_jurisdiction(
    client: AsyncClient,
) -> None:
    resp = await client.get(
        "/v1/cases/visa-categories", params={"jurisdiction_code": "ZZ"}
    )
    assert resp.status_code == 404


async def test_case_actions_list_empty(
    client: AsyncClient, engine: AsyncEngine
) -> None:
    """No actions before seeding."""
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO jurisdictions (code, name, is_live)"
                " VALUES ('JP2', 'Japan2', 1)"
            )
        )
    resp = await client.get(
        "/v1/cases/case-actions", params={"jurisdiction_code": "JP2"}
    )
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
            text(
                "INSERT INTO jurisdictions (code, name, is_live)"
                " VALUES ('DE', 'Germany', 0)"
            )
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
