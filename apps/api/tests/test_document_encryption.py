"""Tests for end-to-end document encryption, access control, and admin inaccessibility."""

from __future__ import annotations

import io
from pathlib import Path

import pymupdf  # type: ignore
import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from torii_api.auth.security import hash_password
from torii_api.services.document_crypto import is_encrypted_document


def _create_sample_pdf(secret_marker: str = "SECRET_PASSPORT_CONTENT") -> bytes:
    """Create a valid PDF containing a specific secret marker text."""
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text(
        (50, 72),
        f"PASSPORT OF JAPAN\n"
        f"Full Name: Kenji Sato\n"
        f"Passport No: TR9988776\n"
        f"Marker: {secret_marker}\n"
        f"Date of Birth: 1990-05-15\n"
        f"Expiry Date: 2032-05-14\n",
    )
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


async def _register_user(client: AsyncClient, email: str, password: str = "Password123!") -> str:
    """Register user and return bearer token."""
    res = await client.post(
        "/v1/auth/register",
        json={"email": email, "password": password},
    )
    assert res.status_code == 201
    return res.json()["access_token"]


async def _create_admin(engine: AsyncEngine, email: str = "admin_sec@example.com") -> None:
    """Insert an admin user into the DB."""
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO users (email, password_hash, role, is_active, email_verified)"
                " VALUES (:email, :pw, 'admin', 1, 1)"
            ),
            {"email": email, "pw": hash_password("AdminPass123!")},
        )


@pytest.mark.asyncio
async def test_uploaded_document_encrypted_at_rest(client: AsyncClient) -> None:
    """Documents uploaded to the wallet must be stored encrypted on disk."""
    token = await _register_user(client, "alice@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    secret_marker = "TOP_SECRET_PASSPORT_ALICE_XYZ"
    pdf_data = _create_sample_pdf(secret_marker)

    upload_res = await client.post(
        "/v1/wallet/upload",
        headers=headers,
        params={"doc_type": "passport", "name": "Alice Passport"},
        files={"file": ("alice_passport.pdf", io.BytesIO(pdf_data), "application/pdf")},
    )
    assert upload_res.status_code == 201
    doc_json = upload_res.json()
    storage_key = doc_json["storage_key"]

    # Verify physical file on disk
    disk_path = Path("data/wallet_storage") / storage_key
    assert disk_path.exists()

    disk_bytes = disk_path.read_bytes()
    assert is_encrypted_document(disk_bytes)
    # The confidential marker must NOT appear in the encrypted ciphertext on disk
    assert secret_marker.encode() not in disk_bytes


@pytest.mark.asyncio
async def test_owner_can_access_and_decrypt_document(client: AsyncClient) -> None:
    """Authorized owner can seamlessly download, preview, and view their decrypted document."""
    token = await _register_user(client, "bob@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    secret_marker = "BOB_CONFIDENTIAL_12345"
    pdf_data = _create_sample_pdf(secret_marker)

    upload_res = await client.post(
        "/v1/wallet/upload",
        headers=headers,
        params={"doc_type": "passport", "name": "Bob Passport"},
        files={"file": ("bob_passport.pdf", io.BytesIO(pdf_data), "application/pdf")},
    )
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["id"]

    # 1. Download file
    file_res = await client.get(f"/v1/wallet/{doc_id}/file", headers=headers)
    assert file_res.status_code == 200
    assert file_res.content == pdf_data
    from torii_api.services.ocr_extractor import extract_text_with_pymupdf

    assert secret_marker in extract_text_with_pymupdf(file_res.content)

    # 2. Rendered page preview
    page_res = await client.get(f"/v1/wallet/{doc_id}/page/1", headers=headers)
    assert page_res.status_code == 200
    assert page_res.headers["content-type"] == "image/png"
    assert len(page_res.content) > 0

    # 3. HTML view
    view_res = await client.get(f"/v1/wallet/{doc_id}/view", headers=headers)
    assert view_res.status_code == 200
    assert "Bob Passport" in view_res.text and "toolbar" in view_res.text


@pytest.mark.asyncio
async def test_admins_strictly_forbidden_from_document_contents(
    client: AsyncClient, engine: AsyncEngine
) -> None:
    """Admin accounts must NOT be able to view or access users' document contents."""
    # Register applicant and upload document
    user_token = await _register_user(client, "charlie@example.com")
    upload_res = await client.post(
        "/v1/wallet/upload",
        headers={"Authorization": f"Bearer {user_token}"},
        params={"doc_type": "passport", "name": "Charlie Passport"},
        files={
            "file": (
                "charlie_passport.pdf",
                io.BytesIO(_create_sample_pdf("CHARLIE_SECRET")),
                "application/pdf",
            )
        },
    )
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["id"]

    # Create and login as admin
    admin_email = "admin_shield@example.com"
    await _create_admin(engine, email=admin_email)
    admin_login = await client.post(
        "/v1/auth/login",
        json={"email_or_username": admin_email, "password": "AdminPass123!"},
    )
    assert admin_login.status_code == 200
    admin_token = admin_login.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Admin attempts to download user's file -> 403 Forbidden
    resp_file = await client.get(f"/v1/wallet/{doc_id}/file", headers=admin_headers)
    assert resp_file.status_code == 403
    assert "Admins are strictly prohibited" in resp_file.json()["detail"]

    # Admin attempts to preview page -> 403 Forbidden
    resp_page = await client.get(f"/v1/wallet/{doc_id}/page/1", headers=admin_headers)
    assert resp_page.status_code == 403
    assert "Admins are strictly prohibited" in resp_page.json()["detail"]

    # Admin attempts HTML view -> 403 Forbidden
    resp_view = await client.get(f"/v1/wallet/{doc_id}/view", headers=admin_headers)
    assert resp_view.status_code == 403
    assert "Admins are strictly prohibited" in resp_view.json()["detail"]


@pytest.mark.asyncio
async def test_cross_user_isolation(client: AsyncClient) -> None:
    """User B cannot access or download User A's document."""
    user_a_token = await _register_user(client, "user_a@example.com")
    upload_res = await client.post(
        "/v1/wallet/upload",
        headers={"Authorization": f"Bearer {user_a_token}"},
        params={"doc_type": "passport", "name": "User A Passport"},
        files={
            "file": (
                "passport.pdf",
                io.BytesIO(_create_sample_pdf("USER_A_PRIVATE_DATA")),
                "application/pdf",
            )
        },
    )
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["id"]

    user_b_token = await _register_user(client, "user_b@example.com")
    user_b_headers = {"Authorization": f"Bearer {user_b_token}"}

    resp = await client.get(f"/v1/wallet/{doc_id}/file", headers=user_b_headers)
    assert resp.status_code == 404
