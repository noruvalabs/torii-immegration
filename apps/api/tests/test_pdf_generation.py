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
