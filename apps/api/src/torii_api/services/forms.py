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
        value = normalized_answers.get(answer_key)
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
