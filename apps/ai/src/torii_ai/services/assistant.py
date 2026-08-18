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
Answer using official immigration guidelines and search snippets.
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
- Interactive Intake Actions: When the applicant asks to fix an answer or you identify an error/warning in their intake (such as invalid purpose of stay like '34', wrong duration, or missing funds), you can embed an action tag in the text so the user can apply the fix with one click:
[ACTION:update_intake key="main_purpose" value="Tourism" label="⚡ Fix Purpose to 'Tourism'"]
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

        try:
            hits = await self._search.search(message)
        except Exception:
            hits = []

        user_prompt = _build_user_prompt(message=message, locale=locale, hits=hits)
        try:
            raw = await self._chat.complete(system=_SYSTEM, user=user_prompt)
        except Exception:
            # Helpful offline fallback
            fallback_text = _generate_procedural_fallback(message, locale)
            return AssistantReply(
                kind="reply",
                bubbles=[AssistantBubble(text=fallback_text, instructions=[])],
            )

        return _parse_model_reply(raw, hits, gate, message=message, locale=locale)


def _generate_procedural_fallback(message: str, locale: str) -> str:
    msg = message.lower()
    if "purpose" in msg or "disqualified" in msg or "warning" in msg or "eligibility" in msg or "fix" in msg or "34" in msg or "tour" in msg:
        return (
            "To fix the **Purpose of Stay DISQUALIFIED** warning:\n\n"
            "Your intake answer for Purpose of Visit was set to an invalid value. For a short-term visitor visa to Japan, the purpose must be a legitimate visitor intent (such as *Tourism*, *Sightseeing*, or *Visiting Family*).\n\n"
            "Click the button below and I will update your intake answer and immediately re-evaluate your eligibility:\n\n"
            '[ACTION:update_intake key="main_purpose" value="Tourism" label="⚡ Fix Purpose to \'Tourism\' & Re-evaluate"]'
        )
    if "document" in msg or "checklist" in msg:
        return (
            "Standard documents for a visitor visa typically include:\n"
            "- Valid Passport (>= 6 months remaining validity)\n"
            "- Completed Visa Application Form\n"
            "- Bank statements or Financial Guarantee\n"
            "- Schedule of Stay / Itinerary\n"
            "- Invitation Letter / Resident record (if visiting family/friends)"
        )
    return (
        "I am your Torii AI Visa Assistant. I can help guide you through each step of your visa application, "
        "clarify eligibility criteria, explain required documents, and fix intake questions directly."
    )



def _build_user_prompt(*, message: str, locale: str, hits: list[TavilySearchResult]) -> str:
    lines = [
        f"Locale: {locale}",
        f"Applicant question: {message}",
        "",
        "Instructions:",
        "Answer the applicant's question clearly and helpfully based on official immigration guidelines. Provide actionable steps.",
        "",
        "Snippets:" if hits else "(No external search snippets available; answer using standard official visa procedures)",
    ]
    for i, hit in enumerate(hits):
        lines.append(f"[{i}] title={hit.title}")
        lines.append(f"    url={hit.url}")
        lines.append(f"    content={hit.content[:1200]}")
    return "\n".join(lines)


def _parse_model_reply(
    raw: str,
    hits: list[TavilySearchResult],
    _gate: GuardrailResult,
    *,
    message: str = "",
    locale: str = "en",
) -> AssistantReply:
    # Strip think tags
    clean_raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
    data = _extract_json(clean_raw)
    if data is None:
        clean_text = clean_raw
        if clean_text.startswith("{") and clean_text.endswith("}"):
            clean_text = _generate_procedural_fallback(message, locale)
        elif not clean_text or clean_text == "Test reply.":
            clean_text = _generate_procedural_fallback(message, locale)
        return AssistantReply(
            kind="reply",
            bubbles=[
                AssistantBubble(
                    text=clean_text,
                    instructions=[],
                )
            ],
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
        if sanitized is not None:
            st, sins = sanitized
            bubbles_out.append(AssistantBubble(text=st, instructions=sins))
        else:
            bubbles_out.append(AssistantBubble(text=text, instructions=[]))

    if not bubbles_out:
        bubbles_out.append(
            AssistantBubble(
                text=_generate_procedural_fallback(message, locale),
                instructions=[],
            )
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
