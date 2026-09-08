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
    "visitor_nationality": ["nationality", "country_of_citizenship", "primary_citizenship", "citizenship", "country_of_nationality"],
    "visitor_passport_number": ["passport_number", "passport_no"],
    "full_name": ["applicant_name", "visitor_full_name", "visitor_name", "beneficiary_name"],
    "nationality": ["visitor_nationality", "country_of_citizenship", "primary_citizenship", "citizenship", "country_of_nationality"],
    "citizenship": ["nationality", "visitor_nationality", "country_of_citizenship", "primary_citizenship", "country_of_nationality"],
    "country_of_nationality": ["nationality", "citizenship", "country_of_citizenship", "visitor_nationality"],
    "country_of_citizenship": ["nationality", "citizenship", "country_of_nationality", "visitor_nationality"],
    "home_town_city": ["home_city", "hometown", "city_in_home_country"],
    "home_city": ["home_town_city", "hometown", "city_in_home_country"],
    "hometown": ["home_town_city", "home_city", "city_in_home_country"],
    "city_in_home_country": ["home_town_city", "home_city", "hometown"],
    "passport_number": ["passport_no", "visitor_passport_number"],
    "passport_expiry": ["passport_expiry_date", "expiry_date"],
    "passport_expiry_date": ["passport_expiry", "expiry_date"],
    "purpose_of_visit": ["main_purpose", "purpose_of_stay", "trip_purpose", "purpose"],
    "main_purpose": ["purpose_of_visit", "purpose_of_stay", "trip_purpose", "purpose"],
    "intended_length_of_stay_days": [
        "stay_duration_days",
        "duration_of_stay",
        "duration",
        "length_of_stay_days",
        "stay_days",
        "visit.length_of_stay_days",
    ],
    "stay_duration_days": [
        "intended_length_of_stay_days",
        "duration_of_stay",
        "duration",
        "length_of_stay_days",
        "stay_days",
        "visit.length_of_stay_days",
    ],
    "length_of_stay_days": [
        "intended_length_of_stay_days",
        "stay_duration_days",
        "duration_of_stay",
        "duration",
        "stay_days",
        "visit.length_of_stay_days",
    ],
    "stay_days": [
        "intended_length_of_stay_days",
        "stay_duration_days",
        "duration_of_stay",
        "duration",
        "length_of_stay_days",
        "visit.length_of_stay_days",
    ],
    "arrival_date": ["planned_arrival_date", "intended_arrival_date"],
    "planned_arrival_date": ["arrival_date", "intended_arrival_date"],
    # Only the same question asked another way. A savings figure or a choice of payer is
    # evidence a human weighs, not a declaration that funds are sufficient.
    "visitor_has_sufficient_funds": [
        "has_sufficient_funds",
        "support_type",
        "financial_support_type",
        "financial.support_type",
    ],
    "has_sufficient_funds": [
        "visitor_has_sufficient_funds",
        "support_type",
        "financial_support_type",
        "financial.support_type",
    ],
    "support_type": [
        "visitor_has_sufficient_funds",
        "has_sufficient_funds",
        "financial_support_type",
        "financial.support_type",
    ],
    "financial_support_type": [
        "support_type",
        "financial.support_type",
        "visitor_has_sufficient_funds",
        "has_sufficient_funds",
    ],
    "relationship_to_visitor": [
        "relationship",
        "sponsor_relationship",
        "relationship_to_applicant",
    ],
    "relationship": [
        "relationship_to_visitor",
        "sponsor_relationship",
        "relationship_to_applicant",
    ],
    "current_country": [
        "current_residence_country",
        "residence_country",
        "current_location_country",
        "country_of_residence",
    ],
    "current_residence_country": [
        "current_country",
        "residence_country",
        "current_location_country",
        "country_of_residence",
    ],
    "current_location_country": [
        "current_country",
        "current_residence_country",
        "residence_country",
        "country_of_residence",
    ],
    "residence_country": [
        "current_country",
        "current_residence_country",
        "current_location_country",
        "country_of_residence",
    ],
    "country_of_residence": [
        "current_country",
        "current_residence_country",
        "residence_country",
        "current_location_country",
    ],
    "residence_card_number": ["japan_residence_card", "zairyu_card_number"],
    "residence_card_expiry": ["japan_residence_expiry", "zairyu_card_expiry"],
    "salary": ["monthly_salary", "salary_monthly", "annual_salary_jpy", "income_monthly"],
    "monthly_salary": ["salary", "salary_monthly", "annual_salary_jpy", "income_monthly"],
    "employer": ["employer_name", "company_name", "sponsoring_organization", "host_company_name"],
    "employer_name": ["employer", "company_name", "sponsoring_organization", "host_company_name"],
    "corporate_number": ["employer_corporate_number", "company_number", "organization_number"],
    "employer_corporate_number": ["corporate_number", "company_number", "organization_number"],
    "attendance_rate": ["school.attendance_rate", "school_attendance_rate"],
    "school.attendance_rate": ["attendance_rate", "school_attendance_rate"],
    "school_attendance_rate": ["attendance_rate", "school.attendance_rate"],
    "school.enrollment_status": [
        "school_completed",
        "current_status",
        "enrollment_status",
        "school_enrollment_status",
    ],
    "school_completed": [
        "current_status",
        "school.enrollment_status",
        "enrollment_status",
        "school_enrollment_status",
    ],
    "current_status": [
        "school_completed",
        "current_visa_status",
        "school.enrollment_status",
        "enrollment_status",
    ],
    "enrollment_status": [
        "school.enrollment_status",
        "school_completed",
        "current_status",
        "school_enrollment_status",
    ],
    "school_enrollment_status": [
        "school.enrollment_status",
        "school_completed",
        "current_status",
        "enrollment_status",
    ],
}


def _resolve_form_field_value(answer_key: str, answers: dict[str, Any]) -> Any:
    """The applicant's answer for a form field, or ``None`` when they have not given one.

    Resolution is limited to what the applicant actually said: their own answer, or one of
    the aliases the packs use for the same fact. It never derives one fact from another —
    a savings figure is not a declaration of sufficient funds, and self-funding is not a
    statement that no guarantor exists. Those are findings the eligibility engine makes
    from stated answers, not values a form filler may assert on the applicant's behalf.
    """
    # 1. The answer itself.
    value = answers.get(answer_key)
    if value is not None and value != "":
        return value

    # 1b. Clean key without section/category prefix (e.g. "visit.length_of_stay_days" -> "length_of_stay_days")
    clean_key = answer_key.split(".")[-1]
    if clean_key != answer_key:
        value = answers.get(clean_key)
        if value is not None and value != "":
            return value

    # 2. An alias the packs use for the same fact.
    for alias in FORM_ANSWER_KEY_ALIASES.get(answer_key, []):
        candidate = answers.get(alias)
        if candidate is not None and candidate != "":
            return candidate

    # 2b. Aliases of clean key
    if clean_key != answer_key:
        for alias in FORM_ANSWER_KEY_ALIASES.get(clean_key, []):
            candidate = answers.get(alias)
            if candidate is not None and candidate != "":
                return candidate

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
        value = _resolve_form_field_value(answer_key, normalized_answers)
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

    # Auto-fill all populated intake answers with clean, official form labels.
    # Deduplicate alias variants so synonyms (e.g. nationality vs citizenship vs country_of_citizenship)
    # do not create multiple redundant entries with the same value.
    seen_canonical_aliases: set[str] = set()

    for key, val in normalized_answers.items():
        if val is None or val == "":
            continue

        clean_key = key.split(".")[-1].lower()
        aliases = FORM_ANSWER_KEY_ALIASES.get(key, []) + FORM_ANSWER_KEY_ALIASES.get(clean_key, [])
        canonical = (aliases[0] if aliases else clean_key).lower()

        already_filled = (
            key in filled
            or clean_key in filled
            or any(alias in filled for alias in aliases)
            or any(
                standard_label_map.get(a) in filled
                for a in [key, clean_key, *aliases]
                if standard_label_map.get(a)
            )
            or any(
                a.replace("_", " ").title() in filled
                for a in [key, clean_key, *aliases]
            )
            or canonical in seen_canonical_aliases
            or clean_key in seen_canonical_aliases
        )

        label = standard_label_map.get(key, key.replace("_", " ").title())
        if not already_filled and label not in filled and key not in filled:
            filled[label] = val
            seen_canonical_aliases.add(canonical)
            seen_canonical_aliases.add(clean_key)
            seen_canonical_aliases.add(key.lower())
            for alias in aliases:
                seen_canonical_aliases.add(alias.lower())

    return FilledForm(filled_fields=filled, missing_required_fields=missing)


def is_stale(form_code: str, form_version: str, live_versions: dict[str, str]) -> bool:
    return live_versions.get(form_code) != form_version
