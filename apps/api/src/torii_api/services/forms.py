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

US_H1B_FORM_TEMPLATE: dict[str, Any] = {
    "code": "i129_h1b",
    "version": "2026-04",
    "official_title": "Petition for a Nonimmigrant Worker (Form I-129) — H-1B",
    "citation": {
        "authority": "U.S. Citizenship and Immigration Services",
        "title": "Form I-129",
        "url": "https://www.uscis.gov/i-129",
        "source_version": "2026-04",
    },
    "field_mappings": [
        {"form_field": "beneficiary.full_name", "answer_key": "full_name", "required": True},
        {
            "form_field": "beneficiary.passport_number",
            "answer_key": "passport_number",
            "required": True,
        },
        {"form_field": "job.title", "answer_key": "job_title", "required": True},
        {"form_field": "petitioner.name", "answer_key": "sponsor_name", "required": False},
        {
            "form_field": "beneficiary.years_in_h1b",
            "answer_key": "years_in_h1b",
            "required": False,
        },
    ],
}

JP_STUDENT_NEW_APPLICATION_FORM_TEMPLATE: dict[str, Any] = {
    "code": "student_visa_application",
    "version": "2026-04",
    "official_title": "Visa Application Form for Entry into Japan (Student)",
    "citation": {
        "authority": "Ministry of Foreign Affairs of Japan",
        "title": "Visa Application Form",
        "url": "https://www.mofa.go.jp/j_info/visit/visa/index.html",
        "source_version": "2026-04",
    },
    "field_mappings": [
        {"form_field": "applicant.full_name", "answer_key": "full_name", "required": True},
        {
            "form_field": "applicant.passport_number",
            "answer_key": "passport_number",
            "required": True,
        },
        {"form_field": "education.school_name", "answer_key": "school_name", "required": False},
        {"form_field": "support.sponsor_type", "answer_key": "sponsor_type", "required": True},
        {"form_field": "eligibility.has_coe", "answer_key": "has_coe", "required": True},
    ],
}


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
