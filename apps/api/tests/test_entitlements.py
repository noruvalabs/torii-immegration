"""Packet download entitlement gate (US-22.2)."""

from __future__ import annotations

import json

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from torii_api.auth.security import create_access_token
from torii_api.config import get_settings
from torii_api.db.engine import create_session_factory
from torii_api.services.payment import case_has_packet_entitlement


@pytest.mark.asyncio
async def test_case_has_packet_entitlement_false_without_payment(engine: AsyncEngine) -> None:
    session_factory = create_session_factory(engine)
    async with session_factory() as session:
        assert not await case_has_packet_entitlement(session, case_id=1, user_id=1)


@pytest.mark.asyncio
async def test_get_packet_requires_payment(
    client: AsyncClient, engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TORII_REQUIRE_PACKET_ENTITLEMENT", "true")
    get_settings.cache_clear()

    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO users"
                " (email, username, password_hash, role, is_active, email_verified)"
                " VALUES ('paygate@example.com', 'paygate', 'x', 'applicant', 1, 1)"
            )
        )
        uid = (
            await conn.execute(text("SELECT id FROM users WHERE email = 'paygate@example.com'"))
        ).scalar_one()
        await conn.execute(
            text("INSERT INTO jurisdictions (code, name, is_live) VALUES ('JP', 'Japan', 1)")
        )
        jid = (
            await conn.execute(text("SELECT id FROM jurisdictions WHERE code = 'JP'"))
        ).scalar_one()
        await conn.execute(
            text(
                "INSERT INTO cases (reference, jurisdiction_id, user_id, status, locale, "
                "host_locale, review_flags_acknowledged, packet_snapshot, intake_answers)"
                " VALUES ('JP-PAY-1', :jid, :uid, 'packet_ready', 'en', 'ja', 1, :pkt, :ans)"
            ),
            {
                "jid": jid,
                "uid": uid,
                "pkt": json.dumps({"case_reference": "JP-PAY-1", "forms": [], "checklist": []}),
                "ans": json.dumps({}),
            },
        )
        case_id = (
            await conn.execute(text("SELECT id FROM cases WHERE reference = 'JP-PAY-1'"))
        ).scalar_one()

    settings = get_settings()
    token = create_access_token(user_id=int(uid), role="applicant", settings=settings)
    headers = {"Authorization": f"Bearer {token}"}

    locked = await client.get(f"/v1/cases/{case_id}/packet", headers=headers)
    assert locked.status_code == 402

    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO payments (case_id, user_id, transaction_id, visa_fee, service_fee, "
                "total_amount, currency, status)"
                " VALUES (:cid, :uid, 'TXN-TEST-1', 10, 5, 15, 'USD', 'completed')"
            ),
            {"cid": case_id, "uid": uid},
        )

    unlocked = await client.get(f"/v1/cases/{case_id}/packet", headers=headers)
    assert unlocked.status_code == 200
    assert unlocked.json()["case_reference"] == "JP-PAY-1"

    get_settings.cache_clear()
