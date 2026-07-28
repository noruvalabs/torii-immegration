"""Versioned official-form selection and explicit field mapping (US-07/08)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from torii_api.services.eligibility import JP_IMMIGRATION_CITATION

JP_WORK_RENEWAL_FORM_TEMPLATE: dict[str, Any] = {
    "code": "extension_of_stay",
    "version": "2026-04",
    "official_title": "Application for Extension of Period of Stay",
    "citation": JP_IMMIGRATION_CITATION,
    "field_mappings": [
        {"form_field": "applicant.full_name", "answer_key": "full_name", "required": True},
        {
            "form_field": "applicant.passport_number",
            "answer_key": "passport_number",
            "required": True,
        },
        {
            "form_field": "residence.years_in_japan",
            "answer_key": "years_in_japan",
            "required": True,
        },
        {"form_field": "sponsor.name", "answer_key": "sponsor_name", "required": False},
        {
            "form_field": "employment.status",
            "answer_key": "employment_status",
            "required": True,
        },
        {"form_field": "employment.employer", "answer_key": "employer_name", "required": False},
    ],
}


class FilledForm(BaseModel):
    filled_fields: dict[str, Any]
    missing_required_fields: list[str]


def fill_form(
    field_mappings: list[dict[str, Any]], answers: dict[str, Any]
) -> FilledForm:
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
