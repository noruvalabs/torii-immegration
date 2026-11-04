"""Tests for Concierge service — product matching, ordering, fulfillment."""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine

from torii_api.db.engine import create_session_factory
from torii_api.services.concierge import _code_matches_pattern


# ---------------------------------------------------------------------------
# Unit tests for code matching
# ---------------------------------------------------------------------------


class TestCodeMatching:
    """Test the _code_matches_pattern helper."""

    def test_exact_fragment_match(self) -> None:
        assert _code_matches_pattern("flight", "flight,itinerary,booking")

    def test_substring_match(self) -> None:
        assert _code_matches_pattern("travel_itinerary", "flight,itinerary,booking")

    def test_no_match(self) -> None:
        assert not _code_matches_pattern("passport", "flight,itinerary,booking")

    def test_case_insensitive(self) -> None:
        assert _code_matches_pattern("TRAVEL_INSURANCE", "insurance,medical_insurance")

    def test_hotel_match(self) -> None:
        assert _code_matches_pattern("hotel_booking", "hotel,accommodation,hotel_booking")

    def test_invitation_match(self) -> None:
        assert _code_matches_pattern("invitation_letter", "invitation,host_letter")

    def test_doctor_match(self) -> None:
        assert _code_matches_pattern("medical_referral", "referral,doctor,medical_referral")

    def test_empty_pattern(self) -> None:
        assert not _code_matches_pattern("anything", "")

    def test_empty_code(self) -> None:
        assert not _code_matches_pattern("", "flight,itinerary")


# ---------------------------------------------------------------------------
# Integration tests (DB-backed via session)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def session(engine: AsyncEngine):
    """Provide an async session for service-level tests."""
    factory = create_session_factory(engine)
    async with factory() as sess:
        yield sess


@pytest.fixture()
def _seed_products():
    """Return raw product dicts for seeding."""
    return [
        {
            "code": "dummy_flight",
            "name": "Dummy Flight Reservation",
            "description": "PDF flight itinerary",
            "product_type": "dummy_flight",
            "price_cents": 1200,
            "checklist_code_pattern": "flight,itinerary,booking,travel_itinerary,flight_reservation",
        },
        {
            "code": "hotel_reservation",
            "name": "Hotel Confirmation Letter",
            "description": "Free hotel confirmation",
            "product_type": "hotel_reservation",
            "price_cents": 0,
            "checklist_code_pattern": "hotel,accommodation,hotel_booking,hotel_reservation",
        },
    ]


@pytest_asyncio.fixture
async def seeded_concierge(session, _seed_products):
    """Seed concierge products and a case with checklist items."""
    from torii_api.auth.security import hash_password
    from torii_api.db.models import (
        Case,
        CaseChecklistItem,
        ConciergeProduct,
        Jurisdiction,
        User,
        UserRole,
    )

    jurisdiction = Jurisdiction(code="JP", name="Japan", is_live=True)
    session.add(jurisdiction)
    await session.flush()

    user = User(
        email="concierge-test@example.com",
        username="concierge_test",
        password_hash=hash_password("test-pass"),
        role=UserRole.APPLICANT,
        is_active=True,
        email_verified=True,
    )
    session.add(user)
    await session.flush()

    case = Case(
        user_id=user.id,
        jurisdiction_id=jurisdiction.id,
        status="documents",
        reference="TEST-CONCIERGE-001",
        locale="en",
        host_locale="en",
    )
    session.add(case)
    await session.flush()

    items = [
        CaseChecklistItem(
            case_id=case.id,
            code="travel_itinerary",
            name="Travel Itinerary",
            how_to_obtain="Book a flight",
            why_required="Shows travel plans",
            status="needed",
        ),
        CaseChecklistItem(
            case_id=case.id,
            code="hotel_booking",
            name="Hotel Booking",
            how_to_obtain="Book a hotel",
            why_required="Shows accommodation",
            status="needed",
        ),
        CaseChecklistItem(
            case_id=case.id,
            code="passport",
            name="Valid Passport",
            how_to_obtain="From your government",
            why_required="Primary ID",
            status="gathered",
        ),
    ]
    for it in items:
        session.add(it)
    await session.flush()

    products = [ConciergeProduct(**p) for p in _seed_products]
    for p in products:
        session.add(p)
    await session.flush()

    await session.commit()
    return {"user": user, "case": case, "items": items, "products": products}


@pytest.mark.asyncio
async def test_match_products_to_checklist(session, seeded_concierge):
    """Products should match only *needed* checklist items."""
    from torii_api.services.concierge import match_products_to_checklist

    case = seeded_concierge["case"]
    matches = await match_products_to_checklist(session, case.id)

    assert len(matches) == 2
    codes = {m["checklist_code"] for m in matches}
    assert "travel_itinerary" in codes
    assert "hotel_booking" in codes
    assert "passport" not in codes


@pytest.mark.asyncio
async def test_create_order(session, seeded_concierge):
    """Should create an order with snapshotted price."""
    from torii_api.services.concierge import create_concierge_order

    data = seeded_concierge
    order = await create_concierge_order(
        session,
        case_id=data["case"].id,
        checklist_item_id=data["items"][0].id,
        product_id=data["products"][0].id,
        user_id=data["user"].id,
    )
    assert order.price_cents == 1200
    assert order.status == "pending"
    assert order.case_id == data["case"].id


@pytest.mark.asyncio
async def test_duplicate_order_rejected(session, seeded_concierge):
    """Cannot create two active orders for the same checklist item."""
    from torii_api.services.concierge import create_concierge_order

    data = seeded_concierge
    await create_concierge_order(
        session,
        case_id=data["case"].id,
        checklist_item_id=data["items"][0].id,
        product_id=data["products"][0].id,
        user_id=data["user"].id,
    )
    await session.flush()

    with pytest.raises(ValueError, match="active order already exists"):
        await create_concierge_order(
            session,
            case_id=data["case"].id,
            checklist_item_id=data["items"][0].id,
            product_id=data["products"][0].id,
            user_id=data["user"].id,
        )


@pytest.mark.asyncio
async def test_fulfill_order(session, seeded_concierge):
    """Fulfilling an order marks it fulfilled and updates checklist item."""
    from torii_api.db.models import CaseDocument
    from torii_api.services.concierge import create_concierge_order, fulfill_order

    data = seeded_concierge

    doc = CaseDocument(
        case_id=data["case"].id,
        doc_type="flight_itinerary",
        filename="itinerary.pdf",
        storage_key="uploads/itinerary.pdf",
        content_type="application/pdf",
    )
    session.add(doc)
    await session.flush()

    order = await create_concierge_order(
        session,
        case_id=data["case"].id,
        checklist_item_id=data["items"][0].id,
        product_id=data["products"][0].id,
        user_id=data["user"].id,
    )
    await session.flush()

    fulfilled = await fulfill_order(
        session,
        order_id=order.id,
        document_id=doc.id,
        notes="Delivered via email",
    )
    assert fulfilled.status == "fulfilled"
    assert fulfilled.fulfilled_document_id == doc.id

    # Checklist item should now be gathered
    await session.refresh(data["items"][0])
    assert data["items"][0].status == "gathered"


@pytest.mark.asyncio
async def test_free_product_order(session, seeded_concierge):
    """Hotel reservation (free) should create order with price_cents=0."""
    from torii_api.services.concierge import create_concierge_order

    data = seeded_concierge
    order = await create_concierge_order(
        session,
        case_id=data["case"].id,
        checklist_item_id=data["items"][1].id,
        product_id=data["products"][1].id,
        user_id=data["user"].id,
    )
    assert order.price_cents == 0
    assert order.status == "pending"
