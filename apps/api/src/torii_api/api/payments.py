"""Payment endpoints for visa application fees."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from torii_api.api.credits import CREDIT_PACKS
from torii_api.auth.deps import CurrentUserDep
from torii_api.config import get_settings
from torii_api.db.models import PaymentCheckout, User
from torii_api.db.session import get_session
from torii_api.services.paddle import create_checkout_session, handle_paddle_webhook_event
from torii_api.services.payment import (
    create_payment,
    get_payment_by_case,
    get_user_payments,
    process_mock_payment,
    refund_payment,
)
from torii_api.services.system_settings import is_payments_enabled

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
    payment = await get_payment_by_case(db=session, case_id=case_id, user_id=current_user.id)

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


# ── Paddle Payment Schemas ───────────────────────────────────────────────────


class PaymentConfigOut(BaseModel):
    payments_enabled: bool
    provider: str = "paddle"
    environment: str
    client_token: str
    default_checkout_url: str = ""


class CheckoutCreateIn(BaseModel):
    pack_id: Literal["starter", "standard", "family"]
    currency: Literal["usd", "jpy"] = "usd"


class CheckoutCreateOut(BaseModel):
    checkout_id: str
    provider: str
    provider_session_id: str | None
    checkout_url: str | None
    amount: float
    currency: str
    credits: int
    pack_id: str


class CheckoutStatusOut(BaseModel):
    checkout_id: str
    status: str
    credits: int
    amount: float
    currency: str
    completed_at: str | None = None


# ── Paddle Endpoints ──────────────────────────────────────────────────────────


@router.get("/config", response_model=PaymentConfigOut)
async def get_payment_configuration(
    session: SessionDep,
) -> PaymentConfigOut:
    """Return platform payment configuration and enabled/disabled state."""
    settings = get_settings()
    enabled = await is_payments_enabled(session)
    return PaymentConfigOut(
        payments_enabled=enabled,
        provider="paddle",
        environment=settings.paddle_env,
        client_token=settings.paddle_client_token,
        default_checkout_url=settings.paddle_default_checkout_url,
    )


@router.post("/checkout", response_model=CheckoutCreateOut, status_code=status.HTTP_201_CREATED)
async def create_paddle_checkout(
    current_user: CurrentUserDep,
    session: SessionDep,
    body: CheckoutCreateIn,
) -> CheckoutCreateOut:
    """Create a Paddle checkout session for purchasing a credit pack."""
    enabled = await is_payments_enabled(session)
    if not enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Online payments and credit purchases are temporarily disabled by the administrator.",
        )

    pack = next((p for p in CREDIT_PACKS if p["id"] == body.pack_id), None)
    if not pack:
        raise HTTPException(status_code=400, detail="Invalid credit pack ID")

    user = await session.get(User, current_user.id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    checkout = await create_checkout_session(
        session=session,
        user=user,
        pack=pack,
        currency=body.currency,
    )

    return CheckoutCreateOut(
        checkout_id=checkout.public_id,
        provider=checkout.provider,
        provider_session_id=checkout.provider_session_id,
        checkout_url=checkout.checkout_url,
        amount=checkout.amount,
        currency=checkout.currency,
        credits=checkout.credits,
        pack_id=checkout.pack_id,
    )


@router.get("/checkout/{checkout_id}", response_model=CheckoutStatusOut)
async def get_checkout_status(
    current_user: CurrentUserDep,
    session: SessionDep,
    checkout_id: str,
) -> CheckoutStatusOut:
    """Check payment and fulfillment status for a checkout session."""
    stmt = select(PaymentCheckout).where(
        PaymentCheckout.public_id == checkout_id,
        PaymentCheckout.user_id == current_user.id,
    )
    res = await session.execute(stmt)
    checkout = res.scalar_one_or_none()
    if not checkout:
        raise HTTPException(status_code=404, detail="Checkout session not found")

    return CheckoutStatusOut(
        checkout_id=checkout.public_id,
        status=checkout.status,
        credits=checkout.credits,
        amount=checkout.amount,
        currency=checkout.currency,
        completed_at=checkout.completed_at.isoformat() if checkout.completed_at else None,
    )


@router.post("/webhooks/paddle")
async def paddle_webhook(
    request: Request,
    session: SessionDep,
    paddle_signature: Annotated[str | None, Header(alias="Paddle-Signature")] = None,
) -> dict[str, Any]:
    """Paddle Billing webhook notification destination."""
    raw_body = await request.body()
    try:
        result = await handle_paddle_webhook_event(
            session=session,
            raw_body=raw_body,
            signature_header=paddle_signature,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

