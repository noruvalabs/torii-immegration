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
