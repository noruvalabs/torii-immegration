"""Paddle Billing integration service (FastAPI / SQLAlchemy).

Implements transaction creation, hosted/overlay checkout sessions, webhook signature
verification, and atomic credit grants matching Torii's credit economy.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
import uuid
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from torii_api.config import get_settings
from torii_api.db.models import (
    CreditTransaction,
    PaymentCheckout,
    PaymentWebhookEvent,
    User,
)

logger = structlog.get_logger()

_SANDBOX_BASE_URL = "https://sandbox-api.paddle.com"
_PRODUCTION_BASE_URL = "https://api.paddle.com"

_ZERO_DECIMAL_CURRENCIES = frozenset({"JPY", "KRW"})
_REPLAY_TOLERANCE_SECONDS = 300


def _minor_units(amount: float, currency: str) -> str:
    """Return unit_price.amount string formatted in smallest currency units."""
    multiplier = Decimal("1") if currency.upper() in _ZERO_DECIMAL_CURRENCIES else Decimal("100")
    minor = (Decimal(str(amount)) * multiplier).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return str(int(minor))


def verify_webhook_signature(
    raw_body: bytes,
    signature_header: str,
    secret: str,
    tolerance_seconds: int = _REPLAY_TOLERANCE_SECONDS,
) -> bool:
    """Verify a `Paddle-Signature` header per Paddle's HMAC-SHA256 scheme."""
    if not signature_header or not secret:
        return False

    try:
        parts = dict(item.split("=", 1) for item in signature_header.split(";"))
        timestamp, signature = parts["ts"], parts["h1"]
    except (KeyError, ValueError):
        return False

    try:
        parsed_timestamp = int(timestamp)
    except ValueError:
        return False

    if abs(time.time() - parsed_timestamp) > tolerance_seconds:
        return False

    computed = hmac.new(
        secret.encode("utf-8"),
        f"{timestamp}:{raw_body.decode('utf-8')}".encode(),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(computed, signature)


class PaddleClient:
    """HTTP client for Paddle v2 Billing REST API."""

    def __init__(self, api_key: str, environment: str = "sandbox") -> None:
        self._base_url = _SANDBOX_BASE_URL if environment == "sandbox" else _PRODUCTION_BASE_URL
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=20.0, base_url=self._base_url) as client:
            response = await client.request(
                method, path, headers=self._headers, json=json_body, params=params
            )

        if response.status_code >= 400:
            logger.error(
                "paddle_api_error",
                path=path,
                status_code=response.status_code,
                body=response.text[:1000],
            )
            response.raise_for_status()

        return response.json() if response.content else {}

    async def find_customer_by_email(self, email: str) -> dict[str, Any] | None:
        payload = await self._request("GET", "/customers", params={"search": email})
        items = payload.get("data") or []
        for item in items:
            if item.get("email", "").lower() == email.lower():
                return item
        return items[0] if items else None

    async def create_customer(self, email: str) -> dict[str, Any]:
        payload = await self._request("POST", "/customers", json_body={"email": email})
        return payload["data"]

    async def ensure_customer(self, email: str) -> str:
        existing = await self.find_customer_by_email(email)
        if existing:
            return str(existing["id"])
        created = await self.create_customer(email)
        return str(created["id"])

    async def find_product_by_name(self, name: str) -> dict[str, Any] | None:
        payload = await self._request("GET", "/products", params={"search": name})
        for prod in payload.get("data") or []:
            if prod.get("name") == name:
                return prod
        return None

    async def create_product(self, name: str, description: str) -> dict[str, Any]:
        payload = await self._request(
            "POST",
            "/products",
            json_body={"name": name, "description": description, "tax_category": "saas"},
        )
        return payload["data"]

    async def ensure_product(self, plan_key: str, plan_name: str) -> str:
        name = f"Torii Visa — {plan_name}"
        existing = await self.find_product_by_name(name)
        if existing:
            return str(existing["id"])
        created = await self.create_product(
            name=name,
            description="Torii Immigration Application Pass and AI Dossier Preparation",
        )
        return str(created["id"])

    async def create_transaction(self, body: dict[str, Any]) -> dict[str, Any]:
        payload = await self._request("POST", "/transactions", json_body=body)
        return payload["data"]

    async def get_transaction(self, transaction_id: str) -> dict[str, Any]:
        payload = await self._request("GET", f"/transactions/{transaction_id}")
        return payload["data"]


async def create_checkout_session(
    session: AsyncSession,
    user: User,
    pack: dict[str, Any],
    currency: str = "usd",
) -> PaymentCheckout:
    """Create a checkout record and register a transaction with Paddle."""
    settings = get_settings()
    currency = currency.upper()
    amount = float(pack["price_usd"] if currency == "USD" else pack["price_jpy"])
    public_id = str(uuid.uuid4())

    checkout = PaymentCheckout(
        public_id=public_id,
        user_id=user.id,
        pack_id=str(pack["id"]),
        credits=int(pack["credits"]),
        amount=amount,
        currency=currency,
        provider="paddle",
        status="requires_payment",
        metadata_json={
            "pack_name": pack["name"],
            "user_email": user.email,
        },
    )
    session.add(checkout)
    await session.flush()

    # If Paddle API key is not configured, record checkout and return mock/pending checkout
    if not settings.paddle_api_key:
        checkout.checkout_url = f"/checkout?mock=true&checkout_id={public_id}"
        await session.commit()
        await session.refresh(checkout)
        return checkout

    client = PaddleClient(settings.paddle_api_key, settings.paddle_env)
    customer_id = await client.ensure_customer(user.email)
    checkout.provider_customer_id = customer_id

    # Check for pre-configured catalog price (required in live)
    price_ids: dict[str, Any] = {}
    try:
        price_ids = json.loads(settings.paddle_price_ids) if settings.paddle_price_ids else {}
    except Exception:
        price_ids = {}

    catalog_price_id = (price_ids.get(pack["id"]) or {}).get(currency)
    if catalog_price_id and catalog_price_id.startswith("pri_"):
        item: dict[str, Any] = {"price_id": catalog_price_id, "quantity": 1}
    else:
        product_id = await client.ensure_product(pack["id"], pack["name"])
        price_body = {
            "description": f"{pack['name']} ({currency} {amount})",
            "product_id": product_id,
            "unit_price": {
                "amount": _minor_units(amount, currency),
                "currency_code": currency,
            },
        }
        item = {"price": price_body, "quantity": 1}

    txn_body: dict[str, Any] = {
        "customer_id": customer_id,
        "currency_code": currency,
        "collection_mode": "automatic",
        "items": [item],
        "custom_data": {
            "public_checkout_id": public_id,
            "pack_id": pack["id"],
            "user_id": str(user.id),
        },
    }

    if settings.paddle_default_checkout_url:
        base_url = settings.paddle_default_checkout_url
        sep = "&" if "?" in base_url else "?"
        txn_body["checkout"] = {"url": f"{base_url}{sep}checkout_id={public_id}"}

    txn = await client.create_transaction(txn_body)
    checkout.provider_session_id = txn.get("id")
    checkout.checkout_url = (txn.get("checkout") or {}).get("url") or ""
    await session.commit()
    await session.refresh(checkout)
    return checkout


async def handle_paddle_webhook_event(
    session: AsyncSession,
    raw_body: bytes,
    signature_header: str | None,
) -> dict[str, Any]:
    """Verify webhook signature, deduplicate event, and fulfill credits on payment."""
    settings = get_settings()

    # Verify signature if secret is configured
    if settings.paddle_webhook_secret:
        if not signature_header:
            raise ValueError("Missing Paddle-Signature header")
        if not verify_webhook_signature(raw_body, signature_header, settings.paddle_webhook_secret):
            raise ValueError("Invalid Paddle webhook signature")

    payload = json.loads(raw_body.decode("utf-8"))
    event_id = str(payload.get("event_id") or payload.get("notification_id") or uuid.uuid4())
    event_type = str(payload.get("event_type") or "")
    data = payload.get("data") or {}

    # Deduplicate event
    existing_event = await session.execute(
        select(PaymentWebhookEvent).where(PaymentWebhookEvent.event_id == event_id)
    )
    if existing_event.scalar_one_or_none():
        logger.info("paddle_webhook_duplicate_ignored", event_id=event_id)
        return {"status": "duplicate_ignored", "event_id": event_id}

    # Record webhook event
    occurred_at_str = payload.get("occurred_at")
    occurred_at = None
    if occurred_at_str:
        try:
            occurred_at = datetime.fromisoformat(occurred_at_str.replace("Z", "+00:00"))
        except Exception:
            occurred_at = None

    wh_record = PaymentWebhookEvent(
        provider="paddle",
        event_id=event_id,
        event_type=event_type,
        occurred_at=occurred_at,
    )
    session.add(wh_record)

    # Process events
    if event_type in ("transaction.completed", "transaction.paid"):
        txn_id = data.get("id")
        custom_data = data.get("custom_data") or {}
        public_checkout_id = custom_data.get("public_checkout_id")

        checkout = None
        if public_checkout_id:
            res = await session.execute(
                select(PaymentCheckout).where(PaymentCheckout.public_id == str(public_checkout_id))
            )
            checkout = res.scalar_one_or_none()

        if not checkout and txn_id:
            res = await session.execute(
                select(PaymentCheckout).where(PaymentCheckout.provider_session_id == str(txn_id))
            )
            checkout = res.scalar_one_or_none()

        if checkout and checkout.status != "succeeded":
            checkout.status = "succeeded"
            checkout.completed_at = datetime.now(UTC)
            if txn_id and not checkout.provider_session_id:
                checkout.provider_session_id = txn_id

            # Credit user balance
            user = await session.get(User, checkout.user_id)
            if user:
                user.credit_balance += checkout.credits
                currency_sym = "$" if checkout.currency == "USD" else "¥"
                amt_str = f"{checkout.amount:,.0f}" if checkout.currency == "JPY" else f"{checkout.amount:.2f}"
                tx = CreditTransaction(
                    user_id=user.id,
                    amount=checkout.credits,
                    balance_after=user.credit_balance,
                    feature="top_up",
                    description=(
                        f"Purchased {checkout.credits} Application Pass(es) via Paddle "
                        f"({currency_sym}{amt_str})"
                    ),
                    reference_id=txn_id or checkout.public_id,
                )
                session.add(tx)
                logger.info(
                    "paddle_payment_fulfilled",
                    user_id=user.id,
                    credits_added=checkout.credits,
                    balance=user.credit_balance,
                    checkout_id=checkout.public_id,
                )

    elif event_type in ("transaction.canceled", "transaction.payment_failed"):
        txn_id = data.get("id")
        custom_data = data.get("custom_data") or {}
        public_checkout_id = custom_data.get("public_checkout_id")

        checkout = None
        if public_checkout_id:
            res = await session.execute(
                select(PaymentCheckout).where(PaymentCheckout.public_id == str(public_checkout_id))
            )
            checkout = res.scalar_one_or_none()
        elif txn_id:
            res = await session.execute(
                select(PaymentCheckout).where(PaymentCheckout.provider_session_id == str(txn_id))
            )
            checkout = res.scalar_one_or_none()

        if checkout and checkout.status == "requires_payment":
            checkout.status = "cancelled" if "canceled" in event_type else "failed"

    await session.commit()
    return {"status": "processed", "event_id": event_id, "event_type": event_type}
