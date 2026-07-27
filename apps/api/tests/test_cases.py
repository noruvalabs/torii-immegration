"""Tests for US-01 — case scoping to jurisdiction + visa category + action."""

from __future__ import annotations

from httpx import AsyncClient


async def _seed_scope_data(client: AsyncClient) -> None:
    """Create a live jurisdiction with visa categories and actions for tests."""
    await client.post(
        "/v1/jurisdictions",
        json={"code": "JP", "name": "Japan", "is_live": True},
    )
    # Create visa categories via raw DB (no admin API yet) — use the management seed
    # For tests we rely on the test fixture creating a fresh DB; seed via the API's
    # own endpoints where possible, otherwise the fixture's in-memory DB is empty.
    # Since we don't have admin CRUD for visa categories yet, we insert via the
    # cases router won't work without them. We need a helper.
    # The simplest approach: the test fixture creates tables from models directly,
    # so we can use the session to insert seed data. But the test client doesn't
    # expose the session. We'll create a small fixture helper.


async def test_visa_categories_list_empty(client: AsyncClient) -> None:
    """No categories before seeding."""
    await client.post(
        "/v1/jurisdictions",
        json={"code": "JP", "name": "Japan", "is_live": True},
    )
    resp = await client.get("/v1/cases/visa-categories", params={"jurisdiction_code": "JP"})
    assert resp.status_code == 200
    assert resp.json() == []


async def test_visa_categories_404_for_unknown_jurisdiction(client: AsyncClient) -> None:
    resp = await client.get("/v1/cases/visa-categories", params={"jurisdiction_code": "ZZ"})
    assert resp.status_code == 404


async def test_case_actions_list_empty(client: AsyncClient) -> None:
    """No actions before seeding."""
    await client.post(
        "/v1/jurisdictions",
        json={"code": "JP", "name": "Japan", "is_live": True},
    )
    resp = await client.get("/v1/cases/case-actions", params={"jurisdiction_code": "JP"})
    assert resp.status_code == 200
    assert resp.json() == []


async def test_scope_case_rejects_unknown_jurisdiction(client: AsyncClient) -> None:
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


async def test_scope_case_rejects_inactive_jurisdiction(client: AsyncClient) -> None:
    """Scoping with a non-live jurisdiction returns 400."""
    await client.post(
        "/v1/jurisdictions",
        json={"code": "DE", "name": "Germany", "is_live": False},
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
