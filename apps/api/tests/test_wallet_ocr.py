"""Tests for Document Vault PyMuPDF extraction and apply-to-case."""

from __future__ import annotations

import pymupdf  # type: ignore

from torii_api.services.ocr_extractor import (
    extract_text_with_pymupdf,
    parse_structured_fields_from_text,
)


def test_pymupdf_pdf_text_extraction():
    """Verify PyMuPDF extracts text accurately from synthetic PDF."""
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text(
        (50, 72),
        "PASSPORT OF JAPAN\n"
        "Full Name: Kenji Sato\n"
        "Passport No: TR1234567\n"
        "Nationality: Japan\n"
        "Date of Birth: 1988-11-20\n"
        "Expiry Date: 2030-11-19\n",
    )
    pdf_bytes = doc.tobytes()
    doc.close()

    text = extract_text_with_pymupdf(pdf_bytes)
    assert "Kenji Sato" in text
    assert "TR1234567" in text
    assert "1988-11-20" in text


def test_parse_structured_fields_passport():
    """Verify structured fields are extracted from passport document text."""
    text = (
        "PASSPORT OF JAPAN\n"
        "Full Name: Kenji Sato\n"
        "Passport No: TR1234567\n"
        "Nationality: Japan\n"
        "Date of Birth: 1988-11-20\n"
        "Expiry Date: 2030-11-19\n"
    )
    fields, conf = parse_structured_fields_from_text("passport", text, "passport_scan.pdf")
    assert fields["full_name"]["value"] == "Kenji Sato"
    assert fields["passport_number"]["value"] == "TR1234567"
    assert fields["nationality"]["value"] == "Japan"
    assert fields["date_of_birth"]["value"] == "1988-11-20"
    assert fields["expiry_date"]["value"] == "2030-11-19"
    assert conf >= 0.85


def test_parse_structured_fields_financial():
    """Verify structured fields from bank statement / proof of funds."""
    text = (
        "Sumitomo Mitsui Banking Corporation\n"
        "Account Holder: Kenji Sato\n"
        "Account Number: 9876543210\n"
        "Available Balance: ¥1,500,000\n"
    )
    fields, conf = parse_structured_fields_from_text("bank_statement", text, "bank_statement.pdf")
    assert fields["account_holder"]["value"] == "Kenji Sato"
    assert fields["account_number"]["value"] == "9876543210"
    assert "1,500,000" in fields["balance"]["value"]
    assert "Bank" in fields["bank_name"]["value"]
    assert conf >= 0.8


def test_parse_structured_fields_residence_card():
    """Verify structured fields from residence card (zairyu card)."""
    text = (
        "RESIDENCE CARD\n"
        "Full Name: Kenji Sato\n"
        "Residence Card No: AB12345678CD\n"
        "Status of Residence: Engineer/Specialist in Humanities/International Services\n"
        "Address: 1-2-3 Roppongi, Minato-ku, Tokyo\n"
        "Date of Birth: 1988-11-20\n"
        "Expiry Date: 2028-11-19\n"
    )
    fields, conf = parse_structured_fields_from_text("residence_card", text, "residence_card.pdf")
    assert fields["residence_card_number"]["value"] == "AB12345678CD"
    assert "Engineer" in fields["status_of_residence"]["value"]
    assert "Roppongi" in fields["current_japan_address"]["value"]
    assert conf >= 0.85


def test_parse_structured_fields_tax_return():
    """Verify structured fields from taxation and income certificate."""
    text = (
        "TAXATION & INCOME CERTIFICATE\n"
        "Full Name: Kenji Sato\n"
        "Tax Year: 2025\n"
        "Gross Salary: JPY 7,800,000\n"
        "Taxable Amount: JPY 5,640,000\n"
        "Tax Paid: JPY 625,400\n"
    )
    fields, conf = parse_structured_fields_from_text("tax_return", text, "tax_return.pdf")
    assert fields["tax_year"]["value"] == "2025"
    assert "7,800,000" in fields["annual_income"]["value"]
    assert "5,640,000" in fields["taxable_income"]["value"]
    assert "625,400" in fields["tax_paid"]["value"]
    assert conf >= 0.85


def test_apply_extracted_fields_to_case_and_user():
    """Verify extracted fields properly populate both User profile and Case intake_answers."""
    from torii_api.api.case_workflow import _apply_extracted_fields_to_case_and_user
    from torii_api.db.models import Case, User

    user = User(
        id=1,
        email="applicant@example.com",
        password_hash="hash",
    )
    case = Case(
        id=10,
        reference="JP-2026-TEST01",
        jurisdiction_id=1,
        user_id=1,
        intake_answers={},
    )

    extracted = {
        "full_name": {"value": "Kenji Sato"},
        "nationality": {"value": "Japan"},
        "passport_number": {"value": "TR1234567"},
        "passport_expiry": {"value": "2030-11-19"},
        "date_of_birth": {"value": "1988-11-20"},
        "current_country": {"value": "Japan"},
        "residence_card_number": {"value": "AB12345678CD"},
        "status_of_residence": {"value": "Engineer/Specialist"},
        "bank_name": {"value": "SMBC"},
        "balance": {"value": "¥1,500,000"},
        "tax_year": {"value": "2025"},
        "annual_income": {"value": "JPY 7,800,000"},
        "employer_name": {"value": "Rakuten Group Inc."},
        "monthly_salary": {"value": "JPY 650,000"},
    }

    _apply_extracted_fields_to_case_and_user(case, user, extracted)

    # Check user model updates
    assert user.full_name == "Kenji Sato"
    assert user.nationality == "Japan"
    assert user.passport_number == "TR1234567"
    assert user.passport_expiry == "2030-11-19"
    assert user.date_of_birth == "1988-11-20"
    assert user.current_country == "Japan"
    assert user.profile_complete is True

    # Check case intake answers
    assert case.intake_answers["full_name"] == "Kenji Sato"
    assert case.intake_answers["passport_number"] == "TR1234567"
    assert case.intake_answers["residence_card_number"] == "AB12345678CD"
    assert case.intake_answers["status_of_residence"] == "Engineer/Specialist"
    assert case.intake_answers["bank_name"] == "SMBC"
    assert case.intake_answers["balance"] == "¥1,500,000"
    assert case.intake_answers["annual_income"] == "JPY 7,800,000"
    assert case.intake_answers["employer_name"] == "Rakuten Group Inc."
    assert case.intake_answers["monthly_salary"] == "JPY 650,000"
