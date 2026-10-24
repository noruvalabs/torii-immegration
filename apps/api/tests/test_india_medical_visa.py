"""Tests for Indian Medical Visa validation, OCR extraction, and content pack integration."""

from __future__ import annotations

from datetime import date, timedelta

from torii_api.services.checklist import (
    IN_MEDICAL_NEW_APPLICATION_DOCUMENT_REQUIREMENTS,
    visible_requirement_items,
)
from torii_api.services.content_packs import load_pack_by_scope
from torii_api.services.medical_visa_validation import (
    check_hospital_letter,
    check_passport_validity,
    validate_medical_visa_documents,
)
from torii_api.services.ocr_extractor import parse_structured_fields_from_text
from torii_api.services.packet import resolve_jurisdiction_submission_kit

# ── Content pack loading ───────────────────────────────────────────────────────


def test_india_medical_pack_loads() -> None:
    pack = load_pack_by_scope("in/medical.new_application")
    assert pack.scope.jurisdiction == "IN"
    assert pack.scope.visa_category == "medical"
    assert pack.scope.action == "new_application"
    assert pack.scope.is_live is True


def test_india_medical_pack_has_required_intake_questions() -> None:
    pack = load_pack_by_scope("in/medical.new_application")
    keys = {q["key"] for q in pack.questions}
    assert "full_name" in keys
    assert "passport_number" in keys
    assert "passport_expiry" in keys
    assert "nationality" in keys
    assert "destination_hospital" in keys
    assert "illness_treatment_category" in keys
    assert "has_indian_hospital_invitation" in keys
    assert "accompanying_attendants_count" in keys


def test_india_medical_pack_has_eligibility_rules() -> None:
    pack = load_pack_by_scope("in/medical.new_application")
    rule_keys = {r["key"] for r in pack.rules}
    assert "passport_expiry" in rule_keys
    assert "has_indian_hospital_invitation" in rule_keys
    assert "has_sufficient_funds" in rule_keys
    assert "accompanying_attendants_count" in rule_keys


def test_india_medical_pack_has_document_items() -> None:
    pack = load_pack_by_scope("in/medical.new_application")
    doc_codes = {d["code"] for d in pack.document_items}
    assert "passport" in doc_codes
    assert "indian_hospital_letter" in doc_codes
    assert "local_medical_referral" in doc_codes
    assert "proof_of_funds" in doc_codes
    assert "passport_photograph" in doc_codes


def test_india_medical_pack_has_forms() -> None:
    pack = load_pack_by_scope("in/medical.new_application")
    assert pack.forms
    form_codes = {f.code for f in pack.forms}
    assert "indian_medical_visa_application" in form_codes


def test_india_medical_pack_has_citations_on_all_rules_and_docs() -> None:
    pack = load_pack_by_scope("in/medical.new_application")
    for rule in pack.rules:
        citation = rule.get("citation")
        assert citation is not None, f"Rule {rule['key']} missing citation"
        assert citation.get("url", "").startswith("http"), (
            f"Rule {rule['key']} has invalid citation URL"
        )
    for doc in pack.document_items:
        citation = doc.get("citation")
        assert citation is not None, f"Document {doc['code']} missing citation"
        assert citation.get("url", "").startswith("http"), (
            f"Document {doc['code']} has invalid citation URL"
        )


# ── Checklist loading ──────────────────────────────────────────────────────────


def test_india_checklist_requirements_load() -> None:
    assert len(IN_MEDICAL_NEW_APPLICATION_DOCUMENT_REQUIREMENTS) >= 5


def test_india_checklist_visible_items_show_all_required() -> None:
    answers = {
        "full_name": "John Doe",
        "passport_number": "A12345678",
        "destination_hospital": "Apollo Hospitals Chennai",
    }
    items = visible_requirement_items(IN_MEDICAL_NEW_APPLICATION_DOCUMENT_REQUIREMENTS, answers)
    codes = {item.code for item in items}
    assert "passport" in codes
    assert "indian_hospital_letter" in codes
    assert "local_medical_referral" in codes
    assert "proof_of_funds" in codes


def test_kenya_origin_requires_yellow_fever_and_polio_certificates() -> None:
    kenya_answers = {
        "full_name": "Amina Ochieng",
        "origin_country": "KE",
        "destination_hospital": "Fortis Memorial Research Institute",
    }
    items = visible_requirement_items(
        IN_MEDICAL_NEW_APPLICATION_DOCUMENT_REQUIREMENTS, kenya_answers
    )
    codes = {item.code for item in items}
    assert "yellow_fever_certificate" in codes, (
        "Kenyan applicant must be asked for Yellow Fever Card"
    )
    assert "polio_vaccine_certificate" in codes, (
        "Kenyan applicant must be asked for Polio Certificate"
    )
    assert "utility_bill_address_proof" not in codes, (
        "Kenyan applicant does not use Bangladesh IVAC utility bill"
    )


def test_bangladesh_origin_requires_ivac_utility_bill_no_yellow_fever() -> None:
    bd_answers = {
        "full_name": "Rahim Ahmed",
        "origin_country": "BD",
        "destination_hospital": "Apollo Gleneagles Kolkata",
    }
    items = visible_requirement_items(IN_MEDICAL_NEW_APPLICATION_DOCUMENT_REQUIREMENTS, bd_answers)
    codes = {item.code for item in items}
    assert "utility_bill_address_proof" in codes, (
        "Bangladeshi applicant must provide IVAC utility bill"
    )
    assert "yellow_fever_certificate" not in codes, (
        "Bangladeshi applicant does not need Yellow Fever"
    )
    assert "polio_vaccine_certificate" not in codes


def test_us_origin_requires_standard_docs_only() -> None:
    us_answers = {
        "full_name": "Sarah Connor",
        "origin_country": "US",
        "destination_hospital": "Medanta The Medicity",
    }
    items = visible_requirement_items(IN_MEDICAL_NEW_APPLICATION_DOCUMENT_REQUIREMENTS, us_answers)
    codes = {item.code for item in items}
    assert "passport" in codes
    assert "indian_hospital_letter" in codes
    assert "yellow_fever_certificate" not in codes
    assert "utility_bill_address_proof" not in codes


# ── Passport validity checks ──────────────────────────────────────────────────


def test_passport_valid_produces_no_alerts() -> None:
    future = (date.today() + timedelta(days=365)).isoformat()
    alerts = check_passport_validity(future)
    assert len(alerts) == 0


def test_expired_passport_produces_error() -> None:
    past = (date.today() - timedelta(days=30)).isoformat()
    alerts = check_passport_validity(past)
    assert any(a.severity == "error" for a in alerts)
    assert any("expired" in a.message.lower() for a in alerts)


def test_passport_less_than_6_months_produces_error() -> None:
    short = (date.today() + timedelta(days=90)).isoformat()
    alerts = check_passport_validity(short)
    assert any(a.severity == "error" for a in alerts)
    assert any("6 months" in a.message for a in alerts)


def test_unparseable_expiry_produces_warning() -> None:
    alerts = check_passport_validity("not-a-date")
    assert any(a.severity == "warning" for a in alerts)


# ── Hospital letter cross-check ────────────────────────────────────────────────


def test_matching_hospital_letter_produces_no_errors() -> None:
    ocr_fields = {
        "patient_name": {"value": "John Doe", "confidence": 0.9},
        "patient_passport_number": {"value": "A12345678", "confidence": 0.9},
        "hospital_name": {"value": "Apollo Hospitals", "confidence": 0.9},
        "doctor_name": {"value": "Dr. Rajesh Kumar", "confidence": 0.85},
    }
    intake = {
        "full_name": "John Doe",
        "passport_number": "A12345678",
        "destination_hospital": "Apollo Hospitals Chennai",
    }
    alerts = check_hospital_letter(ocr_fields, intake)
    errors = [a for a in alerts if a.severity == "error"]
    assert len(errors) == 0


def test_mismatched_name_produces_error() -> None:
    ocr_fields = {
        "patient_name": {"value": "Jane Smith", "confidence": 0.9},
        "patient_passport_number": {"value": "A12345678", "confidence": 0.9},
    }
    intake = {
        "full_name": "John Doe",
        "passport_number": "A12345678",
    }
    alerts = check_hospital_letter(ocr_fields, intake)
    name_errors = [a for a in alerts if a.field == "patient_name" and a.severity == "error"]
    assert len(name_errors) == 1


def test_mismatched_passport_number_produces_error() -> None:
    ocr_fields = {
        "patient_name": {"value": "John Doe", "confidence": 0.9},
        "patient_passport_number": {"value": "B99999999", "confidence": 0.9},
    }
    intake = {
        "full_name": "John Doe",
        "passport_number": "A12345678",
    }
    alerts = check_hospital_letter(ocr_fields, intake)
    pp_errors = [a for a in alerts if a.field == "passport_number" and a.severity == "error"]
    assert len(pp_errors) == 1


def test_missing_passport_on_letter_produces_warning() -> None:
    ocr_fields = {
        "patient_name": {"value": "John Doe", "confidence": 0.9},
    }
    intake = {
        "full_name": "John Doe",
        "passport_number": "A12345678",
    }
    alerts = check_hospital_letter(ocr_fields, intake)
    pp_warnings = [a for a in alerts if a.field == "passport_number" and a.severity == "warning"]
    assert len(pp_warnings) == 1


# ── Full validation pipeline ──────────────────────────────────────────────────


def test_full_validation_catches_multiple_issues() -> None:
    passport_ocr = {
        "full_name": {"value": "Jane Smith", "confidence": 0.9},
        "passport_expiry": {
            "value": (date.today() + timedelta(days=60)).isoformat(),
            "confidence": 0.9,
        },
    }
    hospital_ocr = {
        "patient_name": {"value": "Jane Smith", "confidence": 0.9},
        "patient_passport_number": {"value": "WRONG123", "confidence": 0.9},
    }
    intake = {
        "full_name": "John Doe",
        "passport_number": "A12345678",
    }
    alerts = validate_medical_visa_documents(passport_ocr, hospital_ocr, intake)
    assert len(alerts) >= 2  # At least passport validity + passport number mismatch
    severities = {a["severity"] for a in alerts}
    assert "error" in severities


def test_clean_documents_produce_no_errors() -> None:
    future_expiry = (date.today() + timedelta(days=365)).isoformat()
    passport_ocr = {
        "full_name": {"value": "John Doe", "confidence": 0.95},
        "passport_expiry": {"value": future_expiry, "confidence": 0.92},
    }
    hospital_ocr = {
        "patient_name": {"value": "John Doe", "confidence": 0.9},
        "patient_passport_number": {"value": "A12345678", "confidence": 0.9},
        "hospital_name": {"value": "Apollo Hospitals", "confidence": 0.9},
        "doctor_name": {"value": "Dr. Rajesh Kumar", "confidence": 0.85},
    }
    intake = {
        "full_name": "John Doe",
        "passport_number": "A12345678",
        "destination_hospital": "Apollo Hospitals Chennai",
    }
    alerts = validate_medical_visa_documents(passport_ocr, hospital_ocr, intake)
    errors = [a for a in alerts if a["severity"] == "error"]
    assert len(errors) == 0


# ── OCR extraction for medical documents ───────────────────────────────────────


def test_ocr_extracts_hospital_name_from_letter() -> None:
    text = """
    Apollo Hospitals Chennai
    International Patient Services

    Patient Name: Mohammad Rahman
    Passport Number: B05421997
    Diagnosis: Coronary Artery Disease
    Treating Doctor: Dr. Venkatesh Murthy
    Registration No: TN-MED-2024-9912
    """
    fields, confidence = parse_structured_fields_from_text("indian_hospital_letter", text)
    assert "hospital_name" in fields
    assert "Apollo" in fields["hospital_name"]["value"]


def test_ocr_extracts_patient_passport_from_letter() -> None:
    text = """
    Fortis Healthcare Ltd
    Patient Name: Sarah Johnson
    Passport Number: C98765432
    Treatment Plan: Knee Replacement Surgery
    """
    fields, _ = parse_structured_fields_from_text("indian_hospital_letter", text)
    assert "patient_passport_number" in fields
    assert fields["patient_passport_number"]["value"] == "C98765432"


def test_ocr_extracts_doctor_name() -> None:
    text = """
    Medanta The Medicity
    Treating Doctor: Dr. Naresh Trehan
    Patient Name: Ahmed Hassan
    """
    fields, _ = parse_structured_fields_from_text("indian_hospital_letter", text)
    assert "doctor_name" in fields
    assert "Trehan" in fields["doctor_name"]["value"]


def test_ocr_extracts_diagnosis() -> None:
    text = """
    Hospital: Max Super Speciality
    Patient Name: Li Wei
    Diagnosis: Hepatocellular Carcinoma Stage II
    """
    fields, _ = parse_structured_fields_from_text("indian_hospital_letter", text)
    assert "diagnosis" in fields
    assert "carcinoma" in fields["diagnosis"]["value"].lower()


# ── India submission kit in packet.py ──────────────────────────────────────────


def test_india_packet_returns_india_specific_steps() -> None:
    steps, dossier = resolve_jurisdiction_submission_kit(jurisdiction_code="IN")
    assert len(steps) >= 4
    assert any("indian visa" in s["title"].lower() for s in steps)
    assert any("hospital" in d.lower() for d in dossier)


def test_india_dossier_has_medical_stacking_order() -> None:
    _, dossier = resolve_jurisdiction_submission_kit(jurisdiction_code="IN")
    joined = " ".join(dossier).lower()
    assert "cover letter" in joined
    assert "passport" in joined
    assert "hospital" in joined
    assert "medical" in joined
