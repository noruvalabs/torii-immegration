"""Mock payment service for visa application fees."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from torii_api.db.models import (
    Case,
    Payment,
    PaymentStatus,
)

log = structlog.get_logger()

# Mock visa fees by destination country and visa type (USD)
VISA_FEES: dict[str, dict[str, float]] = {
    "US": {"tourist": 185, "student": 185, "work": 190},
    "UK": {"tourist": 115, "student": 348, "work": 259},
    "CA": {"tourist": 100, "student": 150, "work": 155},
    "AU": {"tourist": 195, "student": 710, "work": 405},
    "DE": {"tourist": 90, "student": 75, "work": 75},
    "FR": {"tourist": 90, "student": 75, "work": 75},
    "JP": {"tourist": 3000, "student": 3000, "work": 4000},  # JPY
    "SG": {"tourist": 30, "student": 30, "work": 225},
    "KR": {"tourist": 40, "student": 40, "work": 55},
}

# Service fee (USD)
SERVICE_FEE = 49.99

# Currency mapping
CURRENCY_MAP: dict[str, str] = {
    "JP": "JPY",
    "US": "USD",
    "UK": "GBP",
    "CA": "CAD",
    "AU": "AUD",
    "DE": "EUR",
    "FR": "EUR",
    "SG": "SGD",
    "KR": "KRW",
}


def generate_transaction_id() -> str:
    """Generate a unique transaction ID."""
    return f"TXN-{uuid.uuid4().hex[:12].upper()}"


def get_visa_fee(destination_code: str, visa_type: str) -> float:
    """Get visa fee for a destination country and visa type."""
    country_fees = VISA_FEES.get(destination_code, {})
    return country_fees.get(visa_type.lower(), 99.99)  # Default fee


def get_currency(destination_code: str) -> str:
    """Get currency for a destination country."""
    return CURRENCY_MAP.get(destination_code, "USD")


async def create_payment(
    db: AsyncSession,
    case_id: int,
    user_id: int,
    destination_code: str,
    visa_type: str,
    metadata: dict[str, Any] | None = None,
) -> Payment:
    """Create a new payment record for a case."""
    visa_fee = get_visa_fee(destination_code, visa_type)
    currency = get_currency(destination_code)
    total = visa_fee + SERVICE_FEE

    payment = Payment(
        case_id=case_id,
        user_id=user_id,
        transaction_id=generate_transaction_id(),
        visa_fee=visa_fee,
        service_fee=SERVICE_FEE,
        total_amount=total,
        currency=currency,
        status=PaymentStatus.PENDING,
        metadata_json=metadata or {},
    )
    db.add(payment)
    await db.flush()
    log.info(
        "payment.created",
        case_id=case_id,
        transaction_id=payment.transaction_id,
        total=total,
        currency=currency,
    )
    return payment


async def process_mock_payment(
    db: AsyncSession,
    payment_id: int,
    user_id: int,
    payment_method: str = "card",
) -> Payment:
    """Process a mock payment (always succeeds)."""
    result = await db.execute(
        select(Payment).where(Payment.id == payment_id, Payment.user_id == user_id)
    )
    payment = result.scalar_one_or_none()

    if not payment:
        raise ValueError("Payment not found")

    if payment.status != PaymentStatus.PENDING:
        raise ValueError(f"Payment cannot be processed: {payment.status}")

    # Update payment status
    payment.status = PaymentStatus.PROCESSING
    payment.payment_method = payment_method
    await db.flush()

    # Simulate processing delay (mock - immediately completes)
    payment.status = PaymentStatus.COMPLETED
    payment.paid_at = datetime.now(UTC)

    # Update case status to payment_completed
    case_result = await db.execute(select(Case).where(Case.id == payment.case_id))
    case = case_result.scalar_one_or_none()
    if case and case.status in ("checklist_ready", "forms_generated", "packet_ready"):
        case.status = "payment_completed"

    await db.flush()
    log.info(
        "payment.completed",
        payment_id=payment.id,
        transaction_id=payment.transaction_id,
        case_id=payment.case_id,
    )
    return payment


async def get_payment_by_case(
    db: AsyncSession,
    case_id: int,
    user_id: int,
) -> Payment | None:
    """Get the latest payment for a case."""
    result = await db.execute(
        select(Payment)
        .where(Payment.case_id == case_id, Payment.user_id == user_id)
        .order_by(Payment.created_at.desc())
    )
    return result.scalar_one_or_none()


async def get_user_payments(
    db: AsyncSession,
    user_id: int,
    limit: int = 20,
    offset: int = 0,
) -> list[Payment]:
    """Get all payments for a user."""
    result = await db.execute(
        select(Payment)
        .where(Payment.user_id == user_id)
        .order_by(Payment.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


async def refund_payment(
    db: AsyncSession,
    payment_id: int,
    user_id: int,
    reason: str = "Customer request",
) -> Payment:
    """Refund a completed payment (mock)."""
    result = await db.execute(
        select(Payment).where(Payment.id == payment_id, Payment.user_id == user_id)
    )
    payment = result.scalar_one_or_none()

    if not payment:
        raise ValueError("Payment not found")

    if payment.status != PaymentStatus.COMPLETED:
        raise ValueError(f"Payment cannot be refunded: {payment.status}")

    payment.status = PaymentStatus.REFUNDED
    if payment.metadata_json:
        payment.metadata_json["refund_reason"] = reason
    else:
        payment.metadata_json = {"refund_reason": reason}

    await db.flush()
    log.info("payment.refunded", payment_id=payment.id, reason=reason)
    return payment
