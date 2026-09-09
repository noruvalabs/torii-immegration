"""Test dummy document generation for all immigration document types."""

from __future__ import annotations

import pymupdf  # type: ignore

from torii_api.services.dummy_generator import generate_dummy_pdf
from torii_api.services.ocr_extractor import (
    extract_text_with_pymupdf,
    parse_structured_fields_from_text,
)

ALL_DOC_TYPES = [
    "passport",
    "photo",
    "bank_statement",
    "proof_of_funds",
    "flight_itinerary",
    "travel_itinerary",
    "employment_letter",
    "employment_contract",
    "residence_card",
    "tax_return",
]


def test_generate_all_dummy_doc_types():
    """Verify each document type generates valid PDF bytes with extractable text."""
    for dt in ALL_DOC_TYPES:
        pdf_bytes, filename, default_name = generate_dummy_pdf(dt, user_name="Kenji Sato")
        assert len(pdf_bytes) > 500, f"Generated PDF for {dt} is too small"
        assert filename.endswith(".pdf")
        assert default_name

        # Verify PyMuPDF opens it cleanly
        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        assert len(doc) >= 1
        text = extract_text_with_pymupdf(pdf_bytes)
        doc.close()

        assert len(text) > 30, f"Extracted text for {dt} is empty"

        # Verify structured field extraction finds fields
        fields, conf = parse_structured_fields_from_text(dt, text, filename)
        assert len(fields) >= 1, f"Failed to parse structured fields for {dt}"
        assert conf >= 0.7
