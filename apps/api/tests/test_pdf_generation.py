"""Unit tests for PDF generation and API download endpoints."""

from __future__ import annotations

from torii_api.services.pdf_generator import (
    generate_cover_letter_pdf,
    generate_dossier_packet_pdf,
    generate_japan_work_renewal_pdf,
)


def test_japan_work_renewal_pdf_generation():
    answers = {
        "full_name": "Hasib Rahman",
        "nationality": "BD",
        "date_of_birth": "1995-05-15",
        "passport_number": "TK9876543",
        "residence_card_number": "AB12345678CD",
        "employer_name": "Tokyo Tech Solutions KK",
        "monthly_salary": "350000",
    }
    pdf_bytes = generate_japan_work_renewal_pdf("JP-2026-TEST01", answers, "Japan · Work Renewal")
    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_bytes) > 2000


def test_cover_letter_pdf_generation():
    answers = {
        "full_name": "Hasib Rahman",
        "passport_number": "TK9876543",
        "nationality": "BD",
    }
    checklist = [
        {"name": "Valid Passport", "status": "verified", "citation": {"authority": "MOJ"}},
        {"name": "Tax Certificate", "status": "provided", "citation": {"authority": "Tax Office"}},
    ]
    pdf_bytes = generate_cover_letter_pdf(
        "JP-2026-TEST01", answers, checklist, "Japan · Work Renewal"
    )
    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_bytes) > 2000


def test_dossier_packet_pdf_generation():
    answers = {
        "full_name": "Hasib Rahman",
        "passport_number": "TK9876543",
    }
    forms = [{"form_code": "moj_work_renewal", "filled_fields": {"name": "Hasib"}}]
    checklist = [{"name": "Passport", "citation": {"authority": "MOJ", "url": "https://moj.go.jp"}}]
    pdf_bytes = generate_dossier_packet_pdf("JP-2026-TEST01", answers, forms, checklist)
    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_bytes) > 3000


def test_uk_visa_application_pdf_generation_with_photo():
    import base64
    # 1x1 dummy PNG
    dummy_png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")
    answers = {
        "full_name": "Hasib Rahman",
        "nationality": "BD",
        "date_of_birth": "2003-10-23",
        "passport_number": "TK4545655",
        "passport_expiry": "2028-02-11",
        "sponsor_name": "Envobyte UK Ltd",
        "cos_reference": "COS12345678",
        "job_title": "Software Engineer",
        "annual_salary_gbp": 38700,
        "english_language_proof": "passed_approved_test",
        "sponsor_certifies_maintenance": True,
    }
    from torii_api.services.pdf_generator import generate_uk_visa_application_pdf
    pdf_bytes = generate_uk_visa_application_pdf("UK-2026-SKILLED", answers, "United Kingdom · Skilled Worker", photo_data=dummy_png)
    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_bytes) > 3000


def test_us_visa_application_pdf_generation():
    answers = {
        "full_name": "Hasib Rahman",
        "nationality": "BD",
        "date_of_birth": "2003-10-23",
        "passport_number": "TK4545655",
        "employer_name": "Tech Corp USA",
        "job_title": "Software Engineer",
    }
    from torii_api.services.pdf_generator import generate_us_visa_application_pdf
    pdf_bytes = generate_us_visa_application_pdf("US-2026-H1B", answers, "United States · H-1B")
    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_bytes) > 3000


def test_official_japan_mofa_template_with_photo():
    import base64
    dummy_png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")
    answers = {
        "full_name": "Hasib Rahman",
        "nationality": "BD",
        "date_of_birth": "2003-10-23",
        "passport_number": "TK4545655",
        "passport_expiry": "2028-02-11",
        "accommodation_name": "Tokyo Hotel",
    }
    from torii_api.services.pdf_generator import generate_official_japan_visa_form_pdf
    pdf_bytes = generate_official_japan_visa_form_pdf("JP-2026-TOURIST", answers, "Japan · Tourist", photo_data=dummy_png)
    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_bytes) > 3000


def _consular_sheet_text(answers: dict) -> str:
    """The words a visa officer actually reads off the filled consular form."""
    import io

    import pypdf

    from torii_api.services.pdf_generator import generate_official_japan_visa_form_pdf

    pdf_bytes = generate_official_japan_visa_form_pdf("JP-2026-TOURIST", answers, "Japan")
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def test_consular_form_prints_the_country_not_the_iso_code():
    """Packs store nationality as a code so the rules can match on it; the form asks for
    the country, and "BD" is not an answer to "Nationality or citizenship"."""
    text = _consular_sheet_text({"full_name": "Rahim Uddin", "nationality": "BD"})
    assert "Bangladesh" in text

    # A nationality already written out passes through as the applicant wrote it.
    written = _consular_sheet_text({"full_name": "Rahim Uddin", "nationality": "Bangladesh"})
    assert "Bangladesh" in written


def test_consular_form_names_the_country_behind_an_other_nationality():
    """The enum lists the nationalities the rules match on; "other" is not a country."""
    text = _consular_sheet_text(
        {"full_name": "Rahim Uddin", "nationality": "other", "nationality_other": "Bhutan"}
    )
    assert "Bhutan" in text


def test_consular_form_prints_the_purpose_in_words():
    """The enum token is this service's vocabulary, not the ministry's."""
    text = _consular_sheet_text({"full_name": "Rahim Uddin", "purpose_of_visit": "visiting_family"})
    assert "Visiting relatives" in text
    assert "visiting_family" not in text
