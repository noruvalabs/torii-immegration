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
        "Available Balance: ¥1,500,000\n"
    )
    fields, conf = parse_structured_fields_from_text("bank_statement", text, "bank_statement.pdf")
    assert fields["account_holder"]["value"] == "Kenji Sato"
    assert "1,500,000" in fields["balance"]["value"]
    assert "Bank" in fields["bank_name"]["value"]
    assert conf >= 0.8
