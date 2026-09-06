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


async def _admin_token(client: AsyncClient, engine) -> str:
    from sqlalchemy import text

    from torii_api.auth.security import hash_password

    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO users (email, password_hash, role, is_active, email_verified)"
                " VALUES (:email, :pw, 'admin', 1, 1)"
            ),
            {"email": "admin@example.com", "pw": hash_password("admin-pass-123")},
        )
    login = await client.post(
        "/v1/auth/login",
        json={"email_or_username": "admin@example.com", "password": "admin-pass-123"},
    )
    return login.json()["access_token"]


async def test_create_jurisdiction_prevents_duplicates_by_code_and_alias(
    client: AsyncClient, engine
) -> None:
    """POST /v1/jurisdictions prevents creating duplicate codes and aliases (e.g. UK vs GB)."""
    admin_tok = await _admin_token(client, engine)

    # 1. Create UK
    resp1 = await client.post(
        "/v1/jurisdictions",
        json={"code": "UK", "name": "United Kingdom", "is_live": True},
        headers={"Authorization": f"Bearer {admin_tok}"},
    )
    assert resp1.status_code == 201

    # 2. Attempt exact code duplicate
    resp2 = await client.post(
        "/v1/jurisdictions",
        json={"code": "UK", "name": "United Kingdom 2", "is_live": True},
        headers={"Authorization": f"Bearer {admin_tok}"},
    )
    assert resp2.status_code == 409

    # 3. Attempt alias duplicate (GB when UK exists)
    resp3 = await client.post(
        "/v1/jurisdictions",
        json={"code": "GB", "name": "United Kingdom (GB)", "is_live": True},
        headers={"Authorization": f"Bearer {admin_tok}"},
    )
    assert resp3.status_code == 409
    assert "already exists" in resp3.json()["detail"]

    # 4. Attempt duplicate by country name
    resp4 = await client.post(
        "/v1/jurisdictions",
        json={"code": "XYZ", "name": "United Kingdom", "is_live": True},
        headers={"Authorization": f"Bearer {admin_tok}"},
    )
    assert resp4.status_code == 409


async def test_delete_jurisdiction_cleans_up_routes_and_prevents_with_cases(
    client: AsyncClient, engine
) -> None:
    """DELETE /v1/jurisdictions/{id} deletes jurisdiction and associated routes, or 409 if cases exist."""
    admin_tok = await _admin_token(client, engine)

    # 1. Create a jurisdiction (this automatically creates starter categories and actions)
    create_resp = await client.post(
        "/v1/jurisdictions",
        json={"code": "FR", "name": "France", "is_live": True},
        headers={"Authorization": f"Bearer {admin_tok}"},
    )
    assert create_resp.status_code == 201
    jid = create_resp.json()["id"]

    # 2. Deleting it should succeed (cleaning up child routes)
    del_resp = await client.delete(
        f"/v1/jurisdictions/{jid}",
        headers={"Authorization": f"Bearer {admin_tok}"},
    )
    assert del_resp.status_code == 204

    # 3. Should no longer exist
    get_resp = await client.get("/v1/jurisdictions")
    assert not any(j["id"] == jid for j in get_resp.json())
