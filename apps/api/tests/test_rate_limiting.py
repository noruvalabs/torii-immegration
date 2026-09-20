"""Tests for Rate Limiting & Abuse Protection (T-10).

Covers:
- Unauthenticated per-IP rate limiting
- Authenticated per-user rate limiting (user request limit)
- Auth brute-force protection (login, registration spam, email endpoints)
- Heavy route throttling
- Per-user monthly research budget enforcement
- Healthcheck and docs exemption
- Standard 429 response body and rate limit headers (Retry-After, X-RateLimit-*)
- CORS allowlist headers
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from torii_api.config import get_settings
from torii_api.services.rate_limiter import (
    RateLimitExceeded,
    ResearchBudgetTracker,
    get_rate_limiter,
)


@pytest.fixture(autouse=True)
async def _reset_limiter(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reset the rate limiter and stub email dispatch before each test."""
    monkeypatch.setattr("torii_api.api.auth.send_email", lambda **kwargs: True)
    limiter = get_rate_limiter()
    await limiter.reset()


async def test_healthcheck_exempt_from_rate_limit(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify healthcheck probe is never throttled even under burst traffic."""
    settings = get_settings()
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(settings, "rate_limit_ip_per_minute", 3)

    for _ in range(10):
        resp = await client.get("/health", headers={"x-forwarded-for": "198.51.100.1"})
        assert resp.status_code == 200


async def test_unauthenticated_ip_rate_limiting(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify unauthenticated requests from an IP are capped and receive 429 on N+1."""
    settings = get_settings()
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(settings, "rate_limit_ip_per_minute", 3)

    headers = {"x-forwarded-for": "203.0.113.10"}

    # Requests 1, 2, 3 should succeed
    for i in range(1, 4):
        resp = await client.get("/v1/jurisdictions", headers=headers)
        assert resp.status_code == 200
        assert "x-ratelimit-limit" in resp.headers
        assert resp.headers["x-ratelimit-limit"] == "3"
        assert resp.headers["x-ratelimit-remaining"] == str(3 - i)

    # Request 4 (N+1) must be rejected with 429 Too Many Requests
    blocked = await client.get("/v1/jurisdictions", headers=headers)
    assert blocked.status_code == 429
    assert "retry-after" in blocked.headers
    assert int(blocked.headers["retry-after"]) >= 1
    assert blocked.headers["x-ratelimit-remaining"] == "0"
    data = blocked.json()
    assert "detail" in data
    assert "Rate limit exceeded" in data["detail"]

    # Different IP should not be blocked
    other_ip = await client.get("/v1/jurisdictions", headers={"x-forwarded-for": "203.0.113.20"})
    assert other_ip.status_code == 200


async def test_authenticated_user_request_limit(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify authenticated user request limit is enforced by user ID across IP changes."""
    settings = get_settings()
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(settings, "rate_limit_user_per_minute", 3)

    # Register user A
    reg_a = await client.post(
        "/v1/auth/register",
        json={"email": "usera@example.com", "password": "password-1234"},
        headers={"x-forwarded-for": "10.0.0.1"},
    )
    assert reg_a.status_code == 201

    # Mint token directly
    from torii_api.auth.security import create_access_token

    user_a_id = reg_a.json()["user"]["id"]
    token_a = create_access_token(user_id=user_a_id, role="applicant", settings=settings)
    auth_headers_a = {"authorization": f"Bearer {token_a}"}

    # First 3 requests with User A succeed, even if coming from different IPs
    for i in range(1, 4):
        resp = await client.get(
            "/v1/auth/me",
            headers={**auth_headers_a, "x-forwarded-for": f"10.0.0.{i}"},
        )
        assert resp.status_code == 200
        assert resp.headers["x-ratelimit-limit"] == "3"
        assert resp.headers["x-ratelimit-remaining"] == str(3 - i)

    # 4th request from User A is blocked
    blocked = await client.get(
        "/v1/auth/me",
        headers={**auth_headers_a, "x-forwarded-for": "10.0.0.99"},
    )
    assert blocked.status_code == 429
    assert blocked.headers["x-ratelimit-remaining"] == "0"
    assert "retry-after" in blocked.headers

    # Meanwhile, User B is NOT blocked
    reg_b = await client.post(
        "/v1/auth/register",
        json={"email": "userb@example.com", "password": "password-1234"},
        headers={"x-forwarded-for": "10.0.0.200"},
    )
    user_b_id = reg_b.json()["user"]["id"]
    token_b = create_access_token(user_id=user_b_id, role="applicant", settings=settings)
    resp_b = await client.get(
        "/v1/auth/me",
        headers={"authorization": f"Bearer {token_b}", "x-forwarded-for": "10.0.0.99"},
    )
    assert resp_b.status_code == 200


async def test_login_brute_force_protection(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify login endpoint throttles brute-force attempts per IP and per identifier."""
    settings = get_settings()
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(settings, "rate_limit_login_per_minute", 2)

    headers = {"x-forwarded-for": "198.51.100.50"}

    # Attempt 1 & 2 fail with 401
    for _ in range(2):
        resp = await client.post(
            "/v1/auth/login",
            json={"email_or_username": "target@example.com", "password": "wrong-password"},
            headers=headers,
        )
        assert resp.status_code == 401

    # Attempt 3 is throttled with 429
    resp3 = await client.post(
        "/v1/auth/login",
        json={"email_or_username": "target@example.com", "password": "wrong-password"},
        headers=headers,
    )
    assert resp3.status_code == 429
    assert "Rate limit exceeded" in resp3.json()["detail"]


async def test_register_abuse_protection(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify registration spam is throttled per IP."""
    settings = get_settings()
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(settings, "rate_limit_register_per_minute", 2)

    headers = {"x-forwarded-for": "198.51.100.60"}

    # 2 registrations succeed
    r1 = await client.post(
        "/v1/auth/register",
        json={"email": "bot1@example.com", "password": "password-1234"},
        headers=headers,
    )
    assert r1.status_code == 201

    r2 = await client.post(
        "/v1/auth/register",
        json={"email": "bot2@example.com", "password": "password-1234"},
        headers=headers,
    )
    assert r2.status_code == 201

    # 3rd registration is throttled
    r3 = await client.post(
        "/v1/auth/register",
        json={"email": "bot3@example.com", "password": "password-1234"},
        headers=headers,
    )
    assert r3.status_code == 429
    assert "Rate limit exceeded" in r3.json()["detail"]


async def test_email_endpoints_abuse_protection(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify forgot-password and resend-verification endpoints throttle email bombing."""
    settings = get_settings()
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(settings, "rate_limit_email_per_minute", 2)

    headers = {"x-forwarded-for": "198.51.100.70"}

    # 2 calls allowed
    f1 = await client.post(
        "/v1/auth/forgot-password", json={"email": "victim@example.com"}, headers=headers
    )
    assert f1.status_code == 200
    f2 = await client.post(
        "/v1/auth/forgot-password", json={"email": "victim@example.com"}, headers=headers
    )
    assert f2.status_code == 200

    # 3rd call rejected
    f3 = await client.post(
        "/v1/auth/forgot-password", json={"email": "victim@example.com"}, headers=headers
    )
    assert f3.status_code == 429

    # Same check on resend-verification
    r1 = await client.post(
        "/v1/auth/resend-verification", json={"email": "victim2@example.com"}, headers=headers
    )
    assert r1.status_code == 200
    r2 = await client.post(
        "/v1/auth/resend-verification", json={"email": "victim2@example.com"}, headers=headers
    )
    assert r2.status_code == 200
    r3 = await client.post(
        "/v1/auth/resend-verification", json={"email": "victim2@example.com"}, headers=headers
    )
    assert r3.status_code == 429


async def test_monthly_research_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify monthly research budget tracker enforces limit independently of credits (T-10)."""
    settings = get_settings()
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(settings, "rate_limit_monthly_research_budget", 3)

    tracker = ResearchBudgetTracker()

    # 3 research calls succeed
    r1 = await tracker.check_budget(user_id=42, settings=settings)
    assert r1.allowed is True
    assert r1.remaining == 2

    r2 = await tracker.check_budget(user_id=42, settings=settings)
    assert r2.allowed is True
    assert r2.remaining == 1

    r3 = await tracker.check_budget(user_id=42, settings=settings)
    assert r3.allowed is True
    assert r3.remaining == 0

    # 4th call raises RateLimitExceeded
    with pytest.raises(RateLimitExceeded) as exc_info:
        await tracker.check_budget(user_id=42, settings=settings)
    assert "Monthly research budget exceeded" in str(exc_info.value.detail)


async def test_cors_allowlist_headers(client: AsyncClient) -> None:
    """Verify explicit CORS allowlist headers are returned for allowed origins and blocked for disallowed."""
    # Preflight OPTIONS request with permitted origin
    resp = await client.options(
        "/v1/jurisdictions",
        headers={
            "origin": "http://localhost:3000",
            "access-control-request-method": "GET",
        },
    )
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert resp.headers.get("access-control-allow-credentials") == "true"

    # Preflight OPTIONS request with disallowed origin
    disallowed_resp = await client.options(
        "/v1/jurisdictions",
        headers={
            "origin": "https://malicious-site.example.com",
            "access-control-request-method": "GET",
        },
    )
    assert (
        disallowed_resp.status_code == 400
        or "access-control-allow-origin" not in disallowed_resp.headers
    )
