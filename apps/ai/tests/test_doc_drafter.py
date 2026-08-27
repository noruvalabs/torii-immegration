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


@pytest.mark.asyncio
async def test_draft_gyoseishoshi_reason_letters() -> None:
    settings = Settings()
    chat = FakeChatClient()
    drafter = AIDocDrafter(chat, settings)

    # 1. Employer Hiring Reason Letter (雇用理由書)
    req_hiring = AIDraftRequest(
        doc_type="reason_letter_work_hiring",
        jurisdiction_code="JP",
        scope_label="Japan · Work Visa (技人国)",
        case_reference="JP-2026-000045",
        intake_answers={
            "full_name": "Rahim Ahmed",
            "employer_name": "Tokyo Cloud Solutions K.K.",
            "monthly_salary": "¥450,000",
        },
    )
    res_hiring = await drafter.draft_document(req_hiring)
    assert "雇用理由書" in res_hiring["content"]
    assert "Rahim Ahmed" in res_hiring["content"]
    assert "Tokyo Cloud Solutions K.K." in res_hiring["content"]

    # 2. Major & Duty Relevance (専攻・職務関連性説明書)
    req_relevance = AIDraftRequest(
        doc_type="reason_letter_major_relevance",
        jurisdiction_code="JP",
        scope_label="Japan · Work Visa (技人国)",
        case_reference="JP-2026-000046",
        intake_answers={
            "full_name": "Elena Rostova",
            "nationality": "Germany",
            "employer_name": "Nippon Robotics Corp.",
            "main_purpose": "AI Autonomous Navigation Software Engineering",
        },
    )
    res_relevance = await drafter.draft_document(req_relevance)
    assert "職務内容と専攻の関連性説明書" in res_relevance["content"]
    assert "Elena Rostova" in res_relevance["content"]

    # 3. Permanent Residence Reason Letter (永住理由書)
    req_pr = AIDraftRequest(
        doc_type="reason_letter_permanent_residence",
        jurisdiction_code="JP",
        scope_label="Japan · Permanent Residence (永住許可)",
        case_reference="JP-2026-000047",
        intake_answers={
            "full_name": "Tariq Mansour",
            "nationality": "France",
            "employer_name": "Fintech Japan K.K.",
            "monthly_salary": "¥800,000",
        },
    )
    res_pr = await drafter.draft_document(req_pr)
    assert "永住許可申請理由書" in res_pr["content"]
    assert "Tariq Mansour" in res_pr["content"]
    assert "法務大臣 殿" in res_pr["content"]

    # 4. Employer Change Notification (所属機関等届出書 - 入管法第19条の16)
    req_job_change = AIDraftRequest(
        doc_type="change_of_employer_notification",
        jurisdiction_code="JP",
        scope_label="Japan · Article 19-16 Job Change Notification",
        case_reference="JP-2026-000048",
        intake_answers={
            "full_name": "Akira Tanaka",
            "nationality": "Canada",
            "employer_name": "NextGen AI Lab Inc.",
        },
    )
    res_job_change = await drafter.draft_document(req_job_change)
    assert "所属機関等に関する届出書" in res_job_change["content"]
    assert "入管法第19条の16" in res_job_change["content"]
    assert "Akira Tanaka" in res_job_change["content"]
