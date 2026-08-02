"""Document checklist definition filtering and status transitions (US-05).

Document requirement sets are authored in ``docs/jurisdictions/*.yml``.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel

from torii_api.services.pack_exports import pack_documents

ChecklistStatus = Literal["needed", "gathered", "uploaded"]

JP_WORK_RENEWAL_DOCUMENT_REQUIREMENTS: list[dict[str, Any]] = pack_documents("jp/work.renewal")
US_H1B_DOCUMENT_REQUIREMENTS: list[dict[str, Any]] = pack_documents("us/h1b.renewal")
JP_STUDENT_NEW_APPLICATION_DOCUMENT_REQUIREMENTS: list[dict[str, Any]] = pack_documents(
    "jp/student.new_application"
)
JP_TOURIST_NEW_APPLICATION_DOCUMENT_REQUIREMENTS: list[dict[str, Any]] = pack_documents(
    "jp/tourist.new_application"
)


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
