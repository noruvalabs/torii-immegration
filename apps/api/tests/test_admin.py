"""Tests for US-30 — staff roles and scoped access (admin user management)."""

from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


async def _register_and_login(client: AsyncClient, email: str) -> str:
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


async def test_admin_can_list_users(client: AsyncClient, engine: AsyncEngine) -> None:
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


async def test_admin_can_filter_by_role(client: AsyncClient, engine: AsyncEngine) -> None:
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


async def test_admin_can_get_user_by_id(client: AsyncClient, engine: AsyncEngine) -> None:
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


async def test_admin_can_change_user_role(client: AsyncClient, engine: AsyncEngine) -> None:
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


async def test_admin_cannot_change_own_role(client: AsyncClient, engine: AsyncEngine) -> None:
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


async def test_admin_can_deactivate_user(client: AsyncClient, engine: AsyncEngine) -> None:
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


async def test_admin_cannot_deactivate_self(client: AsyncClient, engine: AsyncEngine) -> None:
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


async def test_admin_user_count(client: AsyncClient, engine: AsyncEngine) -> None:
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


async def test_admin_scope_details_get_and_put(client: AsyncClient, engine: AsyncEngine) -> None:
    await _seed_admin(engine)
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO jurisdictions (id, code, name, is_live) VALUES (99, 'TEST', 'Testland', 1)"
            )
        )
        await conn.execute(
            text(
                "INSERT INTO visa_categories (id, jurisdiction_id, code, name, is_enabled) VALUES (991, 99, 'work', 'Work Visa', 1)"
            )
        )
        await conn.execute(
            text(
                "INSERT INTO case_actions (id, jurisdiction_id, code, name, is_enabled) VALUES (992, 99, 'new', 'New Application', 1)"
            )
        )

    login = await client.post(
        "/v1/auth/login",
        json={"email_or_username": "real-admin@example.com", "password": "admin-pass-123"},
    )
    token = login.json()["access_token"]

    # 1. GET scope details
    resp = await client.get(
        "/v1/admin/ops/scope-details?jurisdiction_code=TEST&visa_category_code=work&action_code=new",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["jurisdiction"]["code"] == "TEST"
    assert data["visa_category"]["code"] == "work"
    assert data["case_action"]["code"] == "new"

    # 2. PUT scope details
    put_resp = await client.put(
        "/v1/admin/ops/scope-details",
        json={
            "jurisdiction_code": "TEST",
            "visa_category_code": "work",
            "action_code": "new",
            "category_name": "Updated Work Visa",
            "intake_questions": [
                {"key": "test_q", "prompt": "Test Prompt?", "type": "string", "required": True}
            ],
            "document_requirements": [
                {"code": "doc_1", "name": "Passport Copy", "is_required": True}
            ],
            "form_templates": [
                {
                    "code": "form_01",
                    "version": "1.0",
                    "official_title": "Official Test Form",
                    "field_mappings": [
                        {"form_field": "f1", "answer_key": "test_q", "required": True}
                    ],
                }
            ],
            "eligibility_rules": [
                {"key": "age", "operator": "min", "value": 18, "message": "Must be 18+"}
            ],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert put_resp.status_code == 200
    saved = put_resp.json()
    assert saved["visa_category"]["name"] == "Updated Work Visa"
    assert len(saved["intake_questions"]) == 1
    assert saved["intake_questions"][0]["key"] == "test_q"
    assert len(saved["document_requirements"]) == 1
    assert len(saved["form_templates"]) == 1
    assert len(saved["eligibility_rules"]) == 1


async def test_admin_form_template_pdf_upload_and_download(
    client: AsyncClient, engine: AsyncEngine
) -> None:
    await _seed_admin(engine)
    login = await client.post(
        "/v1/auth/login",
        json={"email_or_username": "real-admin@example.com", "password": "admin-pass-123"},
    )
    token = login.json()["access_token"]

    import io

    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(100, 100, "Official Form Test")
    c.save()
    pdf_bytes = buf.getvalue()

    files = {"file": ("test_form.pdf", pdf_bytes, "application/pdf")}
    try:
        resp = await client.post(
            "/v1/admin/ops/form-templates/TEST_FORM_01/upload-pdf",
            files=files,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        res = resp.json()
        assert res["success"] is True
        assert res["code"] == "TEST_FORM_01"
        assert res["pages"] == 1

        get_resp = await client.get("/v1/admin/ops/form-templates/TEST_FORM_01/pdf")
        assert get_resp.status_code == 200
        assert get_resp.headers["content-type"] == "application/pdf"
        assert len(get_resp.content) > 0
    finally:
        from torii_api.services.official_form_store import cache_dir

        test_pdf = cache_dir() / "test_form_01.pdf"
        if test_pdf.is_file():
            test_pdf.unlink(missing_ok=True)
