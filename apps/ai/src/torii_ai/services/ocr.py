"""OCR extraction using LLM for document field extraction."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from torii_ai.config import get_settings

DocumentType = Literal[
    "passport", "residence_card", "employment_contract", "proof_of_funds", "travel_itinerary"
]


class ExtractedValue(BaseModel):
    value: str
    confidence: float


class OCRResult(BaseModel):
    fields: dict[str, ExtractedValue]
    needs_recapture: bool


DOC_TYPE_PROMPTS: dict[DocumentType, str] = {
    "passport": (
        "Extract the following fields from this passport document:\n"
        "- full_name: The holder's full name\n"
        "- passport_number: The passport number\n"
        "- nationality: Country of citizenship\n"
        "- date_of_birth: Date of birth (YYYY-MM-DD)\n"
        "- expiry_date: Passport expiry date (YYYY-MM-DD)\n"
        'Return as JSON with field names as keys and {"value": "...", "confidence": 0.0-1.0} objects.'
    ),
    "residence_card": (
        "Extract the following fields from this residence card document:\n"
        "- full_name: The holder's full name\n"
        "- residence_card_number: The card number\n"
        "- status: Residence status type\n"
        "- expiry_date: Card expiry date (YYYY-MM-DD)\n"
        'Return as JSON with field names as keys and {"value": "...", "confidence": 0.0-1.0} objects.'
    ),
    "employment_contract": (
        "Extract the following fields from this employment contract:\n"
        "- employer_name: Company/employer name\n"
        "- employee_name: Employee name\n"
        "- position: Job title/position\n"
        "- start_date: Employment start date (YYYY-MM-DD)\n"
        'Return as JSON with field names as keys and {"value": "...", "confidence": 0.0-1.0} objects.'
    ),
    "proof_of_funds": (
        "Extract the following fields from this financial document (bank statement, "
        "sponsorship letter, or proof of funds):\n"
        "- account_holder: Name of the account holder\n"
        "- bank_name: Bank or financial institution name\n"
        "- balance: Account balance or available amount (include currency)\n"
        "- statement_date: Date of the statement (YYYY-MM-DD)\n"
        "- account_number: Last 4 digits of account number if visible\n"
        'Return as JSON with field names as keys and {"value": "...", "confidence": 0.0-1.0} objects.'
    ),
    "travel_itinerary": (
        "Extract the following fields from this travel itinerary or booking document:\n"
        "- traveler_name: Full name of the traveler\n"
        "- departure_date: Departure date (YYYY-MM-DD)\n"
        "- return_date: Return date (YYYY-MM-DD) if round trip\n"
        "- destination: Destination city/country\n"
        "- airline_or_hotel: Airline name or hotel name\n"
        "- booking_reference: Booking/reference number\n"
        'Return as JSON with field names as keys and {"value": "...", "confidence": 0.0-1.0} objects.'
    ),
}


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract text from a PDF using PyMuPDF. Supports multilingual content."""
    import pymupdf

    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    pages: list[str] = []
    for page in doc:
        pages.append(page.get_text())
    doc.close()
    return "\n".join(pages).strip()


def extract_document_fields(
    doc_type: DocumentType, filename: str, hint_text: str | None
) -> OCRResult:
    """Extract fields from document using Groq vision model or hint text."""
    import json
    import re

    from openai import OpenAI

    if hint_text:
        quick = _fallback_extract(doc_type, filename, hint_text)
        if quick.fields:
            return quick

    settings = get_settings()

    api_key = settings.nvidia_api_key or settings.groq_api_key
    base_url = settings.nvidia_base_url if settings.nvidia_api_key else settings.groq_base_url
    model = settings.nvidia_model if settings.nvidia_api_key else settings.groq_model

    if not api_key:
        return _fallback_extract(doc_type, filename, hint_text)

    try:
        client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=5.0,
        )

        prompt = DOC_TYPE_PROMPTS.get(doc_type, DOC_TYPE_PROMPTS["passport"])

        if hint_text:
            prompt = f"Document text/content: {hint_text}\n\n{prompt}"

        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a document OCR assistant. Extract fields from document images and return valid JSON only.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=1024,
        )

        content = response.choices[0].message.content or ""

        json_match = re.search(r"\{[\s\S]*\}", content)
        if json_match:
            raw_fields = json.loads(json_match.group())
            fields = {}
            for key, val in raw_fields.items():
                if isinstance(val, dict) and "value" in val:
                    fields[key] = ExtractedValue(
                        value=str(val["value"]),
                        confidence=float(val.get("confidence", 0.8)),
                    )
                elif isinstance(val, str):
                    fields[key] = ExtractedValue(value=val, confidence=0.8)
            return OCRResult(fields=fields, needs_recapture=False)

    except Exception:
        pass

    return _fallback_extract(doc_type, filename, hint_text)


def _fallback_extract(doc_type: DocumentType, filename: str, hint_text: str | None) -> OCRResult:
    """Fallback regex extraction when vision model is unavailable."""
    import re

    text = hint_text or Path(filename).stem.replace("_", " ").replace("-", " ")
    fields: dict[str, ExtractedValue] = {}

    # Extract Full Name
    if name_match := re.search(r"(?:full[ _]?name|holder|applicant[ _]?name|name)\s*[:=]\s*([^\n,;]+)", text, re.IGNORECASE):
        fields["full_name"] = ExtractedValue(value=name_match.group(1).strip(), confidence=0.9)

    # Extract Date of Birth
    if dob_match := re.search(r"(?:date[ _]?of[ _]?birth|dob|birth[ _]?date)\s*[:=]?\s*(\d{4}[-/]\d{2}[-/]\d{2})", text, re.IGNORECASE):
        fields["date_of_birth"] = ExtractedValue(value=dob_match.group(1).replace("/", "-"), confidence=0.9)

    # Extract Expiry Date / Passport Expiry
    if exp_match := re.search(r"(?:passport[ _]?expiry|expiry[ _]?date|expiration[ _]?date|valid[ _]?until)\s*[:=]?\s*(\d{4}[-/]\d{2}[-/]\d{2})", text, re.IGNORECASE):
        fields["passport_expiry"] = ExtractedValue(value=exp_match.group(1).replace("/", "-"), confidence=0.9)

    # Extract Nationality
    if nat_match := re.search(r"(?:nationality|citizenship|country[ _]?of[ _]?citizenship)\s*[:=]\s*([A-Za-z\s]+)", text, re.IGNORECASE):
        fields["nationality"] = ExtractedValue(value=nat_match.group(1).strip(), confidence=0.88)

    if doc_type == "passport":
        if match := re.search(
            r"(?:passport(?:\s*(?:number|no))?\s*[:=#]?\s*)([A-Z0-9]{5,12})",
            text,
            re.IGNORECASE,
        ):
            fields["passport_number"] = ExtractedValue(
                value=match.group(1).upper(), confidence=0.92
            )
    elif doc_type == "residence_card":
        if match := re.search(
            r"(?:residence(?:\s*card)?(?:\s*(?:number|no))?\s*[:=#]?\s*)([A-Z0-9]{6,16})",
            text,
            re.IGNORECASE,
        ):
            fields["residence_card_number"] = ExtractedValue(
                value=match.group(1).upper(), confidence=0.9
            )
    elif doc_type == "proof_of_funds":
        if bal_match := re.search(r"(?:balance|amount|funds)\s*[:=]?\s*([$¥€£A-Z0-9,.]+)", text, re.IGNORECASE):
            fields["balance"] = ExtractedValue(value=bal_match.group(1).strip(), confidence=0.85)
    else:
        if match := re.search(r"(?:employer|company|sponsor)\s*[:=]\s*([^\n,;]+)", text, re.IGNORECASE):
            fields["employer_name"] = ExtractedValue(value=match.group(1).strip(), confidence=0.88)

    return OCRResult(fields=fields, needs_recapture=not fields)
