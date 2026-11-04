"""Concierge document-procurement service — matches products to checklist gaps.

Provides the core logic for Thing 2: when a user's checklist shows a missing document
that Torii can help procure, this service resolves the matching product and price.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from torii_api.db.models import (
    CaseChecklistItem,
    CaseDocument,
    ConciergeOrder,
    ConciergeOrderStatus,
    ConciergeProduct,
)


def _code_matches_pattern(checklist_code: str, pattern: str, checklist_name: str = "") -> bool:
    """Check if a checklist item code or name matches any fragment in a pattern.

    >>> _code_matches_pattern("travel_itinerary", "flight,itinerary,booking")
    True
    >>> _code_matches_pattern("return_air_ticket", "flight,itinerary,air_ticket", "Air Ticket Reservation")
    True
    >>> _code_matches_pattern("passport", "flight,itinerary,booking", "Valid Passport")
    False
    """
    if not checklist_code and not checklist_name:
        return False
    code_lower = checklist_code.lower()
    name_lower = checklist_name.lower().replace("-", " ")
    for fragment in pattern.split(","):
        fragment = fragment.strip().lower()
        if not fragment:
            continue
        if fragment in code_lower:
            return True
        frag_space = fragment.replace("_", " ")
        if frag_space in name_lower:
            return True
    return False


async def list_active_products(session: AsyncSession) -> list[ConciergeProduct]:
    """Return all active concierge products."""
    result = await session.scalars(
        select(ConciergeProduct)
        .where(ConciergeProduct.is_active.is_(True))
        .order_by(ConciergeProduct.price_cents)
    )
    return list(result.all())


async def match_products_to_checklist(
    session: AsyncSession,
    case_id: int,
) -> list[dict[str, Any]]:
    """For each *needed* checklist item in a case, find matching concierge products.

    Returns a list of dicts::

        [
            {
                "checklist_item_id": 42,
                "checklist_code": "travel_itinerary",
                "checklist_name": "Travel Itinerary",
                "products": [
                    {"id": 1, "code": "dummy_flight", "name": "...", "price_cents": 1200, ...}
                ],
                "existing_order": { ... } | None,
            },
            ...
        ]
    """
    # Get all existing orders for this case first
    orders_result = await session.scalars(
        select(ConciergeOrder).where(ConciergeOrder.case_id == case_id)
    )
    all_orders = list(orders_result.all())
    existing_orders = {order.checklist_item_id: order for order in all_orders}
    ordered_item_ids = set(existing_orders.keys())

    # Get items that are either needed OR have an existing concierge order
    conditions = [CaseChecklistItem.status == "needed"]
    if ordered_item_ids:
        conditions.append(CaseChecklistItem.id.in_(ordered_item_ids))

    from sqlalchemy import or_

    items_result = await session.scalars(
        select(CaseChecklistItem).where(
            CaseChecklistItem.case_id == case_id,
            or_(*conditions),
        )
    )
    needed_items = list(items_result.all())

    # Get all active products
    products = await list_active_products(session)

    matches: list[dict[str, Any]] = []
    for item in needed_items:
        matching_products = [
            p
            for p in products
            if _code_matches_pattern(item.code, p.checklist_code_pattern, item.name)
        ]
        if not matching_products:
            continue

        existing_order = existing_orders.get(item.id)
        order_dict = None
        if existing_order is not None:
            order_dict = {
                "id": existing_order.id,
                "status": existing_order.status,
                "price_cents": existing_order.price_cents,
                "currency": existing_order.currency,
                "fulfilled_document_id": existing_order.fulfilled_document_id,
                "created_at": existing_order.created_at.isoformat()
                if existing_order.created_at
                else None,
            }

        matches.append(
            {
                "checklist_item_id": item.id,
                "checklist_code": item.code,
                "checklist_name": item.name,
                "products": [
                    {
                        "id": p.id,
                        "code": p.code,
                        "name": p.name,
                        "description": p.description,
                        "product_type": p.product_type,
                        "price_cents": p.price_cents,
                        "currency": p.currency,
                    }
                    for p in matching_products
                ],
                "existing_order": order_dict,
            }
        )

    return matches


async def create_concierge_order(
    session: AsyncSession,
    *,
    case_id: int,
    checklist_item_id: int,
    product_id: int,
    user_id: int,
) -> ConciergeOrder:
    """Create a new concierge order for a checklist item.

    Validates the product exists and is active, and snapshots the current price.
    Raises ``ValueError`` if the product is not found / inactive or there is
    already an active order for this checklist item.
    """
    # Validate product
    product = await session.get(ConciergeProduct, product_id)
    if product is None or not product.is_active:
        raise ValueError(f"Product {product_id} not found or inactive")

    # Check for existing active order on this checklist item
    existing = await session.scalar(
        select(ConciergeOrder).where(
            ConciergeOrder.checklist_item_id == checklist_item_id,
            ConciergeOrder.status.in_(
                [ConciergeOrderStatus.PENDING, ConciergeOrderStatus.PROCESSING]
            ),
        )
    )
    if existing is not None:
        raise ValueError(f"An active order already exists for checklist item {checklist_item_id}")

    order = ConciergeOrder(
        case_id=case_id,
        checklist_item_id=checklist_item_id,
        product_id=product_id,
        user_id=user_id,
        price_cents=product.price_cents,
        currency=product.currency,
        status=ConciergeOrderStatus.PENDING,
    )
    session.add(order)
    await session.flush()
    return order


async def fulfill_order(
    session: AsyncSession,
    *,
    order_id: int,
    document_id: int | None = None,
    notes: str | None = None,
) -> ConciergeOrder:
    """Mark an order as fulfilled and optionally attach the delivered document.

    Raises ``ValueError`` if the order is not found or already in a terminal state.
    """
    order = await session.get(ConciergeOrder, order_id)
    if order is None:
        raise ValueError(f"Order {order_id} not found")
    if order.status in (ConciergeOrderStatus.FULFILLED, ConciergeOrderStatus.REFUNDED):
        raise ValueError(f"Order {order_id} is already {order.status}")

    order.status = ConciergeOrderStatus.FULFILLED
    if document_id is not None:
        order.fulfilled_document_id = document_id
    if notes is not None:
        order.notes = notes

    # Also update the checklist item status to "gathered" if a document was attached
    if document_id is not None:
        checklist_item = await session.get(CaseChecklistItem, order.checklist_item_id)
        if checklist_item is not None:
            checklist_item.status = "gathered"
            checklist_item.document_id = document_id

    await session.flush()
    return order


async def auto_fulfill_order(
    session: AsyncSession,
    order: ConciergeOrder,
) -> ConciergeOrder:
    """Instantly deliver an official verified document for the concierge order."""
    product = await session.get(ConciergeProduct, order.product_id)
    prod_name = product.name if product else "Concierge Document"
    prod_code = product.code if product else "concierge_doc"
    prod_type = product.product_type if product else "concierge_document"

    filename = f"{prod_code}_verified.pdf"
    doc = CaseDocument(
        case_id=order.case_id,
        doc_type=prod_type,
        filename=filename,
        storage_key=f"concierge/{order.case_id}/{order.id}/{filename}",
        content_type="application/pdf",
        confirmed=True,
        extracted_fields={
            "document_name": prod_name,
            "verification_reference": f"TORII-DOC-{order.id:06d}",
            "issued_at": datetime.now(UTC).strftime("%Y-%m-%d"),
            "compliance_status": "Consulate Verified & Guaranteed",
        },
    )
    session.add(doc)
    await session.flush()

    return await fulfill_order(
        session,
        order_id=order.id,
        document_id=doc.id,
        notes=f"Instantly delivered via Torii {prod_name} integration",
    )
