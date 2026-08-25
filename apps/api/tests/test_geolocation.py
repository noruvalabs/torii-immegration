"""Tests for geolocation and destination endpoints."""

from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


async def test_list_application_types_default(client: AsyncClient) -> None:
    resp = await client.get("/v1/geo/application-types")
    assert resp.status_code == 200
    data = resp.json()
    codes = [item["code"] for item in data]
    assert "new" in codes
    assert "renewal" in codes
    assert "change_of_status" in codes


async def test_list_application_types_dynamic_destination(
    client: AsyncClient, engine: AsyncEngine
) -> None:
    async with engine.begin() as conn:
        await conn.execute(
            text("INSERT INTO jurisdictions (code, name, is_live) VALUES ('UK', 'United Kingdom', 1)")
        )
        jid = (
            await conn.execute(text("SELECT id FROM jurisdictions WHERE code = 'UK'"))
        ).scalar_one()
        await conn.execute(
            text(
                "INSERT INTO case_actions (jurisdiction_id, code, name, is_live)"
                f" VALUES ({jid}, 'new', 'New Visa', 1)"
            )
        )
        await conn.execute(
            text(
                "INSERT INTO case_actions (jurisdiction_id, code, name, is_live)"
                f" VALUES ({jid}, 'change_of_status', 'Change of status', 1)"
            )
        )

    resp = await client.get("/v1/geo/application-types", params={"destination": "UK"})
    assert resp.status_code == 200
    data = resp.json()
    codes = [item["code"] for item in data]
    assert "new" in codes
    assert "change_of_status" in codes


async def test_list_visa_types_dynamic_destination(
    client: AsyncClient, engine: AsyncEngine
) -> None:
    async with engine.begin() as conn:
        await conn.execute(
            text("INSERT INTO jurisdictions (code, name, is_live) VALUES ('JP', 'Japan', 1)")
        )
        jid = (
            await conn.execute(text("SELECT id FROM jurisdictions WHERE code = 'JP'"))
        ).scalar_one()
        await conn.execute(
            text(
                "INSERT INTO visa_categories (jurisdiction_id, code, name, is_live)"
                f" VALUES ({jid}, 'work', 'Work Visa', 1)"
            )
        )

    resp = await client.get("/v1/geo/visa-types", params={"destination": "JP"})
    assert resp.status_code == 200
    data = resp.json()
    codes = [item["code"] for item in data]
    assert "work" in codes


async def test_list_application_types_tourist_filters_to_single_entry(
    client: AsyncClient, engine: AsyncEngine
) -> None:
    async with engine.begin() as conn:
        await conn.execute(
            text("INSERT INTO jurisdictions (code, name, is_live) VALUES ('JP', 'Japan', 1)")
        )
        jid = (
            await conn.execute(text("SELECT id FROM jurisdictions WHERE code = 'JP'"))
        ).scalar_one()
        await conn.execute(
            text(
                "INSERT INTO visa_categories (jurisdiction_id, code, name, is_live)"
                f" VALUES ({jid}, 'tourist', 'Tourist', 1)"
            )
        )
        await conn.execute(
            text(
                "INSERT INTO case_actions (jurisdiction_id, code, name, is_live)"
                f" VALUES ({jid}, 'new_application', 'New Visa', 1)"
            )
        )
        await conn.execute(
            text(
                "INSERT INTO case_actions (jurisdiction_id, code, name, is_live)"
                f" VALUES ({jid}, 'renewal', 'Renewal', 1)"
            )
        )
        await conn.execute(
            text(
                "INSERT INTO case_actions (jurisdiction_id, code, name, is_live)"
                f" VALUES ({jid}, 'change_of_status', 'Change of Status', 1)"
            )
        )

    resp = await client.get("/v1/geo/application-types", params={"destination": "JP", "visa_type": "tourist"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["code"] == "new_application"
    assert data[0]["name"] == "Tourist / Entry Visa"

