"""API tests for chat session + SSE with mocked LLM/search."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from torii_ai.api import chat as chat_api
from torii_ai.citations.models import Citation
from torii_ai.llm.groq import FakeChatClient
from torii_ai.main import create_app
from torii_ai.services.assistant import AssistantService
from torii_ai.services.sessions import session_store
from torii_ai.tools.tavily import FakeSearchClient, TavilySearchResult


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    # Reset in-memory sessions between tests.
    session_store._by_sid.clear()  # noqa: SLF001

    cite = Citation(
        authority="www.isa.go.jp",
        title="Extension of Period of Stay",
        url="https://www.isa.go.jp/en/applications/procedures/16-3.html",
        retrieved_at=datetime.now(UTC),
        source_version="2026-07",
    )
    search = FakeSearchClient(
        [
            TavilySearchResult(
                title=cite.title,
                url=cite.url or "",
                content="Applicants file an Application for Extension of Period of Stay.",
                citation=cite,
            )
        ]
    )
    chat = FakeChatClient(
        reply="""{
          "bubbles": [
            {
              "text": "For renewal you file the Application for Extension of Period of Stay.",
              "claims_requirement": true,
              "instruction": {
                "text": "File the Application for Extension of Period of Stay.",
                "kind": "form_requirement",
                "official_term": null,
                "source_indexes": [0]
              }
            },
            {
              "text": "Want me to walk through the listed documents next?",
              "claims_requirement": false
            }
          ],
          "escalation": null
        }"""
    )
    assistant = AssistantService(chat=chat, search=search)

    app = create_app()
    app.dependency_overrides[chat_api.get_assistant] = lambda: assistant

    transport = ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_health(client: AsyncClient) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    assert resp.json()["service"] == "torii-ai"


@pytest.mark.asyncio
async def test_session_sets_cookie(client: AsyncClient) -> None:
    resp = await client.post("/ai/chat/session", json={"case_id": None, "locale": "en"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["conversation_id"]
    assert body["messages"] == []
    assert "ai_sid" in resp.cookies


@pytest.mark.asyncio
async def test_messages_sse_streams_bubbles(client: AsyncClient) -> None:
    session = await client.post("/ai/chat/session", json={})
    assert session.status_code == 200

    resp = await client.post(
        "/ai/chat/messages",
        json={"message": "What form do I file for a Japan work visa renewal?"},
    )
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]
    text = resp.text
    assert "event: bubble" in text
    assert "Application for Extension" in text
    assert "event: done" in text
    assert '"kind": "reply"' in text


@pytest.mark.asyncio
async def test_refusal_path(client: AsyncClient) -> None:
    await client.post("/ai/chat/session", json={})
    resp = await client.post(
        "/ai/chat/messages",
        json={"message": "Should I apply for renewal or change of status?"},
    )
    assert resp.status_code == 200
    assert "event: done" in resp.text
    assert '"kind": "refusal"' in resp.text


@pytest.mark.asyncio
async def test_case_context_and_fix_actions() -> None:
    assistant = AssistantService(chat=FakeChatClient(reply="fallback"), search=FakeSearchClient())
    reply = await assistant.reply(
        message="how to fix this",
        case_reference="Case #44 - JP-2026-000044",
        scope_label="Japan · Student (renewal)",
        case_status="eligibility",
        jurisdiction_code="JP",
        visa_category_code="student",
        action_code="renewal",
        eligibility_findings=[
            {
                "key": "school_completed",
                "status": "disqualified",
                "message": "A change of status requires completion of your program at a Japanese educational institution.",
            },
            {
                "key": "has_job_offer",
                "status": "disqualified",
                "message": "A formal job offer is required.",
            },
            {
                "key": "employer_sanctioned",
                "status": "incomplete",
                "message": "Missing answer in intake.",
            },
        ],
    )
    assert reply.kind == "reply"
    text = reply.bubbles[0].text
    assert "School Completed" in text
    assert "Has Job Offer" in text
    assert "Employer Sanctioned" in text
    assert "[ACTION:update_intake" in text
    assert 'key="school_completed"' in text
    assert 'key="has_job_offer"' in text
    assert 'key="employer_sanctioned"' in text
