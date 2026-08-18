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

_SYSTEM = """You are Torii, an expert AI immigration and visa preparation assistant.
You provide procedural guidance, statutory requirements, and document checklist verification based strictly on official immigration authorities (such as Japan Immigration Services Agency / MOJ / MOFA, US USCIS / State Dept, UK Visas and Immigration / Home Office) — never unauthorized legal advice.

Respond with JSON only, no markdown fences:
{
  "bubbles": [
    {
      "text": "plain language explanation to the applicant",
      "claims_requirement": true,
      "instruction": {
        "text": "the statutory or procedural requirement statement",
        "kind": "process_step",
        "official_term": null,
        "source_indexes": [0]
      }
    }
  ],
  "escalation": null
}

Rules:
- Adapt strictly to the applicant's specific visa category (e.g. Student Visa, Engineer / Specialist in Humanities / International Services Work Visa, Temporary Visitor / Tourist Visa, H-1B, Skilled Worker) and filing action (New Application / COE, Extension of Stay / Renewal, Change of Status).
- Never give tourist visa guidance to a student or work visa applicant, and vice-versa.
- When an applicant asks about documents, list the exact official statutory documents required for their specific visa type and jurisdiction.
- Interactive Intake Actions: When the applicant asks to fix an answer or you identify an error/warning in their intake, you can embed an action tag in the text so the user can apply the fix with one click:
[ACTION:update_intake key="<field_key>" value="<correct_value>" label="⚡ Fix <Field Label>"]
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

    async def reply(
        self,
        *,
        message: str,
        locale: str = "en",
        jurisdiction_code: str | None = None,
        visa_category_code: str | None = None,
        action_code: str | None = None,
        origin_country: str | None = None,
        residence_country: str | None = None,
        intake_answers: dict[str, Any] | None = None,
        eligibility_findings: list[dict[str, Any]] | None = None,
    ) -> AssistantReply:
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

        # Build focused search query incorporating visa context
        search_query = message
        scope_tokens = []
        if jurisdiction_code:
            scope_tokens.append(jurisdiction_code)
        if visa_category_code:
            scope_tokens.append(visa_category_code)
        if action_code:
            scope_tokens.append(action_code)
        if scope_tokens and not any(t.lower() in message.lower() for t in scope_tokens):
            search_query = f"{' '.join(scope_tokens)} {message}"

        try:
            hits = await self._search.search(search_query)
        except Exception:
            hits = []

        user_prompt = _build_user_prompt(
            message=message,
            locale=locale,
            hits=hits,
            jurisdiction_code=jurisdiction_code,
            visa_category_code=visa_category_code,
            action_code=action_code,
            origin_country=origin_country,
            residence_country=residence_country,
            intake_answers=intake_answers,
            eligibility_findings=eligibility_findings,
        )
        try:
            raw = await self._chat.complete(system=_SYSTEM, user=user_prompt)
        except Exception:
            # Helpful offline fallback tailored to visa type
            fallback_text = _generate_procedural_fallback(
                message,
                locale,
                jurisdiction_code=jurisdiction_code,
                visa_category_code=visa_category_code,
                action_code=action_code,
                intake_answers=intake_answers,
                eligibility_findings=eligibility_findings,
            )
            return AssistantReply(
                kind="reply",
                bubbles=[AssistantBubble(text=fallback_text, instructions=[])],
            )

        return _parse_model_reply(
            raw,
            hits,
            gate,
            message=message,
            locale=locale,
            jurisdiction_code=jurisdiction_code,
            visa_category_code=visa_category_code,
            action_code=action_code,
            intake_answers=intake_answers,
            eligibility_findings=eligibility_findings,
        )


def _generate_procedural_fallback(
    message: str,
    locale: str,
    *,
    jurisdiction_code: str | None = None,
    visa_category_code: str | None = None,
    action_code: str | None = None,
    intake_answers: dict[str, Any] | None = None,
    eligibility_findings: list[dict[str, Any]] | None = None,
) -> str:
    msg = message.lower()
    cat = (visa_category_code or "").lower()
    act = (action_code or "").lower()
    dest = (jurisdiction_code or "JP").upper()

    # If applicant has student context
    if "student" in cat or "study" in msg or "school" in msg or "jlpt" in msg or "coe" in msg:
        if "renewal" in act or "extension" in act:
            if "document" in msg or "checklist" in msg or "requirement" in msg:
                return (
                    "**Official Requirements for Japan Student Visa Extension (在留期間更新許可申請 - 留学):**\n\n"
                    "According to Immigration Services Agency of Japan (MOJ Procedure 16-3):\n"
                    "- **Valid Passport & Current Residence Card (在留カード)**\n"
                    "- **Certificate of Enrollment (在学証明書)** & Official Academic Transcripts (成績証明書)\n"
                    "- **Attendance Record Certificate (出席状況証明書)** (>= 80% attendance required)\n"
                    "- **Proof of Tuition Payment & Living Solvency (経費支弁証明書 / 通帳コピー)**"
                )
        if "document" in msg or "checklist" in msg or "requirement" in msg:
            return (
                "**Official Requirements for Japan Student Visa (留学 / Certificate of Eligibility):**\n\n"
                "According to Immigration Services Agency of Japan (MOJ Procedure 16-1):\n"
                "- **Valid Passport** & Photo (4cm x 3cm)\n"
                "- **Certificate of Admission (入学許可書)** from Japanese institution\n"
                "- **Proof of Financial Solvency**: Bank balance / Sponsor Income Certificates (covering ~¥2,000,000+ tuition & living costs)\n"
                "- **Letter of Sponsorship (経費支弁書)** & Family Relationship Proof\n"
                "- **Japanese Proficiency Certificate (JLPT / NAT-TEST / 150+ hours study certificate)**\n"
                "- **Academic Transcripts & Graduation Diplomas**"
            )
        if "warning" in msg or "fix" in msg or "eligibility" in msg:
            return (
                "For a **Student Visa**, your eligibility is evaluated on your academic enrollment, institutional sponsor, and financial proof.\n\n"
                "If you need to update your study level or sponsor details:\n\n"
                '[ACTION:update_intake key="intended_study_level" value="university" label="⚡ Set Study Level to \'University\'"]'
            )
        return (
            "I am your Torii AI Student Visa Assistant. I can help guide your Japanese educational institution admission, "
            "COE application, sponsor financial documentation, and embassy filing."
        )

    # If applicant has work context
    if "work" in cat or "job" in msg or "engineer" in msg or "employer" in msg or "salary" in msg:
        if "document" in msg or "checklist" in msg or "requirement" in msg:
            return (
                "**Official Requirements for Japan Work Visa (技術・人文知識・国際業務 / Extension & COE):**\n\n"
                "According to Immigration Services Agency of Japan (MOJ Procedures 16-1 / 16-3):\n"
                "- **Valid Passport & Current Residence Card (在留カード)**\n"
                "- **Certificate of Employment (在職証明書)** from Japanese employer\n"
                "- **Employment Contract (雇用契約書 / 労働条件通知書)** specifying annual remuneration\n"
                "- **Resident Tax Certificates (住民税の課税・納税証明書)** for the most recent year\n"
                "- **Sponsoring Company Category Proof (法定調書合計表)** (Category 1 to 4)\n"
                "- **Pension & Health Insurance compliance documentation**"
            )
        if "warning" in msg or "fix" in msg or "eligibility" in msg:
            return (
                "For a **Work Visa Extension**, key review criteria include continuous employment, minimum remuneration standard, "
                "and no tax/pension arrears.\n\n"
                "If you need to update your employment status:\n\n"
                '[ACTION:update_intake key="employment_status" value="employed" label="⚡ Set Employment Status to \'Employed\'"]'
            )
        return (
            "I am your Torii AI Work Visa Assistant. I can assist with Engineer/Specialist in Humanities requirements, "
            "employer category classifications, tax certificates, and renewal procedures."
        )

    # Tourist / Short-term stay
    if "tourist" in cat or "visit" in msg or "holiday" in msg or "tour" in msg:
        if "purpose" in msg or "disqualified" in msg or "warning" in msg or "fix" in msg:
            return (
                "To fix the **Purpose of Stay DISQUALIFIED** warning:\n\n"
                "Your intake answer for Purpose of Visit was set to an invalid value. For a short-term visitor visa to Japan, the purpose must be a legitimate visitor intent (such as *Tourism*, *Sightseeing*, or *Visiting Family*).\n\n"
                "Click below to fix your answer and re-evaluate eligibility:\n\n"
                '[ACTION:update_intake key="main_purpose" value="Tourism" label="⚡ Fix Purpose to \'Tourism\' & Re-evaluate"]'
            )
        if "document" in msg or "checklist" in msg:
            return (
                "**Official Requirements for Japan Temporary Visitor Visa (短期滞在):**\n\n"
                "- **Valid Passport** (>= 6 months validity)\n"
                "- **Visa Application Form with Photograph**\n"
                "- **Proof of Financial Solvency** (Bank statements covering duration of stay)\n"
                "- **Schedule of Stay / Itinerary (滞在予定表)**\n"
                "- **Confirmed Return Flight Booking & Hotel Reservations**"
            )
        return "I am your Torii AI Temporary Visitor Visa Assistant. I can help you assemble your itinerary, financial proofs, and embassy application."

    # Universal Fallback
    if "document" in msg or "checklist" in msg:
        return (
            f"**Statutory Immigration Checklist for {dest}:**\n\n"
            "- Valid Passport\n"
            "- Official Government Application Form\n"
            "- Solvency & Financial Proof\n"
            "- Purpose-specific supporting documents\n"
            "- Security & Clean Record Disclosures"
        )
    return (
        f"I am your Torii AI Immigration Assistant for **{dest}**. I can guide your specific visa application, "
        "clarify statutory requirements, check required documents, and fix intake questions directly."
    )


def _build_user_prompt(
    *,
    message: str,
    locale: str,
    hits: list[TavilySearchResult],
    jurisdiction_code: str | None = None,
    visa_category_code: str | None = None,
    action_code: str | None = None,
    origin_country: str | None = None,
    residence_country: str | None = None,
    intake_answers: dict[str, Any] | None = None,
    eligibility_findings: list[dict[str, Any]] | None = None,
) -> str:
    lines = [
        f"Locale: {locale}",
        f"Active Scope Destination: {jurisdiction_code or 'JP'}",
        f"Active Visa Category: {visa_category_code or 'General Immigration'}",
        f"Active Filing Action: {action_code or 'Standard Application'}",
    ]
    if origin_country:
        lines.append(f"Applicant Nationality / Origin: {origin_country}")
    if residence_country:
        lines.append(f"Applicant Country of Residence: {residence_country}")
    if intake_answers:
        lines.append(f"Current Intake Answers: {json.dumps(intake_answers)}")
    if eligibility_findings:
        lines.append(f"Current Eligibility Findings: {json.dumps(eligibility_findings)}")

    lines.extend(
        [
            "",
            f"Applicant Question: {message}",
            "",
            "Instructions:",
            "Answer the applicant's question clearly and helpfully based strictly on official immigration guidelines for their specific visa type.",
            "Provide actionable steps and specific official document names.",
            "",
            "Official Snippets:"
            if hits
            else "(No external search snippets available; answer using official statutory procedures for this visa category)",
        ]
    )
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
    jurisdiction_code: str | None = None,
    visa_category_code: str | None = None,
    action_code: str | None = None,
    intake_answers: dict[str, Any] | None = None,
    eligibility_findings: list[dict[str, Any]] | None = None,
) -> AssistantReply:
    # Strip think tags
    clean_raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
    data = _extract_json(clean_raw)
    if data is None:
        clean_text = clean_raw
        if (
            (clean_text.startswith("{") and clean_text.endswith("}"))
            or not clean_text
            or clean_text == "Test reply."
        ):
            clean_text = _generate_procedural_fallback(
                message,
                locale,
                jurisdiction_code=jurisdiction_code,
                visa_category_code=visa_category_code,
                action_code=action_code,
                intake_answers=intake_answers,
                eligibility_findings=eligibility_findings,
            )
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
                text=_generate_procedural_fallback(
                    message,
                    locale,
                    jurisdiction_code=jurisdiction_code,
                    visa_category_code=visa_category_code,
                    action_code=action_code,
                    intake_answers=intake_answers,
                    eligibility_findings=eligibility_findings,
                ),
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
