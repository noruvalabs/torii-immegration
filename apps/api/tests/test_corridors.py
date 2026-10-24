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

    headers2 = await _register(client, "corridor2b@example.com")
    outbox_before = len(await _outbox_topics(engine))

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


async def test_check_corridor_allows_unauthenticated_visitors(client: AsyncClient) -> None:
    resp = await client.post("/v1/corridors/check", json=BD_JP_TOURIST)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("queued", "completed")
    assert "id" in data

    # Anonymous user can also poll
    poll = await client.get(f"/v1/corridors/{data['id']}")
    assert poll.status_code == 200
    assert poll.json()["id"] == data["id"]


async def test_check_corridor_prevents_duplicate_outbox_when_already_queued(
    client: AsyncClient, engine: AsyncEngine
) -> None:
    first = await client.post("/v1/corridors/check", json=BD_JP_TOURIST)
    assert first.status_code == 200
    outbox_count = len(await _outbox_topics(engine))

    # Second concurrent or repeated request
    second = await client.post("/v1/corridors/check", json=BD_JP_TOURIST)
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    # No extra outbox events enqueued for already queued/running job
    assert len(await _outbox_topics(engine)) == outbox_count


async def test_check_corridor_force_refresh(client: AsyncClient, engine: AsyncEngine) -> None:
    first = await client.post("/v1/corridors/check", json=BD_JP_TOURIST)
    corridor_id = first.json()["id"]

    now = datetime.now(UTC)
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "UPDATE case_stage_research SET status = 'completed', "
                "payload = :p, researched_at = :ra, expires_at = :e WHERE id = :id"
            ),
            {
                "p": '{"admission": {"visa_required": true}}',
                "ra": now.isoformat(),
                "e": (now + timedelta(days=30)).isoformat(),
                "id": corridor_id,
            },
        )

    outbox_before = len(await _outbox_topics(engine))
    refresh_resp = await client.post(
        "/v1/corridors/check",
        json=dict(BD_JP_TOURIST, force_refresh=True),
    )
    assert refresh_resp.status_code == 200
    assert refresh_resp.json()["status"] == "queued"
    assert len(await _outbox_topics(engine)) == outbox_before + 1


async def test_check_corridor_returns_observability_fields(
    client: AsyncClient, engine: AsyncEngine
) -> None:
    first = await client.post("/v1/corridors/check", json=BD_JP_TOURIST)
    corridor_id = first.json()["id"]

    now = datetime.now(UTC)
    payload_json = (
        '{"admission": {"visa_required": true, "citation": {"authority": "ISA", "url": "https://www.isa.go.jp/visa"}}, '
        '"_meta": {"review_required": false, "verification_status": "verified", "retrieval_status": "direct_scrape", "source_domains": ["isa.go.jp"], "error_diagnostics": null, "failure_reason": null}}'
    )
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "UPDATE case_stage_research SET status = 'completed', "
                "payload = :p, source_pages = :sp, researched_at = :ra, expires_at = :e WHERE id = :id"
            ),
            {
                "p": payload_json,
                "sp": '[{"url": "https://www.isa.go.jp/visa", "title": "ISA", "retrieval_method": "direct_scrape"}]',
                "ra": now.isoformat(),
                "e": (now + timedelta(days=30)).isoformat(),
                "id": corridor_id,
            },
        )

    resp = await client.get(f"/v1/corridors/{corridor_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert data["review_required"] is False
    assert data["verification_status"] == "verified"
    assert data["retrieval_status"] == "direct_scrape"
    assert "isa.go.jp" in data["source_domains"]
    assert data["error_diagnostics"] is None
    assert data["failure_reason"] is None
    # Ensure internal _meta is not leaked into client items
    assert "_meta" not in data["items"]


async def test_check_corridor_failed_research_observability(
    client: AsyncClient, engine: AsyncEngine
) -> None:
    first = await client.post("/v1/corridors/check", json=BD_JP_TOURIST)
    corridor_id = first.json()["id"]

    async with engine.begin() as conn:
        await conn.execute(
            text(
                "UPDATE case_stage_research SET status = 'failed', "
                "error = 'Official source pages were inaccessible (HTTP 403 / timeout / no readable content)', "
                'payload = \'{"_meta": {"review_required": true, "verification_status": "failed", "retrieval_status": "failed", "source_domains": [], "error_diagnostics": "Official source pages were inaccessible"}}\' '
                "WHERE id = :id"
            ),
            {"id": corridor_id},
        )

    resp = await client.get(f"/v1/corridors/{corridor_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "failed"
    assert data["review_required"] is True
    assert data["verification_status"] == "failed"
    assert data["retrieval_status"] == "failed"
    assert "inaccessible" in (data["error_diagnostics"] or "").lower()


async def test_check_corridor_anonymous_sanitized_diagnostics(
    client: AsyncClient, engine: AsyncEngine
) -> None:
    """Anonymous visitors receive sanitized high-level failure reason without internal diagnostics or secrets."""
    first = await client.post("/v1/corridors/check", json=BD_JP_TOURIST)
    corridor_id = first.json()["id"]

    raw_sensitive_error = (
        "Traceback (most recent call last): File 'server.py', line 42; "
        "SELECT password_hash FROM users; http://internal-127.0.0.1:8001/db_secret"
    )

    async with engine.begin() as conn:
        await conn.execute(
            text(
                "UPDATE case_stage_research SET status = 'failed', "
                "error = :err, "
                'payload = \'{"_meta": {"review_required": true, "verification_status": "failed", "retrieval_status": "failed", "source_domains": []}}\' '
                "WHERE id = :id"
            ),
            {"err": raw_sensitive_error, "id": corridor_id},
        )

    # Anonymous GET (no Authorization header)
    resp = await client.get(f"/v1/corridors/{corridor_id}")
    assert resp.status_code == 200
    data = resp.json()
    error_diag = data["error_diagnostics"] or ""
    # Sensitive info must NOT be exposed to anonymous clients
    assert "Traceback" not in error_diag
    assert "SELECT" not in error_diag
    assert "127.0.0.1" not in error_diag
    assert "db_secret" not in error_diag


async def test_check_corridor_failed_refresh_preserves_cached_record(
    client: AsyncClient, engine: AsyncEngine
) -> None:
    """A failed background refresh must never destroy an existing verified research record."""
    from torii_api.db.engine import create_session_factory
    from torii_api.db.models import OutboxEvent
    from torii_api.worker.scheduler import run_stage_research

    # Seed an existing verified record
    first = await client.post("/v1/corridors/check", json=BD_JP_TOURIST)
    corridor_id = first.json()["id"]
    now = datetime.now(UTC)
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "UPDATE case_stage_research SET status = 'completed', "
                "payload = :p, source_pages = :sp, researched_at = :ra, expires_at = :e WHERE id = :id"
            ),
            {
                "p": '{"admission": {"visa_required": true, "route": "consular_visa", "citation": {"authority": "ISA", "url": "https://www.isa.go.jp/visa"}}}',
                "sp": '[{"url": "https://www.isa.go.jp/visa", "title": "ISA"}]',
                "ra": now.isoformat(),
                "e": (now + timedelta(days=30)).isoformat(),
                "id": corridor_id,
            },
        )

    # Trigger force refresh
    refresh_resp = await client.post(
        "/v1/corridors/check",
        json=dict(BD_JP_TOURIST, force_refresh=True),
    )
    assert refresh_resp.status_code == 200

    # Simulate background worker running and failing (e.g. AI service returned 500 or timeout)
    event = OutboxEvent(
        topic="case.stage_research.queued",
        payload={
            "stage_research_id": corridor_id,
            "stage": "admissibility",
            "destination_code": "JP",
            "purpose_code": "tourist",
            "action_code": "new_application",
            "nationality": "BD",
        },
    )
    session_factory = create_session_factory(engine)
    # run_stage_research will fail to contact real AI service, raising or handling error
    await run_stage_research({"session_factory": session_factory}, event)

    # Check that previous verified data was preserved, not wiped!
    poll = await client.get(f"/v1/corridors/{corridor_id}")
    assert poll.status_code == 200
    data = poll.json()
    assert data["status"] == "completed"
    assert data["items"]["admission"]["visa_required"] is True
    assert data["review_required"] is True
    assert data["verification_status"] == "needs_review"


async def test_expired_corridor_never_returned_as_verified_items(
    client: AsyncClient, engine: AsyncEngine
) -> None:
    """When a corridor check has expired (>30 days), items is returned empty and status is stale."""
    first = await client.post("/v1/corridors/check", json=BD_JP_TOURIST)
    corridor_id = first.json()["id"]

    now = datetime.now(UTC)
    past = now - timedelta(days=35)
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "UPDATE case_stage_research SET status = 'completed', "
                "payload = :p, researched_at = :ra, expires_at = :e WHERE id = :id"
            ),
            {
                "p": '{"admission": {"visa_required": true, "route": "consular_visa", "citation": {"authority": "ISA", "url": "https://www.isa.go.jp/visa"}}}',
                "ra": (past - timedelta(days=1)).isoformat(),
                "e": past.isoformat(),
                "id": corridor_id,
            },
        )

    poll = await client.get(f"/v1/corridors/{corridor_id}")
    assert poll.status_code == 200
    data = poll.json()
    assert data["status"] == "stale"
    assert data["verification_status"] == "unverified"
    assert data["review_required"] is True
    # Crucial regression guard: items must be empty so client never displays expired requirements as current!
    assert data["items"] == {}


async def test_concurrency_guard_superseded_older_job_cannot_overwrite_newer_success(
    client: AsyncClient, engine: AsyncEngine
) -> None:
    """An older slow job that fails cannot downgrade or overwrite a newer completed job."""
    from torii_api.db.engine import create_session_factory
    from torii_api.db.models import OutboxEvent
    from torii_api.worker.scheduler import run_stage_research

    first = await client.post("/v1/corridors/check", json=BD_JP_TOURIST)
    corridor_id = first.json()["id"]

    now = datetime.now(UTC)
    # Simulate a newer Job 2 having already completed with generation 2
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "UPDATE case_stage_research SET status = 'completed', "
                "payload = :p, researched_at = :ra, expires_at = :e WHERE id = :id"
            ),
            {
                "p": '{"_meta": {"generation": 2, "verification_status": "verified", "review_required": false}, "admission": {"visa_required": true, "route": "consular_visa", "citation": {"authority": "ISA", "url": "https://www.isa.go.jp/visa"}}}',
                "ra": now.isoformat(),
                "e": (now + timedelta(days=30)).isoformat(),
                "id": corridor_id,
            },
        )

    # Older Job 1 (generation 1) finishes now with a failure
    older_event = OutboxEvent(
        topic="case.stage_research.queued",
        payload={
            "stage_research_id": corridor_id,
            "job_generation": 1,
            "stage": "admissibility",
            "destination_code": "JP",
            "purpose_code": "tourist",
            "action_code": "new_application",
            "nationality": "BD",
            "queued_at": (now - timedelta(seconds=30)).isoformat(),
        },
    )
    session_factory = create_session_factory(engine)
    # Older job executes and encounters an error (AI service unreachable)
    await run_stage_research({"session_factory": session_factory}, older_event)

    # The newer job's verified result must NOT have been downgraded or overwritten!
    poll = await client.get(f"/v1/corridors/{corridor_id}")
    assert poll.status_code == 200
    data = poll.json()
    assert data["status"] == "completed"
    assert data["verification_status"] == "verified"
    assert data["review_required"] is False
    assert data["items"]["admission"]["visa_required"] is True
