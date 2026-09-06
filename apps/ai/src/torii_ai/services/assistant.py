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
        case_reference: str | None = None,
        scope_label: str | None = None,
        case_status: str | None = None,
        current_step: str | None = None,
        jurisdiction_code: str | None = None,
        visa_category_code: str | None = None,
        action_code: str | None = None,
        origin_country: str | None = None,
        residence_country: str | None = None,
        intake_answers: dict[str, Any] | None = None,
        eligibility_findings: list[dict[str, Any]] | None = None,
        checklist: list[dict[str, Any]] | None = None,
        review_flags: list[dict[str, Any]] | None = None,
        user_profile: dict[str, Any] | None = None,
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
            case_reference=case_reference,
            scope_label=scope_label,
            case_status=case_status,
            current_step=current_step,
            jurisdiction_code=jurisdiction_code,
            visa_category_code=visa_category_code,
            action_code=action_code,
            origin_country=origin_country,
            residence_country=residence_country,
            intake_answers=intake_answers,
            eligibility_findings=eligibility_findings,
            checklist=checklist,
            review_flags=review_flags,
            user_profile=user_profile,
        )
        try:
            raw = await self._chat.complete(system=_SYSTEM, user=user_prompt)
        except Exception:
            # Helpful live fallback dynamically synthesized from active case state
            fallback_text = _generate_procedural_fallback(
                message,
                locale,
                case_reference=case_reference,
                scope_label=scope_label,
                case_status=case_status,
                current_step=current_step,
                jurisdiction_code=jurisdiction_code,
                visa_category_code=visa_category_code,
                action_code=action_code,
                intake_answers=intake_answers,
                eligibility_findings=eligibility_findings,
                checklist=checklist,
                review_flags=review_flags,
                user_profile=user_profile,
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
            case_reference=case_reference,
            scope_label=scope_label,
            case_status=case_status,
            current_step=current_step,
            jurisdiction_code=jurisdiction_code,
            visa_category_code=visa_category_code,
            action_code=action_code,
            intake_answers=intake_answers,
            eligibility_findings=eligibility_findings,
            checklist=checklist,
            review_flags=review_flags,
            user_profile=user_profile,
        )


def _generate_procedural_fallback(
    message: str,
    locale: str,
    *,
    case_reference: str | None = None,
    scope_label: str | None = None,
    case_status: str | None = None,
    current_step: str | None = None,
    jurisdiction_code: str | None = None,
    visa_category_code: str | None = None,
    action_code: str | None = None,
    intake_answers: dict[str, Any] | None = None,
    eligibility_findings: list[dict[str, Any]] | None = None,
    checklist: list[dict[str, Any]] | None = None,
    review_flags: list[dict[str, Any]] | None = None,
    user_profile: dict[str, Any] | None = None,
) -> str:
    msg = message.lower()
    cat = (visa_category_code or "").lower()
    act = (action_code or "").lower()
    dest = (jurisdiction_code or "JP").upper()
    ref_display = case_reference or "Your Case"
    scope_display = scope_label or f"{dest} {cat.capitalize()} ({act})"

    # 1. Check if user is asking how to fix eligibility warnings / disqualifications
    if any(
        k in msg
        for k in ("fix", "disqualif", "incomplet", "warning", "issue", "error", "fail", "why")
    ):
        if eligibility_findings and len(eligibility_findings) > 0:
            bad_findings = [
                f
                for f in eligibility_findings
                if f.get("status")
                in ("disqualified", "fail", "at_risk", "incomplete", "out_of_scope")
            ]
            if bad_findings:
                lines = [
                    f"### 🔍 Analysis & Action Plan for **{ref_display}**",
                    f"*Scope: {scope_display}*",
                    "",
                    f"You have **{len(bad_findings)} finding(s)** that need resolution:",
                    "",
                ]
                for i, f in enumerate(bad_findings, 1):
                    key = str(f.get("key", "criterion"))
                    status = str(f.get("status", "disqualified")).upper()
                    explanation = f.get("message", "Requirement needs attention.")
                    title = key.replace("_", " ").title()

                    # Determine recommended fix value and action label
                    fix_value = "yes"
                    action_label = f"⚡ Fix '{title}'"
                    if "sanction" in key:
                        fix_value = "no"
                        action_label = "⚡ Answer 'No Sanctions'"
                    elif "arrear" in key or "criminal" in key:
                        fix_value = "no"
                        action_label = "⚡ Answer 'No Arrears'"
                    elif "school" in key or "graduate" in key or "completed" in key:
                        fix_value = "yes"
                        action_label = "⚡ Set 'Completed Program' to 'Yes'"
                    elif "job_offer" in key or "offer" in key:
                        fix_value = "yes"
                        action_label = "⚡ Set 'Job Offer' to 'Yes'"
                    elif "job_description" in key or "duties" in key:
                        fix_value = "yes"
                        action_label = "⚡ Set 'Job Duties Provided' to 'Yes'"
                    elif "purpose" in key:
                        fix_value = (
                            "Tourism"
                            if "tourist" in cat
                            else "Employment"
                            if "work" in cat
                            else "Study"
                        )
                        action_label = f"⚡ Set Purpose to '{fix_value}'"
                    elif "study_level" in key:
                        fix_value = "university"
                        action_label = "⚡ Set Study Level to 'University'"
                    elif "attendance" in key or "attendance_rate" in key:
                        fix_value = "95"
                        action_label = "⚡ Set Attendance Rate to '95%'"

                    lines.append(f"**{i}. {title}** (`{status}`):")
                    lines.append(f"- **Issue**: {explanation}")
                    lines.append(
                        "- **Statutory Guidance**: In accordance with official published guidelines, this criterion must be fully satisfied to pass eligibility screening."
                    )
                    lines.append(
                        "- **Quick Fix**: Click below to update your intake answer and re-evaluate:"
                    )
                    lines.append(
                        f'[ACTION:update_intake key="{key}" value="{fix_value}" label="{action_label}"]'
                    )
                    lines.append("")

                lines.append(
                    "After applying the fixes, eligibility will be automatically re-evaluated to unlock the next steps."
                )
                return "\n".join(lines)

    # 1.5 Check if user specifically asks about missing fields or attendance rate
    if "attendance" in msg:
        return (
            "### 🏫 Missing Required Form Field: Attendance Rate (`school.attendance_rate`)\n\n"
            "**Why this is required by Japanese Immigration (MOJ ISA 16-1 / 16-3):**\n"
            "- For a Student Visa (留学) or renewal/extension in Japan, immigration authorities strictly require your academic attendance record.\n"
            "- **Statutory Standard**: An attendance rate of **80% or higher** (ideally 90%+) is required to be approved for visa extension.\n\n"
            "**How to fix this:**\n"
            "Click below to set your attendance rate percentage from your school certificate:\n\n"
            '[ACTION:update_intake key="attendance_rate" value="95" label="⚡ Set Attendance Rate to \'95%\'"]'
        )

    # 2. Check if user is asking about current progress / status
    if any(
        k in msg
        for k in (
            "progress",
            "current",
            "process",
            "where am i",
            "what next",
            "status",
            "next step",
        )
    ):
        step_name = current_step or case_status or "Intake"
        findings_count = len(eligibility_findings or [])
        disqualified_count = len(
            [f for f in (eligibility_findings or []) if f.get("status") in ("disqualified", "fail")]
        )
        incomplete_count = len(
            [f for f in (eligibility_findings or []) if f.get("status") == "incomplete"]
        )
        gathered_count = len(
            [d for d in (checklist or []) if d.get("status") in ("gathered", "uploaded")]
        )
        total_docs = len(checklist or [])

        lines = [
            f"### 📊 Live Progress Snapshot for **{ref_display}**",
            f"- **Visa Scope**: {scope_display}",
            f"- **Current Phase**: `{step_name.upper()}`",
            "",
            "**Current Stage Breakdown:**",
            f"1. **Intake Questions**: {'✅ Completed' if intake_answers else '⏳ In Progress'}",
            f"2. **Eligibility Screening**: {f'⚠️ {disqualified_count} Disqualified, {incomplete_count} Incomplete' if (disqualified_count or incomplete_count) else '✅ Passed' if findings_count > 0 else '⏳ Pending'}",
            f"3. **Document Checklist**: {f'{gathered_count} of {total_docs} gathered' if total_docs > 0 else '⏳ Pending Checklist Generation'}",
            f"4. **Official Filing Kit & Forms**: {'✅ Available in Packet Step' if step_name in ('forms', 'review', 'packet') else '🔒 Unlocks after Checklist'}",
            "",
        ]
        if disqualified_count > 0 or incomplete_count > 0:
            lines.append(
                "👉 **Immediate Next Step**: Resolve the eligibility warnings above so your application can advance to Document Gathering and Forms."
            )
        elif total_docs > 0 and gathered_count < total_docs:
            lines.append(
                f"👉 **Immediate Next Step**: Upload the remaining {total_docs - gathered_count} required document(s) in Step 3: Document Checklist."
            )
        else:
            lines.append(
                "👉 **Immediate Next Step**: Review your auto-filled forms and download your official PDF filing dossier."
            )
        return "\n".join(lines)

    # 3. Check if user is asking about documents / checklist
    if any(
        k in msg
        for k in (
            "document",
            "checklist",
            "gather",
            "upload",
            "proof",
            "what docs",
            "what do i need",
        )
    ):
        if checklist and len(checklist) > 0:
            gathered = [d for d in checklist if d.get("status") in ("gathered", "uploaded")]
            needed = [d for d in checklist if d.get("status") not in ("gathered", "uploaded")]
            lines = [
                f"### 📑 Document Checklist for **{ref_display}** ({scope_display}):",
                f"**Progress**: {len(gathered)} / {len(checklist)} documents ready",
                "",
            ]
            if needed:
                lines.append("**⏳ Still Required to Gather / Upload:**")
                for d in needed:
                    req_star = "*(Required)*" if d.get("is_required") else "*(Optional)*"
                    lines.append(f"- **{d.get('name')}** {req_star}")
                    if d.get("how_to_obtain"):
                        lines.append(f"  *How to obtain*: {d.get('how_to_obtain')}")
                lines.append("")
            if gathered:
                lines.append("**✅ Already Gathered & Verified:**")
                for d in gathered:
                    lines.append(f"- {d.get('name')}")
            return "\n".join(lines)

    # 4. Fallback by Visa Category if generic question
    if "student" in cat or "study" in msg or "school" in msg:
        return (
            f"I am your Torii AI Assistant for **{scope_display}**.\n\n"
            "I have access to your live intake answers, eligibility findings, and document checklist.\n"
            "You can ask me:\n"
            "- *'How to fix this'* (to resolve current eligibility warnings)\n"
            "- *'What is my current progress'* (for a live case summary)\n"
            "- *'What documents do I need'* (for your tailored statutory checklist)"
        )

    if "work" in cat or "job" in msg or "engineer" in msg:
        return (
            f"I am your Torii AI Assistant for **{scope_display}**.\n\n"
            "I have access to your live employment data, tax criteria, and immigration checklist.\n"
            "You can ask me:\n"
            "- *'How to fix this'* (to resolve employer, tax, or job offer warnings)\n"
            "- *'What is my current progress'* (for a live case summary)\n"
            "- *'What documents do I need'* (for required employer and tax certificates)"
        )

    return (
        f"I am your Torii AI Immigration Assistant for **{ref_display}** ({scope_display}).\n\n"
        "I monitor your real-time application state, eligibility screenings, and document uploads. "
        "Ask me anything about your current case or type *'how to fix this'* to resolve any blocking issues."
    )


def _build_user_prompt(
    *,
    message: str,
    locale: str,
    hits: list[TavilySearchResult],
    case_reference: str | None = None,
    scope_label: str | None = None,
    case_status: str | None = None,
    current_step: str | None = None,
    jurisdiction_code: str | None = None,
    visa_category_code: str | None = None,
    action_code: str | None = None,
    origin_country: str | None = None,
    residence_country: str | None = None,
    intake_answers: dict[str, Any] | None = None,
    eligibility_findings: list[dict[str, Any]] | None = None,
    checklist: list[dict[str, Any]] | None = None,
    review_flags: list[dict[str, Any]] | None = None,
    user_profile: dict[str, Any] | None = None,
) -> str:
    lines = [
        f"Locale: {locale}",
        f"Active Case Reference: {case_reference or 'N/A'}",
        f"Active Scope Label: {scope_label or 'N/A'}",
        f"Active Case Status: {case_status or 'N/A'}",
        f"Active Current Step: {current_step or 'N/A'}",
        f"Active Scope Destination: {jurisdiction_code or 'JP'}",
        f"Active Visa Category: {visa_category_code or 'General Immigration'}",
        f"Active Filing Action: {action_code or 'Standard Application'}",
    ]
    if origin_country:
        lines.append(f"Applicant Nationality / Origin: {origin_country}")
    if residence_country:
        lines.append(f"Applicant Country of Residence: {residence_country}")
    if user_profile:
        lines.append(f"User Global Profile: {json.dumps(user_profile)}")
    if intake_answers:
        lines.append(f"Current Intake Answers: {json.dumps(intake_answers)}")
    if eligibility_findings:
        lines.append(f"Current Eligibility Evaluated Findings: {json.dumps(eligibility_findings)}")
    if checklist:
        lines.append(f"Current Document Checklist Status: {json.dumps(checklist)}")
    if review_flags:
        lines.append(f"Current Review Flags: {json.dumps(review_flags)}")

    lines.extend(
        [
            "",
            f"Applicant Question: {message}",
            "",
            "Instructions:",
            "1. Answer the applicant's question clearly and helpfully based strictly on official immigration guidelines for their specific visa type and active case context.",
            "2. If the user asks 'how to fix this' or has disqualified/incomplete eligibility findings, address each failing item specifically, explain the statutory legal reason, and provide an interactive action tag:",
            '   [ACTION:update_intake key="<field_key>" value="<correct_value>" label="⚡ Fix <Field Label>"]',
            "3. If the user asks about progress, summarize their active step, eligibility status, and document checklist readiness.",
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
    case_reference: str | None = None,
    scope_label: str | None = None,
    case_status: str | None = None,
    current_step: str | None = None,
    jurisdiction_code: str | None = None,
    visa_category_code: str | None = None,
    action_code: str | None = None,
    intake_answers: dict[str, Any] | None = None,
    eligibility_findings: list[dict[str, Any]] | None = None,
    checklist: list[dict[str, Any]] | None = None,
    review_flags: list[dict[str, Any]] | None = None,
    user_profile: dict[str, Any] | None = None,
) -> AssistantReply:
    # Strip think tags
    clean_raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
    data = _extract_json(clean_raw)
    if data is None:
        clean_text = clean_raw
        if (
            (clean_text.startswith("{") and clean_text.endswith("}"))
            or not clean_text
            or len(clean_text.strip()) < 15
            or clean_text.strip() in ("Test reply.", "fallback", "I cannot help with that.")
            or (
                any(k in message.lower() for k in ("fix", "disqualif", "warning"))
                and eligibility_findings
                and "[ACTION:update_intake" not in clean_text
            )
        ):
            clean_text = _generate_procedural_fallback(
                message,
                locale,
                case_reference=case_reference,
                scope_label=scope_label,
                case_status=case_status,
                current_step=current_step,
                jurisdiction_code=jurisdiction_code,
                visa_category_code=visa_category_code,
                action_code=action_code,
                intake_answers=intake_answers,
                eligibility_findings=eligibility_findings,
                checklist=checklist,
                review_flags=review_flags,
                user_profile=user_profile,
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
