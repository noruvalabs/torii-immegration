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
        pages.append(str(page.get_text()))
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
    """Fallback regex and KV extraction when vision model is unavailable."""
    import re

    text = hint_text or Path(filename).stem.replace("_", " ").replace("-", " ")
    fields: dict[str, ExtractedValue] = {}

    MONTHS_MAP = {
        "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3,
        "april": 4, "apr": 4, "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7,
        "august": 8, "aug": 8, "september": 9, "sep": 9, "sept": 9, "october": 10, "oct": 10,
        "november": 11, "nov": 11, "december": 12, "dec": 12,
    }

    DEMONYM_TO_COUNTRY = {
        "bangladeshi": "Bangladesh", "japanese": "Japan", "american": "United States",
        "indian": "India", "chinese": "China", "filipino": "Philippines", "vietnamese": "Vietnam",
        "nepalese": "Nepal", "nepali": "Nepal", "sri lankan": "Sri Lanka", "korean": "South Korea",
        "south korean": "South Korea", "british": "United Kingdom", "canadian": "Canada",
        "australian": "Australia", "german": "Germany", "french": "France", "pakistani": "Pakistan",
    }

    def _normalize_date(val: str) -> str:
        s = val.strip().replace(",", " ")
        if m := re.match(r"^(\d{4})[-/](\d{1,2})[-/](\d{1,2})$", s):
            return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
        if m := re.match(r"^(\d{1,2})[-/](\d{1,2})[-/](\d{4})$", s):
            return f"{int(m.group(3)):04d}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
        parts = s.split()
        if len(parts) == 3:
            if parts[0].isdigit() and parts[1].lower() in MONTHS_MAP and parts[2].isdigit():
                return f"{int(parts[2]):04d}-{MONTHS_MAP[parts[1].lower()]:02d}-{int(parts[0]):02d}"
            if parts[0].lower() in MONTHS_MAP and parts[1].isdigit() and parts[2].isdigit():
                return f"{int(parts[2]):04d}-{MONTHS_MAP[parts[0].lower()]:02d}-{int(parts[1]):02d}"
        return val.replace("/", "-")

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    kv: dict[str, str] = {}
    for i, line in enumerate(lines):
        if ":" in line:
            k, v = line.split(":", 1)
            if k.strip() and v.strip():
                kv[k.strip().lower()] = v.strip()
        elif "=" in line:
            k, v = line.split("=", 1)
            if k.strip() and v.strip():
                kv[k.strip().lower()] = v.strip()
        if i + 1 < len(lines):
            if len(line) <= 45 and not line.endswith(":"):
                kv[line.lower()] = lines[i + 1]

    # Extract Full Name
    for k in ("full name", "applicant name", "holder name", "name", "full legal name"):
        if k in kv:
            v = kv[k].splitlines()[0].strip()
            if len(v) >= 3 and not re.match(r"^(passport|republic|state|document|field|sample|dummy)", v, re.I):
                fields["full_name"] = ExtractedValue(value=v.title(), confidence=0.95)
                break

    if "full_name" not in fields:
        if name_match := re.search(
            r"(?:full[ _]?name|holder(?:'s)?[ _]?name|applicant[ _]?name|name)\s*[:=]\s*([^\n,;]+)", text, re.IGNORECASE
        ):
            raw = name_match.group(1).splitlines()[0].strip()
            if len(raw) >= 3 and not re.match(r"^(passport|republic|state|document|field|sample|dummy)", raw, re.I):
                fields["full_name"] = ExtractedValue(value=raw.title(), confidence=0.9)

    # Extract Date of Birth
    for k in ("date of birth", "dob", "birth date"):
        if k in kv:
            fields["date_of_birth"] = ExtractedValue(value=_normalize_date(kv[k]), confidence=0.95)
            break

    if "date_of_birth" not in fields:
        if dob_match := re.search(
            r"(?:date[ _]?of[ _]?birth|dob|birth[ _]?date)\s*[:=]?\s*([0-3]?\d\s+[A-Za-z]{3,9}\s+\d{4}|\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{4})",
            text,
            re.IGNORECASE,
        ):
            fields["date_of_birth"] = ExtractedValue(
                value=_normalize_date(dob_match.group(1)), confidence=0.9
            )

    # Extract Expiry Date / Passport Expiry
    for k in ("passport expiry", "expiry date", "expiration date", "valid until"):
        if k in kv:
            fields["passport_expiry"] = ExtractedValue(value=_normalize_date(kv[k]), confidence=0.95)
            break

    if "passport_expiry" not in fields:
        if exp_match := re.search(
            r"(?:passport[ _]?expiry|expiry[ _]?date|expiration[ _]?date|valid[ _]?until)\s*[:=]?\s*([0-3]?\d\s+[A-Za-z]{3,9}\s+\d{4}|\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{4})",
            text,
            re.IGNORECASE,
        ):
            fields["passport_expiry"] = ExtractedValue(
                value=_normalize_date(exp_match.group(1)), confidence=0.9
            )

    # Extract Nationality
    for k in ("nationality", "citizenship", "country of citizenship"):
        if k in kv:
            c = kv[k].strip().lower()
            val = DEMONYM_TO_COUNTRY.get(c, kv[k].strip().title())
            fields["nationality"] = ExtractedValue(value=val, confidence=0.92)
            break

    if "nationality" not in fields:
        if nat_match := re.search(
            r"(?:nationality|citizenship|country[ _]?of[ _]?citizenship)\s*[:=]\s*([A-Za-z\s]+)",
            text,
            re.IGNORECASE,
        ):
            c = nat_match.group(1).strip().lower()
            val = DEMONYM_TO_COUNTRY.get(c, nat_match.group(1).strip().title())
            fields["nationality"] = ExtractedValue(value=val, confidence=0.88)

    INVALID_PASSPORT_WORDS = {
        "PASSPORT", "PASSEPORT", "DOCUMENT", "REPUBLIC", "TRAVEL",
        "NATIONAL", "GOVERNMENT", "JAPAN", "MINISTRY", "UNITED",
        "STATES", "OFFICIAL", "SPECIMEN", "AUTHORITY", "DUMMY",
    }
    INVALID_RC_WORDS = {
        "RESIDENCE", "RESIDENT", "ENGINEER", "MINISTRY", "JUSTICE",
        "GOVERNMENT", "PERMISSION", "SPECIMEN", "HUMANITIES",
    }

    # Direct KV for passport number
    for k in ("passport number", "passport no", "passport num"):
        if k in kv:
            v_p = kv[k].strip().upper()
            if v_p not in INVALID_PASSPORT_WORDS and any(c.isdigit() for c in v_p) and len(v_p) >= 6:
                fields["passport_number"] = ExtractedValue(value=v_p, confidence=0.95)
                break

    if doc_type == "passport":
        if mrz := re.search(r"(?:^|\n)([A-Z0-9]{6,10})<*[0-9][A-Z]{3}[0-9]{6}", text):
            mrz_val = mrz.group(1).upper()
            if mrz_val not in INVALID_PASSPORT_WORDS and any(c.isdigit() for c in mrz_val) and len(mrz_val) >= 6:
                fields["passport_number"] = ExtractedValue(value=mrz_val, confidence=0.98)

        if "passport_number" not in fields:
            passport_pats = [
                r"(?:passport\s*(?:number|no|num|\#)|doc(?:ument)?\s*(?:number|no|\#))\s*[:=#\-]\s*([A-Z0-9]{6,12})",
                r"(?:passport\s*(?:number|no|num))\s+([A-Z0-9]{6,12})",
                r"\b([A-Z]{1,2}[0-9]{7,9})\b",
            ]
            for pat in passport_pats:
                if match := re.search(pat, text, re.IGNORECASE):
                    val = match.group(1).upper()
                    if (
                        val not in INVALID_PASSPORT_WORDS
                        and any(c.isdigit() for c in val)
                        and len(val) >= 6
                    ):
                        fields["passport_number"] = ExtractedValue(value=val, confidence=0.95)
                        break

    elif doc_type == "residence_card":
        rc_pats = [
            r"(?:card\s*(?:number|no|num|\#)|residence\s*card\s*(?:number|no|num|\#))\s*[:=#\-]\s*([A-Z0-9]{8,14})",
            r"\b([A-Z]{2}[0-9]{8}[A-Z]{2})\b",
            r"(?:card\s*(?:number|no))\s+([A-Z0-9]{8,14})",
        ]
        for pat in rc_pats:
            if match := re.search(pat, text, re.IGNORECASE):
                val = match.group(1).upper()
                if (
                    val not in INVALID_RC_WORDS
                    and any(c.isdigit() for c in val)
                    and len(val) >= 8
                ):
                    fields["residence_card_number"] = ExtractedValue(value=val, confidence=0.95)
                    break
    elif doc_type == "proof_of_funds":
        if bal_match := re.search(
            r"(?:balance|amount|funds)\s*[:=]?\s*([$¥€£A-Z0-9,.]+)", text, re.IGNORECASE
        ):
            fields["balance"] = ExtractedValue(value=bal_match.group(1).strip(), confidence=0.85)
    else:
        if match := re.search(
            r"(?:employer|company|sponsor)\s*[:=]\s*([^\n,;]+)", text, re.IGNORECASE
        ):
            fields["employer_name"] = ExtractedValue(value=match.group(1).strip(), confidence=0.88)

    return OCRResult(fields=fields, needs_recapture=not fields)
