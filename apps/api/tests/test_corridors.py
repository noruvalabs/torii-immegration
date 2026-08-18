"""Tests for the corridor admissibility check (docs/plan/03_corridor_bd_jp.md)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


async def _register(client: AsyncClient, email: str) -> dict[str, str]:
    resp = await client.post("/v1/auth/register", json={"email": email, "password": "secure-pass"})
    assert resp.status_code == 201, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _outbox_topics(engine: AsyncEngine) -> list[str]:
    async with engine.begin() as conn:
        rows = await conn.execute(text("SELECT topic FROM outbox_events"))
        return [r[0] for r in rows.fetchall()]


BD_JP_TOURIST = {
    "destination_code": "JP",
    "purpose_code": "tourist",
    "action_code": "new_application",
    "nationality": "BD",
    "residence_country": "BD",
}


async def test_check_corridor_enqueues_when_no_cache(
    client: AsyncClient, engine: AsyncEngine
) -> None:
    headers = await _register(client, "corridor1@example.com")

    resp = await client.post("/v1/corridors/check", headers=headers, json=BD_JP_TOURIST)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "queued"
    assert body["items"] == {}

    assert "case.stage_research.queued" in await _outbox_topics(engine)

    poll = await client.get(f"/v1/corridors/{body['id']}", headers=headers)
    assert poll.status_code == 200
    assert poll.json()["status"] == "queued"


async def test_check_corridor_reuses_completed_result_across_applicants(
    client: AsyncClient, engine: AsyncEngine
) -> None:
    headers1 = await _register(client, "corridor2a@example.com")
    first = await client.post("/v1/corridors/check", headers=headers1, json=BD_JP_TOURIST)
    corridor_id = first.json()["id"]

    now = datetime.now(UTC)
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "UPDATE case_stage_research SET status = 'completed', "
                "payload = :p, researched_at = :ra, expires_at = :e WHERE id = :id"
            ),
            {
                "p": '{"admission": {"visa_required": true, "citation": {"authority": "a", "url": "https://x"}}}',
                "ra": now.isoformat(),
                "e": (now + timedelta(days=30)).isoformat(),
                "id": corridor_id,
            },
        )

    outbox_before = len(await _outbox_topics(engine))

    headers2 = await _register(client, "corridor2b@example.com")
    second = await client.post("/v1/corridors/check", headers=headers2, json=BD_JP_TOURIST)
    assert second.status_code == 200
    body = second.json()
    assert body["id"] == corridor_id
    assert body["status"] == "completed"
    assert body["items"]["admission"]["visa_required"] is True

    # No new research job was queued — the cached row was reused.
    assert len(await _outbox_topics(engine)) == outbox_before


async def test_check_corridor_differs_by_nationality(client: AsyncClient) -> None:
    headers = await _register(client, "corridor3@example.com")
    bd = await client.post("/v1/corridors/check", headers=headers, json=BD_JP_TOURIST)
    us_payload = dict(BD_JP_TOURIST, nationality="US", residence_country="US")
    us = await client.post("/v1/corridors/check", headers=headers, json=us_payload)
    assert bd.json()["id"] != us.json()["id"]


async def test_get_corridor_unknown_id_404s(client: AsyncClient) -> None:
    headers = await _register(client, "corridor4@example.com")
    resp = await client.get("/v1/corridors/999999", headers=headers)
    assert resp.status_code == 404


async def test_check_corridor_requires_auth(client: AsyncClient) -> None:
    resp = await client.post("/v1/corridors/check", json=BD_JP_TOURIST)
    assert resp.status_code == 401
