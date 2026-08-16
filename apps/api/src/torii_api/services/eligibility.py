"""Deterministic, non-advisory eligibility screening (US-04).

Authored rules live in ``docs/jurisdictions/*.yml`` and are re-exported here for
tests and call sites that still import constants.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel

from torii_api.services.content_packs import is_effective_on
from torii_api.services.pack_exports import pack_rules

EligibilityStatus = Literal["pass", "at_risk", "fail", "out_of_scope"]

JP_IMMIGRATION_CITATION = {
    "authority": "Immigration Services Agency of Japan",
    "title": "Application for Extension of Period of Stay",
    "url": "https://www.moj.go.jp/isa/applications/procedures/16-3.html",
    "source_version": "2026-04",
}

JP_WORK_RENEWAL_ELIGIBILITY_RULES: list[dict[str, Any]] = pack_rules("jp/work.renewal")
JP_STUDENT_NEW_APPLICATION_ELIGIBILITY_RULES: list[dict[str, Any]] = pack_rules(
    "jp/student.new_application"
)
JP_TOURIST_NEW_APPLICATION_ELIGIBILITY_RULES: list[dict[str, Any]] = pack_rules(
    "jp/tourist.new_application"
)
US_H1B_ELIGIBILITY_RULES: list[dict[str, Any]] = pack_rules("us/h1b.renewal")

# Nationalities eligible for Japan eVISA (direct application).
# Source: Ministry of Foreign Affairs of Japan — Visa issuance procedures.
EVISA_DIRECT_NATIONALITIES: list[str] = [
    "AU",
    "BR",
    "CA",
    "KH",
    "SA",
    "ZA",
    "TW",
    "GB",
    "US",
]

# Nationalities that apply via Japanese consulate (not direct eVISA).
EVISA_CONSULATE_NATIONALITIES: list[str] = [
    "HK",
    "IN",
    "ID",
    "MO",
    "MN",
    "KR",
    "SG",
    "AE",
]

# All eVISA-eligible nationalities (direct + consulate).
EVISA_ELIGIBLE_NATIONALITIES = EVISA_DIRECT_NATIONALITIES + EVISA_CONSULATE_NATIONALITIES


class EligibilityFinding(BaseModel):
    key: str
    status: EligibilityStatus
    message: str
    citation: dict[str, Any]


class EligibilityResult(BaseModel):
    result: EligibilityStatus
    findings: list[EligibilityFinding]
    disclaimer: str = (
        "This is a rules-based preparation check, not legal advice or a government decision."
    )


KEY_ALIASES: dict[str, list[str]] = {
    "purpose_of_stay": ["main_purpose", "purpose_of_visit", "trip_purpose", "purpose", "travel_purpose"],
    "main_purpose": ["purpose_of_stay", "purpose_of_visit", "trip_purpose", "purpose", "travel_purpose"],
    "stay_duration_days": ["duration_of_stay", "stay_duration", "duration", "days_of_stay"],
    "passport_expiry_date": ["passport_expiry", "expiry_date"],
    "passport_issue_date": ["passport_issue", "issue_date"],
    "current_residence_country": ["residence_country", "current_country", "country_of_residence"],
    "estimated_savings_available": ["savings", "savings_available", "funds_available"],
    "bank_statement_available": ["has_sufficient_funds", "bank_statement_6_months", "bank_statements_available"],
    "traveled_internationally_before": ["travel_history", "international_travel"],
    "prior_overstay_history": ["prior_overstay", "overstay_history"],
    "prior_visa_refusal_any_country": ["prior_refusal", "visa_refusal"],
}

PURPOSE_SYNONYMS: set[str] = {"tour", "tourism", "sightseeing", "holiday", "travel", "vacation", "leisure", "visit"}


def _get_answer_for_key(key: str, answers: dict[str, Any]) -> Any:
    if key in answers and answers[key] is not None:
        return answers[key]
    aliases = KEY_ALIASES.get(key, [])
    for alias in aliases:
        if alias in answers and answers[alias] is not None:
            return answers[alias]
    return None


def _matches(answer: Any, operator: str, expected: Any, context: dict[str, Any]) -> bool:
    if operator == "equals":
        if answer == expected:
            return True
        # Normalize booleans
        if isinstance(expected, bool):
            if isinstance(answer, str):
                return (answer.lower() == "true") == expected
        # Normalize strings
        if isinstance(answer, str) and isinstance(expected, str):
            ans_clean = answer.strip().lower().replace("_", " ")
            exp_clean = expected.strip().lower().replace("_", " ")
            if ans_clean == exp_clean:
                return True
            if ans_clean in PURPOSE_SYNONYMS and exp_clean in PURPOSE_SYNONYMS:
                return True
            return exp_clean in ans_clean or ans_clean in exp_clean
        return False

    numeric = isinstance(answer, (int, float)) and not isinstance(answer, bool)
    if operator == "min":
        return numeric and answer >= expected
    if operator == "max":
        return numeric and answer <= expected
    if operator == "in":
        if isinstance(expected, list):
            if isinstance(answer, str):
                return any(
                    str(opt).strip().lower() == answer.strip().lower()
                    or str(opt).strip().lower() in answer.strip().lower()
                    for opt in expected
                )
            return answer in expected
        if isinstance(expected, str) and isinstance(answer, str):
            ans_clean = answer.strip().lower()
            exp_clean = expected.strip().lower()
            return ans_clean == exp_clean or ans_clean in exp_clean or exp_clean in ans_clean
        return False
    if operator == "nationality_in":
        if isinstance(expected, list) and isinstance(answer, str):
            return any(
                str(opt).strip().lower() == answer.strip().lower()
                or str(opt).strip().lower() in answer.strip().lower()
                for opt in expected
            )
        return isinstance(answer, str) and answer in expected
    if operator == "not_empty":
        return answer is not None and str(answer).strip() != ""
    if operator == "context_equals":
        return context.get(str(expected)) == answer
    return False


def _rule_applies(rule: dict[str, Any], as_of: date, context: dict[str, Any]) -> bool:
    """A rule applies when it is temporally effective and matches the employer category."""
    if not is_effective_on(rule, as_of):
        return False
    required_categories = rule.get("employer_category")
    if required_categories is not None:
        actual = context.get("employer_category")
        if actual is None:
            return False
        if isinstance(required_categories, list):
            return actual in required_categories
        return actual == required_categories
    return True


def evaluate_eligibility(
    answers: dict[str, Any],
    rules: list[dict[str, Any]],
    *,
    as_of: date | None = None,
    context: dict[str, Any] | None = None,
) -> EligibilityResult:
    """Evaluate stored answers without inference, recommendation, or legal advice.

    ``as_of`` selects rules by their ``effective_from`` / ``effective_until`` window
    (defaults to today). ``context`` carries dimensions outside the intake answers —
    ``employer_category`` and prior-application continuity facts (``context_equals``).
    """
    as_of = as_of or date.today()
    context = context or {}
    findings: list[EligibilityFinding] = []
    for rule in rules:
        if not _rule_applies(rule, as_of, context):
            continue
        key = str(rule["key"])
        answer = _get_answer_for_key(key, answers)
        if answer is None or str(answer).strip() == "":
            findings.append(
                EligibilityFinding(
                    key=key,
                    status="out_of_scope",
                    message=f"Cannot evaluate '{key.replace('_', ' ')}' because the answer is missing in intake.",
                    citation=dict(rule.get("citation") or {}),
                )
            )
            continue
        if not _matches(answer, str(rule["operator"]), rule.get("value"), context):
            findings.append(
                EligibilityFinding(
                    key=key,
                    status=rule.get("failure_status", "fail"),
                    message=str(rule.get("message", f"Rule for '{key.replace('_', ' ')}' was not met.")),
                    citation=dict(rule.get("citation") or {}),
                )
            )
        else:
            findings.append(
                EligibilityFinding(
                    key=key,
                    status="pass",
                    message=str(rule.get("pass_message", f"Criterion '{key.replace('_', ' ')}' is satisfied based on intake answers.")),
                    citation=dict(rule.get("citation") or {}),
                )
            )

    statuses = {finding.status for finding in findings}
    if "fail" in statuses:
        result: EligibilityStatus = "fail"
    elif "out_of_scope" in statuses:
        result = "out_of_scope"
    elif "at_risk" in statuses:
        result = "at_risk"
    else:
        result = "pass"
    return EligibilityResult(result=result, findings=findings)
