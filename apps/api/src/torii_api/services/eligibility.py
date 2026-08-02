"""Deterministic, non-advisory eligibility screening (US-04).

Authored rules live in ``docs/jurisdictions/*.yml`` and are re-exported here for
tests and call sites that still import constants.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel

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


def _matches(answer: Any, operator: str, expected: Any) -> bool:
    if operator == "equals":
        return answer == expected
    numeric = isinstance(answer, (int, float)) and not isinstance(answer, bool)
    if operator == "min":
        return numeric and answer >= expected
    if operator == "max":
        return numeric and answer <= expected
    if operator == "in":
        return answer in expected
    if operator == "nationality_in":
        return isinstance(answer, str) and answer in expected
    if operator == "not_empty":
        return answer is not None and answer != ""
    return False


def evaluate_eligibility(answers: dict[str, Any], rules: list[dict[str, Any]]) -> EligibilityResult:
    """Evaluate stored answers without inference, recommendation, or legal advice."""
    findings: list[EligibilityFinding] = []
    for rule in rules:
        key = str(rule["key"])
        if key not in answers or answers[key] is None:
            findings.append(
                EligibilityFinding(
                    key=key,
                    status="out_of_scope",
                    message=f"Cannot evaluate '{key}' because the answer is missing.",
                    citation=dict(rule.get("citation") or {}),
                )
            )
            continue
        if not _matches(answers[key], str(rule["operator"]), rule.get("value")):
            findings.append(
                EligibilityFinding(
                    key=key,
                    status=rule.get("failure_status", "fail"),
                    message=str(rule.get("message", f"Rule for '{key}' was not met.")),
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
