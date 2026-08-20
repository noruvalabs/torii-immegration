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


FORM_ANSWER_KEY_ALIASES: dict[str, list[str]] = {
    "visitor_full_name": ["full_name", "applicant_name", "visitor_name", "beneficiary_name"],
    "visitor_nationality": ["nationality", "country_of_citizenship", "primary_citizenship"],
    "visitor_passport_number": ["passport_number", "passport_no"],
    "full_name": ["applicant_name", "visitor_full_name", "visitor_name", "beneficiary_name"],
    "nationality": ["visitor_nationality", "country_of_citizenship", "primary_citizenship"],
    "passport_number": ["passport_no", "visitor_passport_number"],
    "passport_expiry": ["passport_expiry_date", "expiry_date"],
    "passport_expiry_date": ["passport_expiry", "expiry_date"],
    "purpose_of_visit": ["main_purpose", "purpose_of_stay", "trip_purpose", "purpose"],
    "main_purpose": ["purpose_of_visit", "purpose_of_stay", "trip_purpose", "purpose"],
    "intended_length_of_stay_days": ["stay_duration_days", "duration_of_stay", "duration"],
    "stay_duration_days": ["intended_length_of_stay_days", "duration_of_stay", "duration"],
    "arrival_date": ["planned_arrival_date", "intended_arrival_date"],
    "planned_arrival_date": ["arrival_date", "intended_arrival_date"],
    "visitor_has_sufficient_funds": [
        "has_sufficient_funds",
        "estimated_savings_available",
        "savings",
        "trip_payer",
        "financial_support_type",
    ],
    "relationship_to_visitor": ["relationship", "sponsor_relationship", "relationship_to_applicant"],
    "relationship": ["relationship_to_visitor", "sponsor_relationship", "relationship_to_applicant"],
    "current_residence_country": ["residence_country", "current_location_country", "country_of_residence"],
    "current_location_country": ["current_residence_country", "residence_country", "country_of_residence"],
    "residence_country": ["current_residence_country", "current_location_country", "country_of_residence"],
    "residence_card_number": ["japan_residence_card", "zairyu_card_number"],
    "residence_card_expiry": ["japan_residence_expiry", "zairyu_card_expiry"],
    "salary": ["monthly_salary", "salary_monthly", "annual_salary_jpy", "income_monthly"],
    "monthly_salary": ["salary", "salary_monthly", "annual_salary_jpy", "income_monthly"],
    "employer": ["employer_name", "company_name", "sponsoring_organization", "host_company_name"],
    "employer_name": ["employer", "company_name", "sponsoring_organization", "host_company_name"],
    "corporate_number": ["employer_corporate_number", "company_number", "organization_number"],
    "employer_corporate_number": ["corporate_number", "company_number", "organization_number"],
}


def _resolve_form_field_value(answer_key: str, form_field: str, answers: dict[str, Any]) -> Any:
    # 1. Exact match
    if answer_key in answers and answers[answer_key] is not None and answers[answer_key] != "":
        return answers[answer_key]

    # 2. Aliases match
    for alias in FORM_ANSWER_KEY_ALIASES.get(answer_key, []):
        if alias in answers and answers[alias] is not None and answers[alias] != "":
            val = answers[alias]
            if answer_key == "visitor_has_sufficient_funds":
                if alias == "trip_payer":
                    return "Self-funded" if str(val).lower() == "self_funded" else "Sponsored"
                if alias == "estimated_savings_available":
                    return True
            return val

    # 3. Contextual defaults for guarantor/sponsor fields when travel is self-funded / independent
    trip_payer = str(answers.get("trip_payer") or "").lower()
    is_self_funded = (
        trip_payer in ("self_funded", "self", "applicant", "self-funded")
        or bool(answers.get("estimated_savings_available"))
    )

    if is_self_funded:
        if answer_key == "residence_card_number" and (
            "guarantor" in form_field.lower() or "guarantor" in answer_key.lower()
        ):
            return "N/A (Self-Funded / No Japan Guarantor)"
        if answer_key in ("relationship_to_visitor", "relationship", "sponsor_relationship"):
            return "Self (Direct Applicant)"
        if answer_key == "visitor_has_sufficient_funds":
            return "Self-funded (Personal savings & bank solvency)"
        if "guarantor" in form_field.lower() or "sponsor" in form_field.lower():
            if "name" in form_field.lower() or "name" in answer_key.lower():
                return answers.get("full_name") or "Self-funded Applicant"
            return "N/A (Self-Funded)"

    return None


def fill_form(field_mappings: list[dict[str, Any]], answers: dict[str, Any]) -> FilledForm:
    """Fill declared mappings and all available applicant intake answers into standard form fields."""
    filled: dict[str, Any] = {}
    missing: list[str] = []

    # 1. Standardize and normalize key answers
    normalized_answers = dict(answers or {})

    # Fill declared mappings first
    for mapping in field_mappings or []:
        if not isinstance(mapping, dict):
            continue
        raw_field = mapping.get("form_field")
        raw_key = mapping.get("answer_key")
        if raw_field is None or raw_key is None:
            continue
        form_field = str(raw_field)
        answer_key = str(raw_key)
        value = _resolve_form_field_value(answer_key, form_field, normalized_answers)
        if value is not None and value != "":
            filled[form_field] = value
        elif bool(mapping.get("required", False)):
            missing.append(form_field)

    # 2. Comprehensive official form field mapping dictionary
    standard_label_map: dict[str, str] = {
        "full_name": "Applicant Full Name",
        "applicant_name": "Applicant Name (as in Passport)",
        "date_of_birth": "Date of Birth (YYYY-MM-DD)",
        "place_of_birth": "Place / Country of Birth",
        "sex": "Sex / Gender",
        "marital_status": "Marital Status",
        "nationality": "Nationality / Citizenship",
        "current_residence_country": "Country of Current Residence",
        "residence_country": "Country of Residence",
        "passport_number": "Passport Number",
        "passport_issue_date": "Passport Issue Date",
        "passport_expiry_date": "Passport Expiry Date",
        "passport_issuing_authority": "Passport Issuing Authority",
        "main_purpose": "Purpose of Visit to Japan",
        "purpose_of_visit": "Main Purpose of Visit",
        "stay_duration_days": "Intended Length of Stay (Days)",
        "intended_length_of_stay_days": "Length of Stay in Japan (Days)",
        "planned_arrival_date": "Date of Arrival in Destination",
        "port_of_entry": "Port of Entry / Flight Details",
        "airline_flight_no": "Airline / Flight Number",
        "accommodation_type": "Accommodation Type in Japan",
        "accommodation_name": "Hotel / Accommodation Name",
        "accommodation_address": "Accommodation Address & Tel in Japan",
        "accommodation_booked": "Accommodation Booking Status",
        "trip_payer": "Funding / Trip Payer (Self/Sponsor)",
        "estimated_savings_available": "Available Liquid Savings / Funds",
        "occupation": "Current Profession / Occupation",
        "employer_name": "Employer / Company Name",
        "monthly_salary": "Monthly Salary / Income",
        "employer_address": "Employer Address & Telephone",
        "traveled_internationally_before": "Previous International Travel History",
        "relatives_or_friends_in_destination": "Host / Contact in Japan",
        "criminal_disclosures": "Criminal Record / Offence History (No/Yes)",
        "prior_deportation": "Prior Deportation / Entry Ban History",
    }

    # Auto-fill all populated intake answers with clean, official form labels
    for key, val in normalized_answers.items():
        if val is None or val == "":
            continue
        label = standard_label_map.get(key, key.replace("_", " ").title())
        if label not in filled and key not in filled:
            filled[label] = val

    return FilledForm(filled_fields=filled, missing_required_fields=missing)


def is_stale(form_code: str, form_version: str, live_versions: dict[str, str]) -> bool:
    return live_versions.get(form_code) != form_version
