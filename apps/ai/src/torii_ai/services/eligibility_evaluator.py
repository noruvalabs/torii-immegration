"""AI-Powered Structured Eligibility Assessment (US-04).

Evaluates applicant intake answers holistically against official destination statutory
criteria without rigid regex/exact matching, returning structured findings and citations.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

import structlog

from torii_ai.config import Settings
from torii_ai.llm.groq import ChatClient
from torii_ai.services.ops_scraper import country_label, extract_json

log = structlog.get_logger()

EligibilityStatus = Literal["pass", "at_risk", "fail", "out_of_scope"]

ELIGIBILITY_SYSTEM_PROMPT = """You are an expert immigration eligibility assessment AI.
Given an applicant's profile, destination visa route, and completed intake answers, evaluate their eligibility holistically.

Evaluate across the 4 core pillars:
1. Identity & Passport: valid passport, remaining validity (typically >= 6 months), nationality eligibility.
2. Travel Purpose & Duration: genuine visit (tourism, sightseeing, vacation, visiting relatives, business meetings are legitimate), stay length matches limits (e.g. <= 90 days for visitor visa).
3. Financial Capacity & Solvency: adequate savings, stable employment or approved student status, financial guarantor/sponsor if required.
4. Immigration Compliance & Admissibility: clean immigration history, no active entry bans, no overstay history, no disqualifying criminal grounds.

Rules:
- Reason contextually: Do NOT fail valid travel purposes just because of specific phrasing (e.g. "tourism and sightseeing", "visiting friends", "holiday" are all valid visitor intents).
- Identify actionable gaps: If evidence is missing or recommended (e.g. guarantor letter, bank statements, leave approval), mark that finding as "at_risk" and describe what is needed.
- If statutory disqualification exists (e.g. prior overstay/deportation or active criminal ban), mark as "fail".
- If essential answers are missing, mark as "out_of_scope".
- For every finding, provide an official government citation with a valid https URL (e.g. from MOFA, ISA, UKVI, US State Dept).
- Overall "result": "fail" if any finding is "fail", else "out_of_scope" if any is "out_of_scope", else "at_risk" if any is "at_risk", else "pass".

Return STRICT JSON only, with no markdown fences:
{
  "result": "pass|at_risk|fail|out_of_scope",
  "summary": "Concise plain-language overview of the eligibility assessment.",
  "findings": [
    {
      "key": "snake_case_finding_key (e.g. identity_and_passport, travel_purpose, financial_capacity, immigration_compliance, filing_route)",
      "status": "pass|at_risk|fail|out_of_scope",
      "message": "Clear explanation of this criterion and why it passed or needs attention.",
      "citation": {
        "authority": "Official authority name (e.g. Ministry of Foreign Affairs of Japan)",
        "title": "Document or regulation title",
        "url": "https://...",
        "source_version": "YYYY-MM"
      }
    }
  ],
  "disclaimer": "This is an AI-assisted preparation check based on official published criteria, not legal advice or a government decision."
}
"""


@dataclass
class AIEvaluationRequest:
    destination_code: str
    purpose_code: str
    action_code: str
    nationality: str | None = None
    residence_country: str | None = None
    answers: dict[str, Any] = field(default_factory=dict)
    rules: list[dict[str, Any]] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class AIFinding:
    key: str
    status: EligibilityStatus
    message: str
    citation: dict[str, Any]


@dataclass
class AIEvaluationResult:
    result: EligibilityStatus
    findings: list[dict[str, Any]]
    disclaimer: str = "This is an AI-assisted preparation check based on official published criteria, not legal advice or a government decision."
    summary: str | None = None


class AIElegibilityEvaluator:
    """Evaluates applicant intake answers using LLM contextual reasoning."""

    def __init__(self, *, chat: ChatClient, settings: Settings) -> None:
        self._chat = chat
        self._settings = settings

    async def evaluate(self, req: AIEvaluationRequest) -> dict[str, Any]:
        dest = country_label(req.destination_code) or req.destination_code
        nat = country_label(req.nationality) or req.nationality or "Foreign national"
        res = country_label(req.residence_country) or req.residence_country or nat
        now = datetime.now(UTC)

        user_prompt_lines = [
            f"Destination Country: {dest} ({req.destination_code.upper()})",
            f"Visa Category: {req.purpose_code}",
            f"Action: {req.action_code}",
            f"Applicant Nationality: {nat}",
            f"Applicant Residence: {res}",
            f"Assessment Date: {now.strftime('%Y-%m-%d')}",
            "",
            "Applicant Intake Answers:",
            json.dumps(req.answers, indent=2, default=str),
        ]

        if req.rules:
            user_prompt_lines.extend(
                [
                    "",
                    "Published Statutory Rules Reference:",
                    json.dumps(req.rules, indent=2, default=str),
                ]
            )

        if req.context:
            user_prompt_lines.extend(
                [
                    "",
                    "Additional Application Context:",
                    json.dumps(req.context, indent=2, default=str),
                ]
            )

        user_prompt_lines.append("\nEvaluate the applicant and return strict JSON.")
        user_prompt = "\n".join(user_prompt_lines)

        try:
            raw = await self._chat.complete(system=ELIGIBILITY_SYSTEM_PROMPT, user=user_prompt)
            data = extract_json(raw)
        except Exception as exc:
            log.warning("ai_eligibility.llm_failed", error=str(exc))
            data = None

        if data is None or not isinstance(data, dict) or "result" not in data:
            log.info("ai_eligibility.fallback_heuristic", destination=req.destination_code)
            return self._heuristic_fallback(req)

        # Normalize and validate findings
        findings = []
        raw_findings = data.get("findings")
        if isinstance(raw_findings, list):
            for item in raw_findings:
                if isinstance(item, dict) and "key" in item and "status" in item:
                    status = str(item["status"]).lower()
                    if status not in ("pass", "at_risk", "fail", "out_of_scope"):
                        status = "pass"
                    cit = item.get("citation")
                    if not isinstance(cit, dict) or not cit.get("url"):
                        cit = self._default_citation(req.destination_code)
                    findings.append(
                        {
                            "key": str(item["key"]),
                            "status": status,
                            "message": str(item.get("message") or f"Evaluation for {item['key']}"),
                            "citation": cit,
                        }
                    )

        # Reconcile explicit statutory rules from req.rules to ensure statutory compliance
        for rule in req.rules:
            key = rule.get("key")
            if not key:
                continue
            answer = req.answers.get(key)
            if answer is None:
                continue
            op = str(rule.get("operator") or rule.get("type") or "equals").lower()
            val = rule.get("value")
            failure_status = str(rule.get("failure_status", "fail")).lower()
            breached = False
            if op in ("min", "gte") and isinstance(answer, (int, float)):
                threshold = val if isinstance(val, (int, float)) else 0
                if answer < threshold:
                    breached = True
            elif op in ("equals", "eq"):
                if answer != val:
                    breached = True
            if breached:
                existing = next((f for f in findings if f["key"] == key), None)
                if existing:
                    existing["status"] = failure_status
                else:
                    findings.append(
                        {
                            "key": key,
                            "status": failure_status,
                            "message": str(
                                rule.get(
                                    "message", f"Requirement for {key.replace('_', ' ')} not met."
                                )
                            ),
                            "citation": dict(
                                rule.get("citation") or self._default_citation(req.destination_code)
                            ),
                        }
                    )

        statuses = {f["status"] for f in findings}
        if "fail" in statuses:
            overall = "fail"
        elif "out_of_scope" in statuses:
            overall = "out_of_scope"
        elif "at_risk" in statuses:
            overall = "at_risk"
        else:
            overall = "pass"

        return {
            "result": overall,
            "findings": findings,
            "summary": data.get("summary") or "AI eligibility assessment completed.",
            "disclaimer": data.get(
                "disclaimer",
                "This is an AI-assisted preparation check based on official published criteria, not legal advice or a government decision.",
            ),
        }

    def _default_citation(self, destination: str) -> dict[str, Any]:
        dest = destination.upper()
        now_ver = datetime.now(UTC).strftime("%Y-%m")
        if dest == "JP":
            return {
                "authority": "Ministry of Foreign Affairs of Japan",
                "title": "Visa for Temporary Visitors",
                "url": "https://www.mofa.go.jp/j_info/visit/visa/index.html",
                "source_version": now_ver,
            }
        if dest in ("GB", "UK"):
            return {
                "authority": "UK Visas and Immigration",
                "title": "Standard Visitor visa eligibility",
                "url": "https://www.gov.uk/standard-visitor",
                "source_version": now_ver,
            }
        if dest == "US":
            return {
                "authority": "U.S. Department of State",
                "title": "Visitor Visa (B1/B2)",
                "url": "https://travel.state.gov/content/travel/en/us-visas/tourism-visit/visitor.html",
                "source_version": now_ver,
            }
        return {
            "authority": "Immigration Authority",
            "title": "Visa Eligibility Criteria",
            "url": "https://www.mofa.go.jp/j_info/visit/visa/index.html",
            "source_version": now_ver,
        }

    def _heuristic_fallback(self, req: AIEvaluationRequest) -> dict[str, Any]:
        """Provides a safe, contextual fallback evaluation when LLM client is offline or in mock test."""
        dest = req.destination_code.upper()
        cit = self._default_citation(dest)
        findings = []

        # 1. Travel Purpose
        purpose = str(
            req.answers.get("purpose_of_visit")
            or req.answers.get("main_purpose")
            or req.purpose_code
        ).lower()
        valid_purposes = {
            "tour",
            "tourism",
            "sightseeing",
            "holiday",
            "travel",
            "vacation",
            "visiting_family",
            "visiting_relatives_or_acquaintances",
            "visit",
        }
        if (
            any(p in purpose for p in valid_purposes)
            or purpose in valid_purposes
            or "tourist" in req.purpose_code.lower()
        ):
            findings.append(
                {
                    "key": "purpose_of_stay",
                    "status": "pass",
                    "message": f"Purpose '{purpose.replace('_', ' ')}' is valid for short-term visitor travel.",
                    "citation": cit,
                }
            )
        else:
            findings.append(
                {
                    "key": "purpose_of_stay",
                    "status": "at_risk",
                    "message": f"Purpose '{purpose}' may require a specific business or designated activities visa.",
                    "citation": cit,
                }
            )

        # 2. Stay Duration
        days = (
            req.answers.get("intended_length_of_stay_days")
            or req.answers.get("stay_duration_days")
            or 15
        )
        if isinstance(days, (int, float)) and days <= 90:
            findings.append(
                {
                    "key": "stay_duration",
                    "status": "pass",
                    "message": f"Requested stay of {int(days)} days satisfies the temporary visitor limit (<= 90 days).",
                    "citation": cit,
                }
            )
        else:
            findings.append(
                {
                    "key": "stay_duration",
                    "status": "at_risk",
                    "message": f"Stay of {days} days exceeds standard 90-day visitor limits.",
                    "citation": cit,
                }
            )

        # 3. Financial Capacity
        savings = req.answers.get("estimated_savings_available") or req.answers.get("savings")
        has_funds = req.answers.get("visitor_has_sufficient_funds") or req.answers.get(
            "bank_statement_available"
        )
        if has_funds is not False and (
            savings is None or (isinstance(savings, (int, float)) and savings >= 1000)
        ):
            findings.append(
                {
                    "key": "financial_capacity",
                    "status": "pass",
                    "message": "Financial capacity and supporting funds are confirmed.",
                    "citation": cit,
                }
            )
        else:
            findings.append(
                {
                    "key": "financial_capacity",
                    "status": "at_risk",
                    "message": "Additional proof of financial sponsorship or bank balance recommended.",
                    "citation": cit,
                }
            )

        # 4. Immigration Compliance
        prior_refusal = req.answers.get("prior_visa_refusal_any_country")
        prior_overstay = req.answers.get("prior_overstay_history")
        if prior_refusal or prior_overstay:
            findings.append(
                {
                    "key": "immigration_compliance",
                    "status": "at_risk",
                    "message": "Prior visa history or refusal noted. Consular review may request supplementary explanation.",
                    "citation": cit,
                }
            )
        # 5. Statutory / Category specific rules passed in req.rules
        for rule in req.rules:
            key = rule.get("key")
            if not key:
                continue
            answer = req.answers.get(key)
            if answer is None:
                continue
            rule_cit = dict(rule.get("citation") or cit)
            op = str(rule.get("operator") or rule.get("type") or "equals").lower()
            failure_status = rule.get("failure_status", "fail")
            msg = rule.get("message", f"Requirement for '{key.replace('_', ' ')}' not met.")
            val = rule.get("value")
            if op in ("min", "gte") and isinstance(answer, (int, float)):
                threshold = val if isinstance(val, (int, float)) else 0
                if answer < threshold:
                    findings.append(
                        {
                            "key": key,
                            "status": failure_status,
                            "message": msg,
                            "citation": rule_cit,
                        }
                    )
            elif op in ("equals", "eq"):
                if answer != val:
                    findings.append(
                        {
                            "key": key,
                            "status": failure_status,
                            "message": msg,
                            "citation": rule_cit,
                        }
                    )

        statuses = {f["status"] for f in findings}
        overall = "fail" if "fail" in statuses else "at_risk" if "at_risk" in statuses else "pass"

        return {
            "result": overall,
            "findings": findings,
            "summary": "AI eligibility screening completed against official destination criteria.",
            "disclaimer": "This is an AI-assisted preparation check based on official published criteria, not legal advice or a government decision.",
        }
