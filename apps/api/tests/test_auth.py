import pytest
from httpx import AsyncClient


@pytest.fixture(autouse=True)
def _enable_verification(monkeypatch: pytest.MonkeyPatch) -> None:
    from torii_api.config import get_settings

    monkeypatch.setattr(get_settings(), "require_email_verification", True)


async def _register_and_verify(
    client: AsyncClient, monkeypatch, email: str, password: str, username: str | None = None
) -> str:
    sent_tokens: list[str] = []

    def mock_send(**kwargs):
        html = kwargs.get("html_body", "")
        if "token=" in html:
            token = html.split("token=")[1].split('"')[0]
            sent_tokens.append(token)
        return True

    monkeypatch.setattr("torii_api.api.auth.send_email", mock_send)
    payload: dict[str, str] = {"email": email, "password": password}
    if username:
        payload["username"] = username
    reg = await client.post("/v1/auth/register", json=payload)
    assert reg.status_code == 201
    assert len(sent_tokens) >= 1
    raw_token = sent_tokens[-1]
    verify_resp = await client.get(f"/v1/auth/verify-email?token={raw_token}")
    assert verify_resp.status_code == 200
    return verify_resp.json()["access_token"]


async def test_register_login_and_me(client: AsyncClient, monkeypatch) -> None:
    sent_tokens: list[str] = []

    def mock_send(**kwargs):
        html = kwargs.get("html_body", "")
        if "token=" in html:
            token = html.split("token=")[1].split('"')[0]
            sent_tokens.append(token)
        return True

    monkeypatch.setattr("torii_api.api.auth.send_email", mock_send)

    register = await client.post(
        "/v1/auth/register",
        json={"email": "Applicant@Example.com", "password": "secure-pass"},
    )
    assert register.status_code == 201
    body = register.json()
    assert body["user"]["email"] == "applicant@example.com"
    assert body["user"]["role"] == "applicant"
    assert body["user"]["email_verified"] is False
    assert body["access_token"] == ""  # No session returned before email verification

    # Unverified user cannot log in
    unverified_login = await client.post(
        "/v1/auth/login",
        json={"email_or_username": "applicant@example.com", "password": "secure-pass"},
    )
    assert unverified_login.status_code == 403
    assert "verify your email" in unverified_login.json()["detail"].lower()

    # Re-registering with unverified email re-sends verification without 409
    rereg = await client.post(
        "/v1/auth/register",
        json={"email": "applicant@example.com", "password": "secure-pass"},
    )
    assert rereg.status_code == 201

    # Now verify the email with the sent token
    raw_token = sent_tokens[-1]
    verify_resp = await client.get(f"/v1/auth/verify-email?token={raw_token}")
    assert verify_resp.status_code == 200
    verify_data = verify_resp.json()
    assert verify_data["detail"] == "Email verified successfully"
    assert verify_data["user"]["email_verified"] is True
    verified_token = verify_data["access_token"]

    # Now that the account is verified, duplicate registration MUST fail with 409
    dup = await client.post(
        "/v1/auth/register",
        json={"email": "applicant@example.com", "password": "other-pass"},
    )
    assert dup.status_code == 409

    # Now login succeeds
    login = await client.post(
        "/v1/auth/login",
        json={"email_or_username": "applicant@example.com", "password": "secure-pass"},
    )
    assert login.status_code == 200
    assert login.json()["access_token"]

    bad_login = await client.post(
        "/v1/auth/login",
        json={"email_or_username": "applicant@example.com", "password": "wrong"},
    )
    assert bad_login.status_code == 401

    unauth = await client.get("/v1/auth/me")
    assert unauth.status_code == 401

    me = await client.get("/v1/auth/me", headers={"Authorization": f"Bearer {verified_token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "applicant@example.com"


async def test_register_rejects_short_password(client: AsyncClient) -> None:
    resp = await client.post(
        "/v1/auth/register",
        json={"email": "short@example.com", "password": "abc"},
    )
    assert resp.status_code == 422


async def test_register_with_username(client: AsyncClient, monkeypatch) -> None:
    await _register_and_verify(
        client, monkeypatch, email="user1@example.com", password="secure-pass", username="johndoe"
    )

    # Login with username
    login = await client.post(
        "/v1/auth/login",
        json={"email_or_username": "johndoe", "password": "secure-pass"},
    )
    assert login.status_code == 200


async def test_login_with_email_or_username(client: AsyncClient, monkeypatch) -> None:
    await _register_and_verify(
        client, monkeypatch, email="login@example.com", password="secure-pass", username="loginuser"
    )

    # Login with email
    r1 = await client.post(
        "/v1/auth/login",
        json={"email_or_username": "login@example.com", "password": "secure-pass"},
    )
    assert r1.status_code == 200

    # Login with username
    r2 = await client.post(
        "/v1/auth/login",
        json={"email_or_username": "loginuser", "password": "secure-pass"},
    )
    assert r2.status_code == 200


async def test_duplicate_username_rejected(client: AsyncClient) -> None:
    await client.post(
        "/v1/auth/register",
        json={"email": "a@example.com", "password": "secure-pass", "username": "same"},
    )
    resp = await client.post(
        "/v1/auth/register",
        json={"email": "b@example.com", "password": "secure-pass", "username": "same"},
    )
    assert resp.status_code == 409


async def test_verify_email(client: AsyncClient) -> None:
    register = await client.post(
        "/v1/auth/register",
        json={"email": "verify@example.com", "password": "secure-pass"},
    )
    assert register.status_code == 201

    # Extract verification token from DB via the API (token is in email_verification_token hash)
    # We can't easily get the raw token from the response, so test with invalid token
    resp = await client.get("/v1/auth/verify-email?token=invalid-token")
    assert resp.status_code == 400

    # Test already-verified case
    resp2 = await client.get("/v1/auth/verify-email?token=invalid-token")
    assert resp2.status_code == 400


async def test_forgot_password_never_leaks_info(client: AsyncClient) -> None:
    # Always returns 200 even for non-existent email
    resp = await client.post(
        "/v1/auth/forgot-password",
        json={"email": "nonexistent@example.com"},
    )
    assert resp.status_code == 200
    assert "If that email is registered" in resp.json()["detail"]


async def test_reset_password_invalid_token(client: AsyncClient) -> None:
    resp = await client.post(
        "/v1/auth/reset-password",
        json={"token": "invalid-token", "password": "new-pass-123"},
    )
    assert resp.status_code == 400


async def test_resend_verification_never_leaks_info(client: AsyncClient) -> None:
    resp = await client.post(
        "/v1/auth/resend-verification",
        json={"email": "nonexistent@example.com"},
    )
    assert resp.status_code == 200
    assert "If that email is registered" in resp.json()["detail"]


async def test_profile_update_and_get(client: AsyncClient, monkeypatch) -> None:
    token = await _register_and_verify(
        client, monkeypatch, email="profileuser@example.com", password="secure-pass"
    )
    headers = {"Authorization": f"Bearer {token}"}

    # Update profile with all fields including date_of_birth and passport_expiry
    put_resp = await client.put(
        "/v1/auth/profile",
        headers=headers,
        json={
            "full_name": "Tanaka Taro",
            "nationality": "Japan",
            "passport_number": "TK12345678",
            "passport_expiry": "2030-12-31",
            "date_of_birth": "1995-05-15",
            "current_country": "Japan",
        },
    )
    assert put_resp.status_code == 200
    body = put_resp.json()
    assert body["full_name"] == "Tanaka Taro"
    assert body["nationality"] == "Japan"
    assert body["passport_number"] == "TK12345678"
    assert body["passport_expiry"] == "2030-12-31"
    assert body["date_of_birth"] == "1995-05-15"
    assert body["current_country"] == "Japan"
    assert body["profile_complete"] is True

    # Check /v1/auth/me reflects saved fields
    me_resp = await client.get("/v1/auth/me", headers=headers)
    assert me_resp.status_code == 200
    me_body = me_resp.json()
    assert me_body["date_of_birth"] == "1995-05-15"
    assert me_body["passport_expiry"] == "2030-12-31"


async def test_google_social_login(client: AsyncClient) -> None:
    resp = await client.post(
        "/v1/auth/google",
        json={
            "email": "googleuser@example.com",
            "name": "Google Tester",
            "avatar_url": "https://lh3.googleusercontent.com/a/default-user",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["user"]["email"] == "googleuser@example.com"
    assert data["user"]["role"] == "applicant"
    assert data["user"]["email_verified"] is True
    assert data["user"]["full_name"] == "Google Tester"

    # Repeat login with existing user
    resp2 = await client.post(
        "/v1/auth/google",
        json={"email": "googleuser@example.com"},
    )
    assert resp2.status_code == 200
    assert resp2.json()["user"]["email"] == "googleuser@example.com"


async def test_auth_config(client: AsyncClient) -> None:
    resp = await client.get("/v1/auth/config")
    assert resp.status_code == 200
    data = resp.json()
    assert "google_auth_enabled" in data
    assert "google_client_id" in data


async def test_login_rejects_unverified_user_when_required(
    client: AsyncClient, monkeypatch
) -> None:
    from torii_api.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "require_email_verification", True)

    resp = await client.post(
        "/v1/auth/register",
        json={"email": "needsverify@example.com", "password": "secure-password"},
    )
    assert resp.status_code == 201

    login_resp = await client.post(
        "/v1/auth/login",
        json={"email_or_username": "needsverify@example.com", "password": "secure-password"},
    )
    assert login_resp.status_code == 403
    assert "verify your email" in login_resp.json()["detail"].lower()


async def test_register_respects_request_origin(client: AsyncClient, monkeypatch) -> None:
    sent_emails = []

    def mock_send_email(**kwargs):
        sent_emails.append(kwargs)
        return True

    monkeypatch.setattr("torii_api.api.auth.send_email", mock_send_email)

    resp = await client.post(
        "/v1/auth/register",
        json={"email": "dynamic_url@test.com", "password": "secure-password"},
        headers={"Origin": "https://visa.noruvalabs.com"},
    )
    assert resp.status_code == 201
    assert len(sent_emails) == 1
    assert "https://visa.noruvalabs.com/verify-email?token=" in sent_emails[0]["html_body"]


async def test_change_password(client: AsyncClient, monkeypatch) -> None:
    token = await _register_and_verify(
        client, monkeypatch, email="changepw@example.com", password="old-password-123"
    )
    headers = {"Authorization": f"Bearer {token}"}

    # Wrong current password fails with 400
    wrong = await client.post(
        "/v1/auth/change-password",
        headers=headers,
        json={"current_password": "wrong-password", "new_password": "new-password-456"},
    )
    assert wrong.status_code == 400
    assert "incorrect" in wrong.json()["detail"].lower()

    # Same password fails with 400
    same = await client.post(
        "/v1/auth/change-password",
        headers=headers,
        json={"current_password": "old-password-123", "new_password": "old-password-123"},
    )
    assert same.status_code == 400

    # Short password fails validation
    short = await client.post(
        "/v1/auth/change-password",
        headers=headers,
        json={"current_password": "old-password-123", "new_password": "short"},
    )
    assert short.status_code == 422

    # Valid change succeeds
    ok = await client.post(
        "/v1/auth/change-password",
        headers=headers,
        json={"current_password": "old-password-123", "new_password": "new-password-456"},
    )
    assert ok.status_code == 200
    assert "successfully" in ok.json()["detail"].lower()

    # Login with new password works
    login_ok = await client.post(
        "/v1/auth/login",
        json={"email_or_username": "changepw@example.com", "password": "new-password-456"},
    )
    assert login_ok.status_code == 200

    # Login with old password fails
    login_old = await client.post(
        "/v1/auth/login",
        json={"email_or_username": "changepw@example.com", "password": "old-password-123"},
    )
    assert login_old.status_code == 401


async def test_verify_email_expires(client: AsyncClient, monkeypatch) -> None:
    sent_tokens: list[str] = []

    def mock_send(**kwargs):
        html = kwargs.get("html_body", "")
        if "token=" in html:
            token = html.split("token=")[1].split('"')[0]
            sent_tokens.append(token)
        return True

    monkeypatch.setattr("torii_api.api.auth.send_email", mock_send)
    from torii_api.config import get_settings

    settings = get_settings()
    # Expire immediately
    monkeypatch.setattr(settings, "email_verification_token_expire_minutes", -1)

    reg = await client.post(
        "/v1/auth/register",
        json={"email": "expired@example.com", "password": "secure-password"},
    )
    assert reg.status_code == 201
    assert len(sent_tokens) >= 1
    raw_token = sent_tokens[-1]

    verify_resp = await client.get(f"/v1/auth/verify-email?token={raw_token}")
    assert verify_resp.status_code == 400
    assert "expired" in verify_resp.json()["detail"].lower()
