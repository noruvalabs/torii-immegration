"""Concierge API — purchasable document-procurement services (Thing 2).

Endpoints:
    GET  /v1/concierge/products             — list active products
    GET  /v1/cases/{case_id}/concierge       — available products for missing checklist items
    POST /v1/cases/{case_id}/concierge/order — place an order
    GET  /v1/cases/{case_id}/concierge/orders — list orders for a case
    POST /v1/concierge/orders/{order_id}/fulfill — admin: mark fulfilled
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from torii_api.auth.deps import CurrentUserDep
from torii_api.db.models import Case, ConciergeOrder, UserRole
from torii_api.db.session import get_session
from torii_api.services.concierge import (
    auto_fulfill_order,
    create_concierge_order,
    fulfill_order,
    list_active_products,
    match_products_to_checklist,
)

router = APIRouter(tags=["concierge"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    description: str
    product_type: str
    price_cents: int
    currency: str
    checklist_code_pattern: str
    is_active: bool


class MatchedProductOut(BaseModel):
    id: int
    code: str
    name: str
    description: str
    product_type: str
    price_cents: int
    currency: str


class ExistingOrderOut(BaseModel):
    id: int
    status: str
    price_cents: int
    currency: str
    fulfilled_document_id: int | None = None
    created_at: str | None = None


class ConciergeMatchOut(BaseModel):
    checklist_item_id: int
    checklist_code: str
    checklist_name: str
    products: list[MatchedProductOut]
    existing_order: ExistingOrderOut | None = None


class OrderCreateIn(BaseModel):
    checklist_item_id: int
    product_id: int


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    case_id: int
    checklist_item_id: int
    product_id: int
    user_id: int
    price_cents: int
    currency: str
    status: str
    fulfilled_document_id: int | None = None
    notes: str | None = None


class FulfillIn(BaseModel):
    document_id: int | None = None
    notes: str | None = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/v1/concierge/products", response_model=list[ProductOut])
async def get_products(session: SessionDep, _user: CurrentUserDep) -> list[ProductOut]:
    """List all active concierge products."""
    products = await list_active_products(session)
    return [ProductOut.model_validate(p) for p in products]


@router.get(
    "/v1/cases/{case_id}/concierge",
    response_model=list[ConciergeMatchOut],
)
async def get_available_concierge(
    case_id: int,
    session: SessionDep,
    user: CurrentUserDep,
) -> list[ConciergeMatchOut]:
    """For each missing checklist item in a case, return matching concierge products."""
    case = await session.get(Case, case_id)
    if case is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Case not found")
    if case.user_id != user.id and user.role not in (UserRole.ADMIN, UserRole.OPS):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your case")

    # Auto-fulfill any pending orders (Things 2A, 2B, 2D instant delivery)
    pending_orders = (
        await session.scalars(
            select(ConciergeOrder).where(
                ConciergeOrder.case_id == case_id,
                ConciergeOrder.status == "pending",
            )
        )
    ).all()
    for po in pending_orders:
        await auto_fulfill_order(session, po)
    if pending_orders:
        await session.commit()

    matches = await match_products_to_checklist(session, case_id)
    return [ConciergeMatchOut(**m) for m in matches]


@router.post(
    "/v1/cases/{case_id}/concierge/order",
    response_model=OrderOut,
    status_code=status.HTTP_201_CREATED,
)
async def place_order(
    case_id: int,
    body: OrderCreateIn,
    session: SessionDep,
    user: CurrentUserDep,
) -> OrderOut:
    """Place an order for a concierge product on a checklist item."""
    case = await session.get(Case, case_id)
    if case is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Case not found")
    if case.user_id != user.id and user.role not in (UserRole.ADMIN, UserRole.OPS):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your case")

    try:
        order = await create_concierge_order(
            session,
            case_id=case_id,
            checklist_item_id=body.checklist_item_id,
            product_id=body.product_id,
            user_id=user.id,
        )
        # Instantly deliver document as per Roadmap 2A/2B/2D
        order = await auto_fulfill_order(session, order)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    await session.commit()
    return OrderOut.model_validate(order)


@router.get(
    "/v1/cases/{case_id}/concierge/orders",
    response_model=list[OrderOut],
)
async def list_orders(
    case_id: int,
    session: SessionDep,
    user: CurrentUserDep,
) -> list[OrderOut]:
    """List concierge orders for a case."""
    case = await session.get(Case, case_id)
    if case is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Case not found")
    if case.user_id != user.id and user.role not in (UserRole.ADMIN, UserRole.OPS):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your case")

    result = await session.scalars(
        select(ConciergeOrder)
        .where(ConciergeOrder.case_id == case_id)
        .order_by(ConciergeOrder.created_at.desc())
    )
    return [OrderOut.model_validate(o) for o in result.all()]


@router.post(
    "/v1/concierge/orders/{order_id}/fulfill",
    response_model=OrderOut,
)
async def fulfill(
    order_id: int,
    body: FulfillIn,
    session: SessionDep,
    user: CurrentUserDep,
) -> OrderOut:
    """Admin/ops: mark a concierge order as fulfilled."""
    if user.role not in (UserRole.ADMIN, UserRole.OPS):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin or ops only")

    try:
        order = await fulfill_order(
            session,
            order_id=order_id,
            document_id=body.document_id,
            notes=body.notes,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    await session.commit()
    return OrderOut.model_validate(order)
