from httpx import AsyncClient


async def test_create_and_list_jurisdictions(client: AsyncClient) -> None:
    # Empty to start.
    assert (await client.get("/v1/jurisdictions")).json() == []

    created = await client.post(
        "/v1/jurisdictions", json={"code": "jp", "name": "Japan", "is_live": True}
    )
    assert created.status_code == 201
    body = created.json()
    assert body["code"] == "JP"  # normalized to upper-case
    assert body["is_live"] is True

    # Duplicate code → 409.
    dup = await client.post("/v1/jurisdictions", json={"code": "JP", "name": "Japan"})
    assert dup.status_code == 409

    # A draft (not live) jurisdiction is hidden by live_only.
    await client.post("/v1/jurisdictions", json={"code": "CA", "name": "Canada", "is_live": False})
    live = await client.get("/v1/jurisdictions", params={"live_only": True})
    assert [j["code"] for j in live.json()] == ["JP"]

    all_ = await client.get("/v1/jurisdictions")
    assert [j["code"] for j in all_.json()] == ["CA", "JP"]
