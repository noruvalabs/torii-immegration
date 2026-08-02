"""Versioned official-form selection and explicit field mapping (US-07/08).

Form templates are authored in ``docs/jurisdictions/*.yml``.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from torii_api.services.pack_exports import pack_form

JP_WORK_RENEWAL_FORM_TEMPLATE: dict[str, Any] = pack_form("jp/work.renewal")
US_H1B_FORM_TEMPLATE: dict[str, Any] = pack_form("us/h1b.renewal")
JP_STUDENT_NEW_APPLICATION_FORM_TEMPLATE: dict[str, Any] = pack_form("jp/student.new_application")
JP_TOURIST_NEW_APPLICATION_FORM_TEMPLATE: dict[str, Any] = pack_form("jp/tourist.new_application")


class FilledForm(BaseModel):
    filled_fields: dict[str, Any]
    missing_required_fields: list[str]


def fill_form(field_mappings: list[dict[str, Any]], answers: dict[str, Any]) -> FilledForm:
    """Fill only declared mappings; never infer undeclared form fields."""
    filled: dict[str, Any] = {}
    missing: list[str] = []
    for mapping in field_mappings:
        form_field = str(mapping["form_field"])
        answer_key = str(mapping["answer_key"])
        value = answers.get(answer_key)
        if value is not None and value != "":
            filled[form_field] = value
        elif bool(mapping.get("required", False)):
            missing.append(form_field)
    return FilledForm(filled_fields=filled, missing_required_fields=missing)


def is_stale(form_code: str, form_version: str, live_versions: dict[str, str]) -> bool:
    return live_versions.get(form_code) != form_version
