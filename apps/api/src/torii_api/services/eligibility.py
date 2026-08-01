"""Deterministic, non-advisory eligibility screening (US-04)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel

EligibilityStatus = Literal["pass", "at_risk", "fail", "out_of_scope"]

JP_IMMIGRATION_CITATION = {
    "authority": "Immigration Services Agency of Japan",
    "title": "Application for Extension of Period of Stay",
    "url": "https://www.moj.go.jp/isa/applications/procedures/16-3.html",
    "source_version": "2026-04",
}

JP_WORK_RENEWAL_ELIGIBILITY_RULES: list[dict[str, Any]] = [
    {
        "key": "years_in_japan",
        "operator": "min",
        "value": 1,
        "failure_status": "fail",
        "message": "At least one full year in Japan is required for this renewal screening path.",
        "citation": JP_IMMIGRATION_CITATION,
    }
]

JP_STUDENT_NEW_APPLICATION_ELIGIBILITY_RULES: list[dict[str, Any]] = [
    {
        "key": "has_school_acceptance",
        "operator": "equals",
        "value": True,
        "failure_status": "fail",
        "message": (
            "An acceptance from a recognized school in Japan is required "
            "for this student visa path."
        ),
        "citation": {
            "authority": "Immigration Services Agency of Japan",
            "title": "Certificate of Eligibility Application (Student)",
            "url": "https://www.moj.go.jp/isa/applications/procedures/16-1.html",
            "source_version": "2026-04",
        },
    },
    {
        "key": "has_financial_support",
        "operator": "equals",
        "value": True,
        "failure_status": "at_risk",
        "message": "You should provide evidence of funds to cover tuition and living costs.",
        "citation": {
            "authority": "Immigration Services Agency of Japan",
            "title": "Certificate of Eligibility Application (Student)",
            "url": "https://www.moj.go.jp/isa/applications/procedures/16-1.html",
            "source_version": "2026-04",
        },
    },
]

JP_TOURIST_CITATION = {
    "authority": "Immigration Services Agency of Japan",
    "title": "Visa for Temporary Visitors (Tourism)",
    "url": "https://www.moj.go.jp/isa/applications/procedures/16-1.html",
    "source_version": "2026-04",
}

# Nationalities eligible for Japan eVISA (direct application).
# Source: Ministry of Foreign Affairs of Japan — Visa issuance procedures.
EVISA_DIRECT_NATIONALITIES: list[str] = [
    "AU", "BR", "CA", "KH", "SA", "ZA", "TW", "GB", "US",
]

# Nationalities that apply via Japanese consulate (not direct eVISA).
EVISA_CONSULATE_NATIONALITIES: list[str] = [
    "HK", "IN", "ID", "MO", "MN", "KR", "SG", "AE",
]

# All eVISA-eligible nationalities (direct + consulate).
EVISA_ELIGIBLE_NATIONALITIES = (
    EVISA_DIRECT_NATIONALITIES + EVISA_CONSULATE_NATIONALITIES
)

JP_TOURIST_NEW_APPLICATION_ELIGIBILITY_RULES: list[dict[str, Any]] = [
    {
        "key": "visitor_nationality",
        "operator": "nationality_in",
        "value": EVISA_ELIGIBLE_NATIONALITIES,
        "failure_status": "at_risk",
        "message": (
            "The visitor's nationality may not be eligible for Japan eVISA. "
            "They may need to apply through an accredited agency or on paper."
        ),
        "citation": JP_TOURIST_CITATION,
    },
    {
        "key": "intended_length_of_stay_days",
        "operator": "max",
        "value": 90,
        "failure_status": "at_risk",
        "message": (
            "Short-term visitor visas are typically issued for stays of up to "
            "90 days. Longer stays may require a different visa category."
        ),
        "citation": JP_TOURIST_CITATION,
    },
    {
        "key": "visitor_has_sufficient_funds",
        "operator": "equals",
        "value": "visitor_own_funds",
        "failure_status": "at_risk",
        "message": (
            "The visitor should demonstrate their own funds, or the guarantor "
            "should prepare a financial sponsorship statement."
        ),
        "citation": JP_TOURIST_CITATION,
    },
]

US_H1B_CITATION = {
    "authority": "U.S. Citizenship and Immigration Services",
    "title": "H-1B Specialty Occupations",
    "url": "https://www.uscis.gov/working-in-the-united-states/temporary-workers/h-1b-specialty-occupations",
    "source_version": "2026-04",
}

US_H1B_ELIGIBILITY_RULES: list[dict[str, Any]] = [
    {
        "key": "has_bachelor_degree",
        "operator": "equals",
        "value": True,
        "failure_status": "fail",
        "message": (
            "Published H-1B specialty occupation criteria generally require "
            "a related bachelor's degree or equivalent."
        ),
        "citation": US_H1B_CITATION,
    },
    {
        "key": "has_employer_sponsor",
        "operator": "equals",
        "value": True,
        "failure_status": "fail",
        "message": "An H-1B petition requires a U.S. employer petitioner.",
        "citation": US_H1B_CITATION,
    },
]


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
