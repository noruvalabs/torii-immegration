from httpx import AsyncClient


async def test_register_login_and_me(client: AsyncClient) -> None:
    register = await client.post(
        "/v1/auth/register",
        json={"email": "Applicant@Example.com", "password": "secure-pass"},
    )
    assert register.status_code == 201
    body = register.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["email"] == "applicant@example.com"
    assert body["user"]["role"] == "applicant"
    token = body["access_token"]

    dup = await client.post(
        "/v1/auth/register",
        json={"email": "applicant@example.com", "password": "other-pass"},
    )
    assert dup.status_code == 409

    login = await client.post(
        "/v1/auth/login",
        json={"email": "applicant@example.com", "password": "secure-pass"},
    )
    assert login.status_code == 200
    assert login.json()["access_token"]

    bad_login = await client.post(
        "/v1/auth/login",
        json={"email": "applicant@example.com", "password": "wrong"},
    )
    assert bad_login.status_code == 401

    unauth = await client.get("/v1/auth/me")
    assert unauth.status_code == 401

    me = await client.get("/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "applicant@example.com"


async def test_register_rejects_short_password(client: AsyncClient) -> None:
    resp = await client.post(
        "/v1/auth/register",
        json={"email": "short@example.com", "password": "abc"},
    )
    assert resp.status_code == 422
