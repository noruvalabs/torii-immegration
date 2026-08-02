"""Payment endpoints for visa application fees."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from torii_api.auth.deps import CurrentUserDep
from torii_api.db.session import get_session
from torii_api.services.payment import (
    create_payment,
    get_payment_by_case,
    get_user_payments,
    process_mock_payment,
    refund_payment,
)

router = APIRouter(prefix="/v1/payments", tags=["payments"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


# ── Response schemas ──────────────────────────────────────────────────────────


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    case_id: int
    transaction_id: str
    visa_fee: float
    service_fee: float
    total_amount: float
    currency: str
    status: str
    payment_method: str | None = None
    paid_at: str | None = None
    created_at: str | None = None


class PaymentCreateIn(BaseModel):
    case_id: int
    destination_code: str
    visa_type: str


class PaymentProcessIn(BaseModel):
    payment_method: str = "card"


class PaymentListOut(BaseModel):
    payments: list[PaymentOut]
    total: int


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post("/", response_model=PaymentOut, status_code=status.HTTP_201_CREATED)
async def create_new_payment(
    current_user: CurrentUserDep,
    session: SessionDep,
    body: PaymentCreateIn,
) -> PaymentOut:
    """Create a new payment record for a case."""
    from sqlalchemy import select

    from torii_api.db.models import Case

    # Verify case belongs to user
    result = await session.execute(
        select(Case).where(
            Case.id == body.case_id,
            Case.user_id == current_user.id,
        )
    )
    case = result.scalar_one_or_none()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    payment = await create_payment(
        db=session,
        case_id=body.case_id,
        user_id=current_user.id,
        destination_code=body.destination_code,
        visa_type=body.visa_type,
    )

    return PaymentOut.model_validate(payment)


@router.get("/", response_model=PaymentListOut)
async def list_payments(
    current_user: CurrentUserDep,
    session: SessionDep,
) -> PaymentListOut:
    """List all payments for the current user."""
    payments = await get_user_payments(db=session, user_id=current_user.id)
    return PaymentListOut(
        payments=[PaymentOut.model_validate(p) for p in payments],
        total=len(payments),
    )


@router.get("/case/{case_id}", response_model=PaymentOut)
async def get_case_payment(
    current_user: CurrentUserDep,
    session: SessionDep,
    case_id: int,
) -> PaymentOut:
    """Get payment for a specific case."""
    payment = await get_payment_by_case(
        db=session, case_id=case_id, user_id=current_user.id
    )

    if not payment:
        raise HTTPException(status_code=404, detail="No payment found for this case")

    return PaymentOut.model_validate(payment)


@router.post("/{payment_id}/process", response_model=PaymentOut)
async def process_payment(
    current_user: CurrentUserDep,
    session: SessionDep,
    payment_id: int,
    body: PaymentProcessIn | None = None,
) -> PaymentOut:
    """Process a mock payment (always succeeds)."""
    try:
        payment = await process_mock_payment(
            db=session,
            payment_id=payment_id,
            user_id=current_user.id,
            payment_method=body.payment_method if body else "card",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return PaymentOut.model_validate(payment)


@router.post("/{payment_id}/refund", response_model=PaymentOut)
async def refund_existing_payment(
    current_user: CurrentUserDep,
    session: SessionDep,
    payment_id: int,
) -> PaymentOut:
    """Refund a completed payment."""
    try:
        payment = await refund_payment(
            db=session,
            payment_id=payment_id,
            user_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return PaymentOut.model_validate(payment)


@router.get("/fees/{destination_code}")
async def get_visa_fees(
    destination_code: str,
) -> dict:
    """Get visa fees for a destination country."""
    from torii_api.services.payment import get_currency, get_visa_fee

    visa_types = ["tourist", "student", "work"]
    fees = {}
    for vt in visa_types:
        fees[vt] = {
            "visa_fee": get_visa_fee(destination_code, vt),
            "service_fee": 49.99,
            "total": get_visa_fee(destination_code, vt) + 49.99,
        }

    return {
        "destination_code": destination_code,
        "currency": get_currency(destination_code),
        "fees": fees,
    }
