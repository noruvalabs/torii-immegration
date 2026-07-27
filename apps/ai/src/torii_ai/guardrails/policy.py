"""UPL / information-not-advice guardrails (US-12, US-15)."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel

GuardrailKind = Literal["allow", "refusal", "escalation"]
EscalationReason = Literal[
    "out_of_scope",
    "low_confidence",
    "requires_legal_advice",
    "unsupported_request",
]


class GuardrailResult(BaseModel):
    kind: GuardrailKind
    escalation_reason: EscalationReason | None = None
    message: str | None = None


_ADVICE_PATTERNS = [
    re.compile(r"\bshould i\b", re.I),
    re.compile(r"\bwhat should i do\b", re.I),
    re.compile(r"\badvise me\b", re.I),
    re.compile(r"\blegal advice\b", re.I),
    re.compile(r"\bwill i (be )?(approved|rejected)\b", re.I),
    re.compile(r"\bguarantee\b", re.I),
]

_REFUSAL_TEXT = (
    "I can share published procedural information and official requirements, "
    "but I cannot give legal advice or tell you what you should do in your situation. "
    "For strategy or judgment calls, please consult a licensed professional."
)


def classify_user_message(message: str) -> GuardrailResult:
    """Heuristic gate before retrieval/generation (US-15.3)."""
    text = message.strip()
    if not text:
        return GuardrailResult(
            kind="refusal",
            message="Please ask a procedural question about visas, forms, or documents.",
        )
    for pattern in _ADVICE_PATTERNS:
        if pattern.search(text):
            return GuardrailResult(
                kind="refusal",
                message=_REFUSAL_TEXT,
            )
    return GuardrailResult(kind="allow")
