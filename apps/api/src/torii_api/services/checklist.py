"""Document checklist definition filtering and status transitions (US-05)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel

from torii_api.services.eligibility import JP_IMMIGRATION_CITATION

ChecklistStatus = Literal["needed", "gathered", "uploaded"]

JP_WORK_RENEWAL_DOCUMENT_REQUIREMENTS: list[dict[str, Any]] = [
    {
        "code": "passport",
        "name": {"en": "Passport", "ja": "パスポート"},
        "how_to_obtain": {"en": "Use your current valid passport.", "ja": "有効なパスポート。"},
        "why_required": {"en": "Confirms identity and travel document details."},
        "is_required": True,
        "citation": JP_IMMIGRATION_CITATION,
    },
    {
        "code": "residence_card",
        "name": {"en": "Residence card", "ja": "在留カード"},
        "how_to_obtain": {"en": "Use the residence card currently issued to you."},
        "why_required": {"en": "Confirms current residence status."},
        "is_required": True,
        "citation": JP_IMMIGRATION_CITATION,
    },
    {
        "code": "employment_contract",
        "name": {"en": "Employment contract", "ja": "雇用契約書"},
        "how_to_obtain": {"en": "Request a current copy from your employer."},
        "why_required": {"en": "Supports current employment details."},
        "is_required": True,
        "show_when": {"key": "employment_status", "equals": "employed"},
        "citation": JP_IMMIGRATION_CITATION,
    },
]

US_H1B_DOCUMENT_REQUIREMENTS: list[dict[str, Any]] = [
    {
        "code": "passport",
        "name": {"en": "Passport"},
        "how_to_obtain": {"en": "Use your current valid passport biographic page."},
        "why_required": {"en": "Confirms identity and travel document details."},
        "is_required": True,
        "citation": {
            "authority": "U.S. Citizenship and Immigration Services",
            "title": "H-1B Specialty Occupations",
            "url": "https://www.uscis.gov/working-in-the-united-states/temporary-workers/h-1b-specialty-occupations",
            "source_version": "2026-04",
        },
    },
    {
        "code": "degree_diploma",
        "name": {"en": "Degree diploma / transcripts"},
        "how_to_obtain": {
            "en": (
                "Request official transcripts or diploma from your university; "
                "include a foreign credential evaluation if the degree is not from the U.S."
            )
        },
        "why_required": {"en": "Supports the specialty occupation education requirement."},
        "is_required": True,
        "citation": {
            "authority": "U.S. Citizenship and Immigration Services",
            "title": "H-1B Specialty Occupations",
            "url": "https://www.uscis.gov/working-in-the-united-states/temporary-workers/h-1b-specialty-occupations",
            "source_version": "2026-04",
        },
    },
    {
        "code": "job_offer_letter",
        "name": {"en": "Job offer / employment letter"},
        "how_to_obtain": {
            "en": (
                "Ask your petitioning employer for a signed offer or support "
                "letter describing the specialty role."
            )
        },
        "why_required": {
            "en": "Documents the offered specialty occupation and employer relationship."
        },
        "is_required": True,
        "show_when": {"key": "has_employer_sponsor", "equals": True},
        "citation": {
            "authority": "U.S. Citizenship and Immigration Services",
            "title": "H-1B Specialty Occupations",
            "url": "https://www.uscis.gov/working-in-the-united-states/temporary-workers/h-1b-specialty-occupations",
            "source_version": "2026-04",
        },
    },
    {
        "code": "i94_record",
        "name": {"en": "I-94 arrival/departure record"},
        "how_to_obtain": {
            "en": (
                "Download your most recent I-94 from https://i94.cbp.dhs.gov/ "
                "if you are currently in the U.S."
            )
        },
        "why_required": {
            "en": "Confirms current U.S. admission status for extension/change filings."
        },
        "is_required": True,
        "show_when": {"key": "currently_in_h1b", "equals": True},
        "citation": {
            "authority": "U.S. Customs and Border Protection",
            "title": "I-94 Website",
            "url": "https://i94.cbp.dhs.gov/",
            "source_version": "2026-04",
        },
    },
]

JP_STUDENT_NEW_APPLICATION_DOCUMENT_REQUIREMENTS: list[dict[str, Any]] = [
    {
        "code": "passport",
        "name": {"en": "Passport", "ja": "パスポート"},
        "how_to_obtain": {"en": "Use your current valid passport.", "ja": "有効なパスポート。"},
        "why_required": {"en": "Confirms your identity and travel document details."},
        "is_required": True,
        "citation": {
            "authority": "Immigration Services Agency of Japan",
            "title": "Certificate of Eligibility Application (Student)",
            "url": "https://www.moj.go.jp/isa/applications/procedures/16-1.html",
            "source_version": "2026-04",
        },
    },
    {
        "code": "school_acceptance_letter",
        "name": {"en": "School acceptance letter", "ja": "入学許可書"},
        "how_to_obtain": {
            "en": "Request the official acceptance/admission letter from your school."
        },
        "why_required": {"en": "Shows the purpose of stay as study in Japan."},
        "is_required": True,
        "citation": {
            "authority": "Immigration Services Agency of Japan",
            "title": "Certificate of Eligibility Application (Student)",
            "url": "https://www.moj.go.jp/isa/applications/procedures/16-1.html",
            "source_version": "2026-04",
        },
    },
    {
        "code": "financial_proof",
        "name": {"en": "Proof of financial support", "ja": "経費支弁能力を証明する資料"},
        "how_to_obtain": {
            "en": "Prepare bank statements, scholarship letters, or sponsor financial documents."
        },
        "why_required": {"en": "Shows ability to cover tuition and living expenses."},
        "is_required": True,
        "citation": {
            "authority": "Immigration Services Agency of Japan",
            "title": "Certificate of Eligibility Application (Student)",
            "url": "https://www.moj.go.jp/isa/applications/procedures/16-1.html",
            "source_version": "2026-04",
        },
    },
    {
        "code": "coe_copy",
        "name": {
            "en": "Certificate of Eligibility (if issued)",
            "ja": "在留資格認定証明書（交付済みの場合）",
        },
        "how_to_obtain": {"en": "Include a copy if your school already obtained a COE for you."},
        "why_required": {"en": "Helps confirm eligibility status for visa issuance processing."},
        "is_required": False,
        "show_when": {"key": "has_coe", "equals": True},
        "citation": {
            "authority": "Immigration Services Agency of Japan",
            "title": "Certificate of Eligibility Application (Student)",
            "url": "https://www.moj.go.jp/isa/applications/procedures/16-1.html",
            "source_version": "2026-04",
        },
    },
]


class ChecklistDefinitionItem(BaseModel):
    code: str
    name: str | dict[str, str]
    how_to_obtain: str | dict[str, str]
    why_required: str | dict[str, str]
    is_required: bool = True
    citation: dict[str, Any]
    show_when: dict[str, Any] | None = None


def visible_requirement_items(
    raw_items: list[dict[str, Any]], answers: dict[str, Any]
) -> list[ChecklistDefinitionItem]:
    """Return requirement items whose optional ``show_when`` condition matches."""
    items = [ChecklistDefinitionItem.model_validate(item) for item in raw_items]
    return [
        item
        for item in items
        if item.show_when is None
        or answers.get(str(item.show_when["key"])) == item.show_when.get("equals")
    ]


def update_status(current: str, requested: ChecklistStatus) -> ChecklistStatus:
    """Allow applicant-driven checklist status changes without skipping document upload."""
    if requested == "uploaded":
        return "uploaded"
    if requested == "gathered":
        return "gathered"
    if current == "uploaded":
        return "uploaded"
    if current == "gathered":
        return "gathered"
    return "needed"
