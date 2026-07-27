"""In-memory conversation sessions (v1 — no AI DB yet)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import Lock
from typing import Any
from uuid import uuid4


@dataclass
class ChatMessage:
    role: str
    content: str
    created_at: datetime
    instructions: list[dict[str, Any]] = field(default_factory=list)

    def to_public(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "role": self.role,
            "content": self.content,
            "created_at": self.created_at.isoformat(),
        }
        if self.role == "assistant" and self.instructions:
            out["instructions"] = self.instructions
        return out


@dataclass
class Conversation:
    id: str
    case_id: str | None
    locale: str
    messages: list[ChatMessage] = field(default_factory=list)


class SessionStore:
    """Process-local session map keyed by ``ai_sid`` cookie value."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._by_sid: dict[str, Conversation] = {}

    def get_or_create(
        self,
        sid: str | None,
        *,
        case_id: str | None,
        locale: str = "en",
    ) -> tuple[str, Conversation]:
        with self._lock:
            if sid and sid in self._by_sid:
                convo = self._by_sid[sid]
                if case_id is not None:
                    convo.case_id = case_id
                return sid, convo
            new_sid = sid or str(uuid4())
            convo = Conversation(id=str(uuid4()), case_id=case_id, locale=locale)
            self._by_sid[new_sid] = convo
            return new_sid, convo

    def get(self, sid: str) -> Conversation | None:
        with self._lock:
            return self._by_sid.get(sid)

    def append(self, sid: str, message: ChatMessage) -> None:
        with self._lock:
            convo = self._by_sid.get(sid)
            if convo is None:
                return
            convo.messages.append(message)


# Process singleton — fine for single-worker local/dev; replace with Redis/DB later.
session_store = SessionStore()


def utcnow() -> datetime:
    return datetime.now(UTC)
