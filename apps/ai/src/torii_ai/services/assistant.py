"""Grounded assistant — search, generate, cite, guardrail (US-14/11/12/15)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from torii_ai.citations.engine import sanitize_bubble
from torii_ai.citations.models import Instruction
from torii_ai.guardrails.policy import GuardrailResult, classify_user_message
from torii_ai.llm.groq import ChatClient
from torii_ai.tools.tavily import SearchClient, TavilySearchResult

_SYSTEM = """You are Torii, a guided immigration form-preparation assistant.
You give procedural INFORMATION from official sources only — never legal advice.
Answer ONLY using the provided search snippets. If snippets are insufficient, say so plainly.
Respond with JSON only, no markdown fences:
{
  "bubbles": [
    {
      "text": "plain language to the applicant",
      "claims_requirement": true,
      "instruction": {
        "text": "the requirement statement",
        "kind": "process_step",
        "official_term": null,
        "source_indexes": [0]
      }
    }
  ],
  "escalation": null
}
Rules:
- claims_requirement true ONLY when stating a form/document/eligibility/process requirement.
- source_indexes refer to the numbered snippets (0-based). Omit instruction if conversational.
- escalation may be "low_confidence" or "out_of_scope" or null.
- Never invent URLs or authorities not present in snippets.
"""


@dataclass
class AssistantBubble:
    text: str
    instructions: list[Instruction]


@dataclass
class AssistantReply:
    kind: str  # reply | escalation | refusal
    bubbles: list[AssistantBubble]
    escalation_reason: str | None = None


class AssistantService:
    def __init__(self, *, chat: ChatClient, search: SearchClient) -> None:
        self._chat = chat
        self._search = search

    async def reply(self, *, message: str, locale: str = "en") -> AssistantReply:
        gate = classify_user_message(message)
        if gate.kind == "refusal":
            return AssistantReply(
                kind="refusal",
                bubbles=[
                    AssistantBubble(
                        text=gate.message or "I cannot help with that.",
                        instructions=[],
                    )
                ],
            )

        hits = await self._search.search(message)
        if not hits:
            return AssistantReply(
                kind="escalation",
                bubbles=[
                    AssistantBubble(
                        text=(
                            "I could not find grounded official sources for that "
                            "question right now. Try rephrasing, or ask a licensed "
                            "professional for case-specific help."
                        ),
                        instructions=[],
                    )
                ],
                escalation_reason="low_confidence",
            )

        user_prompt = _build_user_prompt(message=message, locale=locale, hits=hits)
        raw = await self._chat.complete(system=_SYSTEM, user=user_prompt)
        return _parse_model_reply(raw, hits, gate)


def _build_user_prompt(*, message: str, locale: str, hits: list[TavilySearchResult]) -> str:
    lines = [f"Locale: {locale}", f"Applicant question: {message}", "", "Snippets:"]
    for i, hit in enumerate(hits):
        lines.append(f"[{i}] title={hit.title}")
        lines.append(f"    url={hit.url}")
        lines.append(f"    content={hit.content[:1200]}")
    return "\n".join(lines)


def _parse_model_reply(
    raw: str, hits: list[TavilySearchResult], _gate: GuardrailResult
) -> AssistantReply:
    data = _extract_json(raw)
    if data is None:
        return AssistantReply(
            kind="escalation",
            bubbles=[
                AssistantBubble(
                    text="I could not produce a grounded answer. Please try again.",
                    instructions=[],
                )
            ],
            escalation_reason="low_confidence",
        )

    escalation = data.get("escalation")
    bubbles_out: list[AssistantBubble] = []
    for item in data.get("bubbles") or []:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text") or "").strip()
        if not text:
            continue
        claims = bool(item.get("claims_requirement"))
        instructions: list[Instruction] = []
        instr = item.get("instruction")
        if isinstance(instr, dict) and claims:
            built = _instruction_from_model(instr, hits)
            if built is not None:
                instructions.append(built)
        sanitized = sanitize_bubble(text=text, instructions=instructions, claims_requirement=claims)
        if sanitized is None:
            continue
        st, sins = sanitized
        bubbles_out.append(AssistantBubble(text=st, instructions=sins))

    if not bubbles_out:
        return AssistantReply(
            kind="escalation",
            bubbles=[
                AssistantBubble(
                    text=(
                        "I could not cite official sources for a requirement-level answer, "
                        "so I am not showing unverified guidance."
                    ),
                    instructions=[],
                )
            ],
            escalation_reason="low_confidence",
        )

    kind = "escalation" if escalation else "reply"
    reason = str(escalation) if escalation else None
    return AssistantReply(kind=kind, bubbles=bubbles_out, escalation_reason=reason)


def _instruction_from_model(
    instr: dict[str, Any], hits: list[TavilySearchResult]
) -> Instruction | None:
    text = str(instr.get("text") or "").strip()
    if not text:
        return None
    indexes = instr.get("source_indexes") or []
    sources = []
    for idx in indexes:
        if isinstance(idx, int) and 0 <= idx < len(hits):
            sources.append(hits[idx].citation)
    if not sources:
        return None
    kind = instr.get("kind") or "process_step"
    if kind not in {
        "form_requirement",
        "field_help",
        "document_requirement",
        "eligibility",
        "process_step",
        "timeline",
    }:
        kind = "process_step"
    official = instr.get("official_term")
    return Instruction(
        text=text,
        kind=kind,
        official_term=str(official) if official else None,
        sources=sources,
    )


def _extract_json(raw: str) -> dict[str, Any] | None:
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            data = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return None
    return data if isinstance(data, dict) else None
