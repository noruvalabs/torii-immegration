"""Tests for US-30 — staff roles and scoped access (admin user management)."""

from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


async def _register_and_login(
    client: AsyncClient, email: str
) -> str:
    """Register a user and return their JWT token."""
    await client.post(
        "/v1/auth/register",
        json={"email": email, "password": "secure-pass"},
    )
    login = await client.post(
        "/v1/auth/login",
        json={"email_or_username": email, "password": "secure-pass"},
    )
    return login.json()["access_token"]


async def _seed_admin(engine: AsyncEngine) -> None:
    """Insert an admin user directly into the DB."""
    from torii_api.auth.security import hash_password

    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO users (email, password_hash, role, is_active, email_verified)"
                " VALUES (:email, :pw, 'admin', 1, 1)"
            ),
            {"email": "real-admin@example.com", "pw": hash_password("admin-pass-123")},
        )


async def test_list_users_requires_admin(client: AsyncClient) -> None:
    token = await _register_and_login(client, "applicant@example.com")
    resp = await client.get(
        "/v1/admin/users",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


async def test_list_users_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/v1/admin/users")
    assert resp.status_code == 401


async def test_admin_can_list_users(
    client: AsyncClient, engine: AsyncEngine
) -> None:
    await _seed_admin(engine)
    login = await client.post(
        "/v1/auth/login",
        json={
            "email_or_username": "real-admin@example.com",
            "password": "admin-pass-123",
        },
    )
    token = login.json()["access_token"]
    resp = await client.get(
        "/v1/admin/users",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    users = resp.json()
    assert len(users) >= 1
    assert any(u["email"] == "real-admin@example.com" for u in users)


async def test_admin_can_filter_by_role(
    client: AsyncClient, engine: AsyncEngine
) -> None:
    await _seed_admin(engine)
    # Create an applicant
    await client.post(
        "/v1/auth/register",
        json={"email": "app@example.com", "password": "secure-pass"},
    )
    login = await client.post(
        "/v1/auth/login",
        json={
            "email_or_username": "real-admin@example.com",
            "password": "admin-pass-123",
        },
    )
    token = login.json()["access_token"]
    resp = await client.get(
        "/v1/admin/users",
        params={"role": "applicant"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    users = resp.json()
    assert all(u["role"] == "applicant" for u in users)


async def test_admin_can_get_user_by_id(
    client: AsyncClient, engine: AsyncEngine
) -> None:
    await _seed_admin(engine)
    # Create another user
    reg = await client.post(
        "/v1/auth/register",
        json={"email": "target@example.com", "password": "secure-pass"},
    )
    target_id = reg.json()["user"]["id"]

    login = await client.post(
        "/v1/auth/login",
        json={
            "email_or_username": "real-admin@example.com",
            "password": "admin-pass-123",
        },
    )
    token = login.json()["access_token"]
    resp = await client.get(
        f"/v1/admin/users/{target_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["email"] == "target@example.com"


async def test_admin_can_change_user_role(
    client: AsyncClient, engine: AsyncEngine
) -> None:
    await _seed_admin(engine)
    reg = await client.post(
        "/v1/auth/register",
        json={"email": "promote@example.com", "password": "secure-pass"},
    )
    target_id = reg.json()["user"]["id"]

    login = await client.post(
        "/v1/auth/login",
        json={
            "email_or_username": "real-admin@example.com",
            "password": "admin-pass-123",
        },
    )
    token = login.json()["access_token"]
    resp = await client.patch(
        f"/v1/admin/users/{target_id}/role",
        json={"role": "ops"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "ops"


async def test_admin_cannot_change_own_role(
    client: AsyncClient, engine: AsyncEngine
) -> None:
    await _seed_admin(engine)
    login = await client.post(
        "/v1/auth/login",
        json={
            "email_or_username": "real-admin@example.com",
            "password": "admin-pass-123",
        },
    )
    token = login.json()["access_token"]
    admin_id = login.json()["user"]["id"]
    resp = await client.patch(
        f"/v1/admin/users/{admin_id}/role",
        json={"role": "applicant"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400


async def test_admin_can_deactivate_user(
    client: AsyncClient, engine: AsyncEngine
) -> None:
    await _seed_admin(engine)
    reg = await client.post(
        "/v1/auth/register",
        json={"email": "deact@example.com", "password": "secure-pass"},
    )
    target_id = reg.json()["user"]["id"]

    login = await client.post(
        "/v1/auth/login",
        json={
            "email_or_username": "real-admin@example.com",
            "password": "admin-pass-123",
        },
    )
    token = login.json()["access_token"]
    resp = await client.patch(
        f"/v1/admin/users/{target_id}/active",
        json={"is_active": False},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False

    # Deactivated user cannot login
    login2 = await client.post(
        "/v1/auth/login",
        json={
            "email_or_username": "deact@example.com",
            "password": "secure-pass",
        },
    )
    assert login2.status_code == 403


async def test_admin_cannot_deactivate_self(
    client: AsyncClient, engine: AsyncEngine
) -> None:
    await _seed_admin(engine)
    login = await client.post(
        "/v1/auth/login",
        json={
            "email_or_username": "real-admin@example.com",
            "password": "admin-pass-123",
        },
    )
    token = login.json()["access_token"]
    admin_id = login.json()["user"]["id"]
    resp = await client.patch(
        f"/v1/admin/users/{admin_id}/active",
        json={"is_active": False},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400


async def test_admin_user_count(
    client: AsyncClient, engine: AsyncEngine
) -> None:
    await _seed_admin(engine)
    await client.post(
        "/v1/auth/register",
        json={"email": "u1@example.com", "password": "secure-pass"},
    )
    await client.post(
        "/v1/auth/register",
        json={"email": "u2@example.com", "password": "secure-pass"},
    )
    login = await client.post(
        "/v1/auth/login",
        json={
            "email_or_username": "real-admin@example.com",
            "password": "admin-pass-123",
        },
    )
    token = login.json()["access_token"]
    resp = await client.get(
        "/v1/admin/users/count",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    counts = resp.json()
    assert counts["admin"] >= 1
    assert counts["applicant"] >= 2
