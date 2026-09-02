"""Tests for the credit balance, top-up packs, atomic consumption, and case unlock endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_credits_balance_and_initial_grant(client: AsyncClient) -> None:
    # 1. Register a new user (receives 3 welcome credits by default)
    reg = await client.post(
        "/v1/auth/register",
        json={"email": "credit_test@example.com", "password": "password123"},
    )
    assert reg.status_code == 201
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Query balance
    bal_res = await client.get("/v1/credits/balance", headers=headers)
    assert bal_res.status_code == 200
    bal_data = bal_res.json()
    assert bal_data["credit_balance"] == 3
    assert len(bal_data["packs"]) == 3


@pytest.mark.asyncio
async def test_credits_consume_and_insufficient_balance(client: AsyncClient) -> None:
    reg = await client.post(
        "/v1/auth/register",
        json={"email": "credit_consume@example.com", "password": "password123"},
    )
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Consume 2 credits for OCR
    ocr_res = await client.post(
        "/v1/credits/consume",
        json={
            "feature": "ocr_extraction",
            "amount": 2,
            "description": "OCR scan of passport photo page",
        },
        headers=headers,
    )
    assert ocr_res.status_code == 200
    assert ocr_res.json()["credits_consumed"] == 2
    assert ocr_res.json()["credit_balance"] == 1

    # 2. Consume 1 credit for AI Q&A
    ai_res = await client.post(
        "/v1/credits/consume",
        json={
            "feature": "ai_query",
            "amount": 1,
            "description": "AI Copilot legal citation lookup",
        },
        headers=headers,
    )
    assert ai_res.status_code == 200
    assert ai_res.json()["credit_balance"] == 0

    # 3. Attempt to consume more credits than balance (e.g. 50) -> HTTP 402
    over_res = await client.post(
        "/v1/credits/consume",
        json={
            "feature": "case_unlock",
            "amount": 50,
            "description": "Attempted over-consumption",
        },
        headers=headers,
    )
    assert over_res.status_code == 402


@pytest.mark.asyncio
async def test_credits_top_up(client: AsyncClient) -> None:
    reg = await client.post(
        "/v1/auth/register",
        json={"email": "credit_topup@example.com", "password": "password123"},
    )
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Top up standard bundle (3 passes)
    top_res = await client.post(
        "/v1/credits/top-up",
        json={"pack_id": "standard", "currency": "usd"},
        headers=headers,
    )
    assert top_res.status_code == 200
    data = top_res.json()
    assert data["credits_added"] == 3
    assert data["credit_balance"] == 6  # 3 initial + 3

    # Balance ledger check
    bal_res = await client.get("/v1/credits/balance", headers=headers)
    assert bal_res.status_code == 200
    txs = bal_res.json()["recent_transactions"]
    assert len(txs) >= 1
    assert txs[0]["amount"] == 3
    assert txs[0]["feature"] == "top_up"
