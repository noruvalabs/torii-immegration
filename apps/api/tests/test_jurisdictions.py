from httpx import AsyncClient


async def _register_user(client: AsyncClient, email: str = "testuser@example.com") -> str:
    """Register a user and return their token."""
    await client.post(
        "/v1/auth/register",
        json={"email": email, "password": "secure-pass"},
    )
    login = await client.post(
        "/v1/auth/login",
        json={"email_or_username": email, "password": "secure-pass"},
    )
    return login.json()["access_token"]


async def test_list_jurisdictions_public(client: AsyncClient) -> None:
    """GET /v1/jurisdictions works without auth."""
    resp = await client.get("/v1/jurisdictions")
    assert resp.status_code == 200


async def test_create_jurisdiction_requires_admin(client: AsyncClient) -> None:
    """POST /v1/jurisdictions requires admin role — applicant gets 403."""
    token = await _register_user(client)
    resp = await client.post(
        "/v1/jurisdictions",
        json={"code": "JP", "name": "Japan", "is_live": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


async def test_update_jurisdiction_requires_admin(client: AsyncClient) -> None:
    """PATCH /v1/jurisdictions/{id} requires admin role."""
    token = await _register_user(client)
    resp = await client.patch(
        "/v1/jurisdictions/1",
        json={"name": "Updated"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


async def test_delete_jurisdiction_requires_admin(client: AsyncClient) -> None:
    """DELETE /v1/jurisdictions/{id} requires admin role."""
    token = await _register_user(client)
    resp = await client.delete(
        "/v1/jurisdictions/1",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


async def test_visa_category_list_public(client: AsyncClient, engine) -> None:
    """GET /v1/jurisdictions/{id}/visa-categories works without auth."""
    async with engine.begin() as conn:
        from sqlalchemy import text
        await conn.execute(
            text("INSERT INTO jurisdictions (code, name, is_live) VALUES ('JP', 'Japan', 1)")
        )
    resp = await client.get("/v1/jurisdictions/1/visa-categories")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_visa_category_create_requires_admin(client: AsyncClient, engine) -> None:
    """POST /v1/jurisdictions/{id}/visa-categories requires admin role."""
    async with engine.begin() as conn:
        from sqlalchemy import text
        await conn.execute(
            text("INSERT INTO jurisdictions (code, name, is_live) VALUES ('JP', 'Japan', 1)")
        )
    token = await _register_user(client)
    resp = await client.post(
        "/v1/jurisdictions/1/visa-categories",
        json={"code": "work", "name": "Work Visa"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


async def test_case_action_list_public(client: AsyncClient, engine) -> None:
    """GET /v1/jurisdictions/{id}/case-actions works without auth."""
    async with engine.begin() as conn:
        from sqlalchemy import text
        await conn.execute(
            text("INSERT INTO jurisdictions (code, name, is_live) VALUES ('JP', 'Japan', 1)")
        )
    resp = await client.get("/v1/jurisdictions/1/case-actions")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_case_action_create_requires_admin(client: AsyncClient, engine) -> None:
    """POST /v1/jurisdictions/{id}/case-actions requires admin role."""
    async with engine.begin() as conn:
        from sqlalchemy import text
        await conn.execute(
            text("INSERT INTO jurisdictions (code, name, is_live) VALUES ('JP', 'Japan', 1)")
        )
    token = await _register_user(client)
    resp = await client.post(
        "/v1/jurisdictions/1/case-actions",
        json={"code": "renewal", "name": "Renewal"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
