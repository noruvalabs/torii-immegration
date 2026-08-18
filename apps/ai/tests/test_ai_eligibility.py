"""Tests for AI-powered eligibility evaluator (US-04)."""

from __future__ import annotations

import json

import pytest
from httpx import ASGITransport, AsyncClient

from torii_ai.config import Settings
from torii_ai.llm.groq import FakeChatClient
from torii_ai.main import create_app
from torii_ai.services.eligibility_evaluator import (
    AIElegibilityEvaluator,
    AIEvaluationRequest,
)

SAMPLE_LLM_REPLY = json.dumps(
    {
        "result": "pass",
        "summary": "Applicant satisfies all visitor visa requirements.",
        "findings": [
            {
                "key": "travel_purpose",
                "status": "pass",
                "message": "Trip purpose 'visiting family and tourism' is legitimate.",
                "citation": {
                    "authority": "Ministry of Foreign Affairs of Japan",
                    "title": "Visa for Temporary Visitors",
                    "url": "https://www.mofa.go.jp/j_info/visit/visa/index.html",
                    "source_version": "2026-08",
                },
            },
            {
                "key": "financial_capacity",
                "status": "pass",
                "message": "Funds and employment proof are sufficient.",
                "citation": {
                    "authority": "Ministry of Foreign Affairs of Japan",
                    "title": "Visa for Temporary Visitors",
                    "url": "https://www.mofa.go.jp/j_info/visit/visa/index.html",
                    "source_version": "2026-08",
                },
            },
        ],
        "disclaimer": "This is an AI-assisted preparation check based on official published criteria, not legal advice or a government decision.",
    }
)


@pytest.mark.asyncio
async def test_ai_eligibility_evaluator_with_llm_json() -> None:
    settings = Settings()
    chat = FakeChatClient(reply=SAMPLE_LLM_REPLY)
    evaluator = AIElegibilityEvaluator(chat=chat, settings=settings)

    req = AIEvaluationRequest(
        destination_code="JP",
        purpose_code="tourist",
        action_code="new_application",
        nationality="BD",
        residence_country="BD",
        answers={
            "purpose_of_visit": "visiting family and tourism",
            "intended_length_of_stay_days": 14,
            "visitor_has_sufficient_funds": True,
        },
    )

    result = await evaluator.evaluate(req)
    assert result["result"] == "pass"
    assert len(result["findings"]) == 2
    assert result["findings"][0]["key"] == "travel_purpose"
    assert result["findings"][0]["status"] == "pass"
    assert "mofa.go.jp" in result["findings"][0]["citation"]["url"]


@pytest.mark.asyncio
async def test_ai_eligibility_evaluator_heuristic_fallback() -> None:
    settings = Settings()
    # Invalid JSON triggers safe heuristic fallback
    chat = FakeChatClient(reply="Invalid non-JSON response")
    evaluator = AIElegibilityEvaluator(chat=chat, settings=settings)

    req = AIEvaluationRequest(
        destination_code="JP",
        purpose_code="tourist",
        action_code="new_application",
        nationality="BD",
        residence_country="BD",
        answers={
            "purpose_of_visit": "tourism",
            "intended_length_of_stay_days": 10,
            "visitor_has_sufficient_funds": True,
        },
    )

    result = await evaluator.evaluate(req)
    assert result["result"] == "pass"
    assert len(result["findings"]) >= 3
    keys = [f["key"] for f in result["findings"]]
    assert "purpose_of_stay" in keys
    assert "stay_duration" in keys


@pytest.mark.asyncio
async def test_ai_eligibility_endpoint() -> None:
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post(
            "/ai/agentic/evaluate-eligibility",
            json={
                "destination_code": "JP",
                "purpose_code": "tourist",
                "action_code": "new_application",
                "nationality": "BD",
                "residence_country": "BD",
                "answers": {
                    "purpose_of_visit": "sightseeing",
                    "intended_length_of_stay_days": 14,
                },
                "rules": [],
                "context": {},
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert "result" in data
        assert "findings" in data
        assert isinstance(data["findings"], list)
        assert len(data["findings"]) > 0
