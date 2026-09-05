"""Chat session + SSE message endpoints (citation-contract.md)."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Annotated, Any

from fastapi import APIRouter, Cookie, Depends, Request, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from torii_ai.config import Settings, get_settings
from torii_ai.llm.groq import FakeChatClient, GroqChatClient
from torii_ai.llm.nvidia import NvidiaChatClient
from torii_ai.services.assistant import AssistantService
from torii_ai.services.sessions import ChatMessage, session_store, utcnow
from torii_ai.tools.tavily import FakeSearchClient, TavilyClient

router = APIRouter(prefix="/ai/chat", tags=["chat"])

COOKIE_NAME = "ai_sid"


class SessionIn(BaseModel):
    case_id: str | None = None
    locale: str = Field(default="en", max_length=16)


class SessionOut(BaseModel):
    conversation_id: str
    locale: str
    messages: list[dict[str, Any]]


class MessageIn(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    case_id: str | None = None
    case_reference: str | None = None
    scope_label: str | None = None
    case_status: str | None = None
    current_step: str | None = None
    jurisdiction_code: str | None = None
    visa_category_code: str | None = None
    action_code: str | None = None
    origin_country: str | None = None
    residence_country: str | None = None
    intake_answers: dict[str, Any] | None = None
    eligibility_findings: list[dict[str, Any]] | None = None
    checklist: list[dict[str, Any]] | None = None
    review_flags: list[dict[str, Any]] | None = None
    user_profile: dict[str, Any] | None = None
    locale: str = Field(default="en", max_length=16)


def get_assistant(settings: Annotated[Settings, Depends(get_settings)]) -> AssistantService:
    """Default wired assistant; tests override via ``app.dependency_overrides``."""
    search = TavilyClient(settings) if settings.tavily_api_key else FakeSearchClient()
    if settings.groq_api_key:
        chat = GroqChatClient(settings, model=settings.groq_extract_model or settings.groq_model)
    elif settings.nvidia_api_key:
        chat = NvidiaChatClient(settings)
    else:
        chat = FakeChatClient()
    return AssistantService(chat=chat, search=search)


AssistantDep = Annotated[AssistantService, Depends(get_assistant)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


@router.post("/session", response_model=SessionOut)
async def create_session(
    payload: SessionIn,
    response: Response,
    settings: SettingsDep,
    ai_sid: Annotated[str | None, Cookie(alias=COOKIE_NAME)] = None,
) -> SessionOut:
    """Establish or refresh the anonymous chat session (US-14.4)."""
    sid, convo = session_store.get_or_create(ai_sid, case_id=payload.case_id, locale=payload.locale)
    response.set_cookie(
        key=COOKIE_NAME,
        value=sid,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        # The browser reaches this service both directly at /ai and through the
        # Next.js /assistant/ai proxy. A root-scoped cookie preserves the same
        # conversation on both route shapes.
        path="/",
    )
    return SessionOut(
        conversation_id=convo.id,
        locale=convo.locale,
        messages=[m.to_public() for m in convo.messages],
    )


@router.post("/messages")
async def post_message(
    payload: MessageIn,
    request: Request,
    assistant: AssistantDep,
    settings: SettingsDep,
    ai_sid: Annotated[str | None, Cookie(alias=COOKIE_NAME)] = None,
) -> StreamingResponse:
    """Stream assistant bubbles as SSE (citation-contract.md)."""
    sid, convo = session_store.get_or_create(ai_sid, case_id=payload.case_id, locale=payload.locale)
    session_store.append(
        sid,
        ChatMessage(role="user", content=payload.message, created_at=utcnow()),
    )

    reply = await assistant.reply(
        message=payload.message,
        locale=payload.locale or convo.locale,
        case_reference=payload.case_reference,
        scope_label=payload.scope_label,
        case_status=payload.case_status,
        current_step=payload.current_step,
        jurisdiction_code=payload.jurisdiction_code,
        visa_category_code=payload.visa_category_code,
        action_code=payload.action_code,
        origin_country=payload.origin_country,
        residence_country=payload.residence_country,
        intake_answers=payload.intake_answers,
        eligibility_findings=payload.eligibility_findings,
        checklist=payload.checklist,
        review_flags=payload.review_flags,
        user_profile=payload.user_profile,
    )

    async def event_stream() -> AsyncIterator[bytes]:
        assistant_parts: list[str] = []
        all_instructions: list[dict[str, Any]] = []
        for index, bubble in enumerate(reply.bubbles):
            instructions = [i.model_dump(mode="json") for i in bubble.instructions]
            all_instructions.extend(instructions)
            assistant_parts.append(bubble.text)
            data = {"index": index, "text": bubble.text, "instructions": instructions}
            yield _sse("bubble", data)
        done = {"kind": reply.kind, "escalation_reason": reply.escalation_reason}
        yield _sse("done", done)
        session_store.append(
            sid,
            ChatMessage(
                role="assistant",
                content="\n\n".join(assistant_parts),
                created_at=utcnow(),
                instructions=all_instructions,
            ),
        )

    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    # Ensure cookie is set even if session was new on this request.
    response = StreamingResponse(event_stream(), media_type="text/event-stream", headers=headers)
    response.set_cookie(
        key=COOKIE_NAME,
        value=sid,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        path="/",
    )
    # request reserved for future auth header inspection
    _ = request
    return response


def _sse(event: str, data: dict[str, Any]) -> bytes:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n".encode()
