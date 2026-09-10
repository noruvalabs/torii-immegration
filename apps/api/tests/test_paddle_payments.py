"""Tests for Paddle payment provider, admin payment controls, and webhook fulfillment."""

from __future__ import annotations

import hashlib
import hmac
import json
import time

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from torii_api.auth.security import hash_password
from torii_api.config import get_settings
from torii_api.services.paddle import verify_webhook_signature


async def _register_and_login(client: AsyncClient, email: str = "applicant@example.com") -> tuple[str, int]:
    """Register and login user, returning token and user_id."""
    await client.post(
        "/v1/auth/register",
        json={"email": email, "password": "secure-password-123"},
    )
    login = await client.post(
        "/v1/auth/login",
        json={"email_or_username": email, "password": "secure-password-123"},
    )
    token = login.json()["access_token"]
    me = await client.get("/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    user_id = me.json()["id"]
    return token, user_id


async def _seed_admin(engine: AsyncEngine) -> str:
    """Seed an admin user and return login token."""
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO users (email, password_hash, role, is_active, email_verified)"
                " VALUES (:email, :pw, 'admin', 1, 1)"
            ),
            {"email": "admin-paddle@example.com", "pw": hash_password("admin-pass-123")},
        )
    return "admin-paddle@example.com"


@pytest.mark.asyncio
async def test_payment_config_endpoint(client: AsyncClient) -> None:
    """Public /config endpoint returns payments enabled state and provider."""
    res = await client.get("/v1/payments/config")
    assert res.status_code == 200
    data = res.json()
    assert data["provider"] == "paddle"
    assert data["payments_enabled"] is True
    assert "environment" in data


@pytest.mark.asyncio
async def test_admin_payment_settings_toggle(client: AsyncClient, engine: AsyncEngine) -> None:
    """Admin can get and toggle payment status via PATCH /v1/admin/settings/payment."""
    await _seed_admin(engine)
    login = await client.post(
        "/v1/auth/login",
        json={"email_or_username": "admin-paddle@example.com", "password": "admin-pass-123"},
    )
    admin_token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Get current settings
    res = await client.get("/v1/admin/settings/payment", headers=headers)
    assert res.status_code == 200
    assert res.json()["payments_enabled"] is True

    # 2. Disable payments
    patch_res = await client.patch(
        "/v1/admin/settings/payment",
        headers=headers,
        json={"payments_enabled": False},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["payments_enabled"] is False

    # 3. Public config now reflects disabled state
    cfg_res = await client.get("/v1/payments/config")
    assert cfg_res.status_code == 200
    assert cfg_res.json()["payments_enabled"] is False

    # 4. Re-enable payments
    patch_back = await client.patch(
        "/v1/admin/settings/payment",
        headers=headers,
        json={"payments_enabled": True},
    )
    assert patch_back.status_code == 200
    assert patch_back.json()["payments_enabled"] is True


@pytest.mark.asyncio
async def test_checkout_blocked_when_payments_disabled(
    client: AsyncClient, engine: AsyncEngine
) -> None:
    """When payments are disabled, /checkout returns 403 Forbidden."""
    await _seed_admin(engine)
    login = await client.post(
        "/v1/auth/login",
        json={"email_or_username": "admin-paddle@example.com", "password": "admin-pass-123"},
    )
    admin_token = login.json()["access_token"]
    user_token, _ = await _register_and_login(client, "buyer1@example.com")

    # Disable payments as admin
    await client.patch(
        "/v1/admin/settings/payment",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"payments_enabled": False},
    )

    # Attempt to create checkout
    res = await client.post(
        "/v1/payments/checkout",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"pack_id": "starter", "currency": "usd"},
    )
    assert res.status_code == 403
    assert "disabled" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_checkout_creation_when_enabled(
    client: AsyncClient, engine: AsyncEngine
) -> None:
    """When enabled, creating a checkout session succeeds and records session in DB."""
    user_token, user_id = await _register_and_login(client, "buyer2@example.com")

    res = await client.post(
        "/v1/payments/checkout",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"pack_id": "standard", "currency": "usd"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["provider"] == "paddle"
    assert data["pack_id"] == "standard"
    assert data["credits"] == 3
    assert data["amount"] == 39.0
    assert data["currency"] == "USD"
    checkout_id = data["checkout_id"]

    # Check checkout status endpoint
    status_res = await client.get(
        f"/v1/payments/checkout/{checkout_id}",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert status_res.status_code == 200
    assert status_res.json()["status"] == "requires_payment"


@pytest.mark.asyncio
async def test_webhook_signature_verification() -> None:
    """HMAC-SHA256 signature verification accepts valid signatures and rejects invalid."""
    secret = "pdl_ntfset_0123456789abcdef"
    body = b'{"event_id": "evt_123", "event_type": "transaction.completed"}'
    ts = int(time.time())

    computed = hmac.new(
        secret.encode("utf-8"),
        f"{ts}:{body.decode('utf-8')}".encode(),
        hashlib.sha256,
    ).hexdigest()
    valid_header = f"ts={ts};h1={computed}"

    assert verify_webhook_signature(body, valid_header, secret) is True
    assert verify_webhook_signature(body, f"ts={ts};h1=wrongsignature", secret) is False
    assert verify_webhook_signature(body, f"ts={ts - 400};h1={computed}", secret) is False


@pytest.mark.asyncio
async def test_webhook_transaction_fulfillment(
    client: AsyncClient, engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
) -> None:
    """transaction.completed webhook event updates checkout and grants credits to user."""
    settings = get_settings()
    secret = "pdl_test_webhook_secret_key"
    monkeypatch.setattr(settings, "paddle_webhook_secret", secret)

    user_token, user_id = await _register_and_login(client, "buyer3@example.com")

    # Initial balance check
    bal_res = await client.get("/v1/credits/balance", headers={"Authorization": f"Bearer {user_token}"})
    initial_balance = bal_res.json()["credit_balance"]

    # Create checkout session
    checkout_res = await client.post(
        "/v1/payments/checkout",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"pack_id": "family", "currency": "usd"},
    )
    checkout_data = checkout_res.json()
    checkout_id = checkout_data["checkout_id"]

    # Simulate Paddle webhook delivery
    event_payload = {
        "event_id": f"evt_{time.time_ns()}",
        "event_type": "transaction.completed",
        "occurred_at": "2026-09-10T12:00:00Z",
        "data": {
            "id": "txn_paddle_test_999",
            "status": "completed",
            "custom_data": {
                "public_checkout_id": checkout_id,
                "pack_id": "family",
                "user_id": str(user_id),
            },
        },
    }
    raw_body = json.dumps(event_payload).encode("utf-8")
    ts = int(time.time())
    sig = hmac.new(
        secret.encode("utf-8"),
        f"{ts}:{raw_body.decode('utf-8')}".encode(),
        hashlib.sha256,
    ).hexdigest()
    sig_header = f"ts={ts};h1={sig}"

    wh_res = await client.post(
        "/v1/payments/webhooks/paddle",
        content=raw_body,
        headers={"Paddle-Signature": sig_header, "Content-Type": "application/json"},
    )
    assert wh_res.status_code == 200
    assert wh_res.json()["status"] == "processed"

    # Verify user credit balance increased by 5 credits (Family pack)
    bal_after_res = await client.get("/v1/credits/balance", headers={"Authorization": f"Bearer {user_token}"})
    assert bal_after_res.json()["credit_balance"] == initial_balance + 5

    # Verify checkout record status is succeeded
    status_res = await client.get(
        f"/v1/payments/checkout/{checkout_id}",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert status_res.json()["status"] == "succeeded"

    # Duplicate webhook delivery should be idempotently ignored without duplicate credit
    wh_dup = await client.post(
        "/v1/payments/webhooks/paddle",
        content=raw_body,
        headers={"Paddle-Signature": sig_header, "Content-Type": "application/json"},
    )
    assert wh_dup.status_code == 200
    assert wh_dup.json()["status"] == "duplicate_ignored"

    # Balance remains initial + 5 (no double credit)
    bal_final = await client.get("/v1/credits/balance", headers={"Authorization": f"Bearer {user_token}"})
    assert bal_final.json()["credit_balance"] == initial_balance + 5
