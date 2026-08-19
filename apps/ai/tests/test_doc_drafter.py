"""Tests for AI Document Drafter (Cover letter, Statement of Reason, Schedule of stay)."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from torii_ai.config import Settings
from torii_ai.llm.groq import FakeChatClient
from torii_ai.main import create_app
from torii_ai.services.doc_drafter import AIDocDrafter, AIDraftRequest


@pytest.mark.asyncio
async def test_doc_drafter_service_fallback() -> None:
    settings = Settings()
    chat = FakeChatClient()
    drafter = AIDocDrafter(chat, settings)

    req = AIDraftRequest(
        doc_type="cover_letter",
        jurisdiction_code="JP",
        scope_label="Japan · Work Visa Extension",
        case_reference="JP-2026-000019",
        intake_answers={
            "full_name": "Kenji Sato",
            "passport_number": "TK99887766",
            "nationality": "Japan",
            "employer_name": "Torii Tech K.K.",
            "monthly_salary": "¥650,000",
        },
        checklist=[{"name": "Passport", "status": "gathered"}],
    )

    result = await drafter.draft_document(req)
    assert result["doc_type"] == "cover_letter"
    assert "Kenji Sato" in result["content"]
    assert "TK99887766" in result["content"]
    assert "Torii Tech K.K." in result["content"]


@pytest.mark.asyncio
async def test_draft_document_endpoint() -> None:
    settings = Settings(groq_api_key="", nvidia_api_key="")
    app = create_app(settings)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/ai/agentic/draft-document",
            json={
                "doc_type": "statement_of_reason",
                "jurisdiction_code": "JP",
                "scope_label": "Japan · Work Visa Extension",
                "case_reference": "JP-2026-000019",
                "intake_answers": {
                    "full_name": "Maria Garcia",
                    "passport_number": "MG123456",
                    "nationality": "Spain",
                    "main_purpose": "Senior System Architect duties",
                    "employer_name": "Tokyo AI Systems",
                },
                "checklist": [{"name": "Certificate of Employment", "status": "uploaded"}],
            },
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["doc_type"] == "statement_of_reason"
    assert "Maria Garcia" in body["content"]
    assert "Tokyo AI Systems" in body["content"]
    assert "STATEMENT OF REASON" in body["content"]
