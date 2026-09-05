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
            text(
                "INSERT INTO jurisdictions (code, name, is_live) VALUES ('UK', 'United Kingdom', 1)"
            )
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
        # A route on its own is not an offer: a case needs a procedure too, and one
        # sourced the same way the route is. See services/scope_availability.
        await conn.execute(
            text(
                "INSERT INTO case_actions (jurisdiction_id, code, name, is_live)"
                f" VALUES ({jid}, 'new', 'New Visa', 1)"
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

    resp = await client.get(
        "/v1/geo/application-types", params={"destination": "JP", "visa_type": "tourist"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["code"] == "new_application"
    assert data[0]["name"] == "Tourist / Entry Visa"


# ── Which destinations are offered ─────────────────────────────────────────────────
# US is parked (docs/jurisdictions/us/_jurisdiction.yml). Offering a destination whose
# content packs are not live sends the applicant to an empty scope.


def test_only_japan_and_the_uk_are_offered_as_destinations() -> None:
    from torii_api.services.geolocation import get_supported_destinations

    codes = {destination["code"] for destination in get_supported_destinations()}
    assert codes == {"JP", "UK", "GB"}
    assert "US" not in codes


def test_a_parked_destination_is_excluded_from_the_picker() -> None:
    from torii_api.services.geolocation import get_destinations_excluding

    for current in ("JP", "US", "BD"):
        codes = {destination["code"] for destination in get_destinations_excluding(current)}
        assert "US" not in codes
        assert current not in codes


def test_a_parked_country_can_still_be_labelled() -> None:
    """Parking US as a destination must not break naming it as where someone lives."""
    from torii_api.services.geolocation import resolve_country_meta

    meta = resolve_country_meta("US")
    assert meta["name"] == "United States"
    assert meta["currency"] == "USD"


def test_offered_destinations_all_have_live_content() -> None:
    """An offered destination without a live pack is a dead end for the applicant."""
    from torii_api.services.content_packs import list_jurisdiction_metas
    from torii_api.services.geolocation import get_supported_destinations

    live = {meta.code.upper() for meta in list_jurisdiction_metas() if meta.is_live}
    for destination in get_supported_destinations():
        code = "UK" if destination["code"] == "GB" else destination["code"]
        assert code in live, f"{code} is offered but has no live content pack"
