"""OCR and PyMuPDF extraction service for visa documents."""

from __future__ import annotations

import re
from typing import Any

import httpx
import structlog

from torii_api.config import Settings

log = structlog.get_logger()


def extract_text_with_pymupdf(pdf_bytes: bytes) -> str:
    """Extract text from PDF using PyMuPDF (fitz)."""
    try:
        import pymupdf  # type: ignore

        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        pages: list[str] = []
        for page in doc:
            pages.append(str(page.get_text()))
        doc.close()
        return "\n".join(pages).strip()
    except Exception as e:
        log.warning("ocr.pymupdf_extraction_failed", error=str(e))
        return ""


def parse_structured_fields_from_text(
    doc_type: str, text: str, filename: str = ""
) -> tuple[dict[str, Any], float]:
    """Parse key-value immigration fields using robust regex and heuristic rules."""
    combined_text = f"{filename}\n{text}"
    fields: dict[str, Any] = {}

    # Common fields: Full Name
    name_patterns = [
        r"(?:full[ _]?name|holder(?:'s)?[ _]?name|applicant[ _]?name|surname[,\s]+given[ _]?names?|given[ _]?names?|name)\s*[:=]\s*([A-Za-z \-'\.]{3,40})(?:[\r\n,;]|$)",
        r"(?:p<[a-z]{3})([a-z\<\s]+)",  # MRZ name pattern
        r"Name\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)(?:[\r\n]|$)",
    ]
    for pat in name_patterns:
        if m := re.search(pat, combined_text, re.IGNORECASE):
            raw_name = m.group(1).replace("<", " ").strip()
            if len(raw_name) >= 3 and not re.match(
                r"^(passport|republic|state|document)", raw_name, re.I
            ):
                fields["full_name"] = {"value": raw_name.title(), "confidence": 0.9}
                break

    # Date of Birth
    dob_patterns = [
        r"(?:date[ _]?of[ _]?birth|dob|birth[ _]?date|born)\s*[:=]?\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})",
        r"(?:date[ _]?of[ _]?birth|dob|birth[ _]?date|born)\s*[:=]?\s*(\d{1,2}[-/]\d{1,2}[-/]\d{4})",
        r"(?:date[ _]?of[ _]?birth|dob)\s*[:=]?\s*([0-3]?\d\s+[A-Za-z]{3,9}\s+\d{4})",
    ]
    for pat in dob_patterns:
        if m := re.search(pat, combined_text, re.IGNORECASE):
            fields["date_of_birth"] = {"value": m.group(1).replace("/", "-"), "confidence": 0.9}
            break

    # Expiry Date / Passport Expiry
    exp_patterns = [
        r"(?:passport[ _]?expiry|expiry[ _]?date|expiration[ _]?date|valid[ _]?until|expires)\s*[:=]?\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})",
        r"(?:passport[ _]?expiry|expiry[ _]?date|expiration[ _]?date|valid[ _]?until|expires)\s*[:=]?\s*(\d{1,2}[-/]\d{1,2}[-/]\d{4})",
        r"(?:expiry[ _]?date|valid[ _]?until)\s*[:=]?\s*([0-3]?\d\s+[A-Za-z]{3,9}\s+\d{4})",
    ]
    for pat in exp_patterns:
        if m := re.search(pat, combined_text, re.IGNORECASE):
            fields["passport_expiry"] = {"value": m.group(1).replace("/", "-"), "confidence": 0.92}
            fields["expiry_date"] = {"value": m.group(1).replace("/", "-"), "confidence": 0.92}
            break

    # Nationality / Citizenship
    nat_patterns = [
        r"(?:nationality|citizenship|country[ _]?of[ _]?citizenship|national of)\s*[:=]\s*([A-Za-z ]+?)(?:[\r\n,;\.]|$)",
    ]
    for pat in nat_patterns:
        if m := re.search(pat, combined_text, re.IGNORECASE):
            clean_nat = m.group(1).strip()
            if len(clean_nat) >= 3 and not re.match(r"^(the|and|or|date|sex)", clean_nat, re.I):
                fields["nationality"] = {"value": clean_nat.title(), "confidence": 0.88}
                break

    # Document-specific extraction
    doc_type_clean = (doc_type or "").lower().strip()

    if doc_type_clean in ("passport", "identity"):
        passport_pats = [
            r"(?:passport(?:\s*(?:number|no|num))?\s*[:=#]?\s*)([A-Z0-9]{6,12})",
            r"(?:doc(?:ument)?[ _]?no\.?\s*[:=#]?\s*)([A-Z0-9]{6,12})",
            r"\b([A-Z]{1,2}[0-9]{7,9})\b",
        ]
        for pat in passport_pats:
            if m := re.search(pat, combined_text, re.IGNORECASE):
                val = m.group(1).upper()
                if not val.startswith("HTTP") and len(val) >= 6:
                    fields["passport_number"] = {"value": val, "confidence": 0.95}
                    break

        if m := re.search(
            r"(?:issuing[ _]?country|issuing[ _]?authority|authority)\s*[:=]\s*([A-Za-z\s]+)",
            combined_text,
            re.I,
        ):
            fields["issuing_country"] = {"value": m.group(1).strip().title(), "confidence": 0.85}

    elif doc_type_clean in ("residence_card", "national_id"):
        rc_pats = [
            r"(?:residence(?:\s*card)?(?:\s*(?:number|no))?\s*[:=#]?\s*)([A-Z0-9]{8,14})",
            r"(?:card(?:\s*(?:number|no))?\s*[:=#]?\s*)([A-Z0-9]{8,14})",
            r"\b([A-Z]{2}[0-9]{8}[A-Z]{2})\b",
        ]
        for pat in rc_pats:
            if m := re.search(pat, combined_text, re.IGNORECASE):
                fields["residence_card_number"] = {"value": m.group(1).upper(), "confidence": 0.92}
                break

        if m := re.search(
            r"(?:status[ _]?of[ _]?residence|residence[ _]?status|visa[ _]?status)\s*[:=]\s*([A-Za-z \(\)]+?)(?:[\r\n,;]|$)",
            combined_text,
            re.I,
        ):
            fields["status_of_residence"] = {
                "value": m.group(1).strip().title(),
                "confidence": 0.88,
            }

    elif doc_type_clean in ("bank_statement", "proof_of_funds", "tax_return"):
        bal_pats = [
            r"(?:closing[ _]?balance|ending[ _]?balance|available[ _]?balance|total[ _]?balance|balance|amount|funds)\s*[:=]?\s*([$¥€£A-Z]{0,3}\s*[0-9,]+(?:\.[0-9]{2})?)",
            r"([$¥€£]\s*[0-9,]+(?:\.[0-9]{2})?)",
        ]
        for pat in bal_pats:
            if m := re.search(pat, combined_text, re.IGNORECASE):
                fields["balance"] = {"value": m.group(1).strip(), "confidence": 0.88}
                break

        if m := re.search(
            r"(?:bank[ _]?name|institution|bank)\s*[:=]\s*([A-Za-z0-9 \.,]+?)(?:[\r\n,]|$)",
            combined_text,
            re.I,
        ):
            fields["bank_name"] = {"value": m.group(1).strip().title(), "confidence": 0.85}
        elif "bank" in combined_text.lower():
            if m := re.search(
                r"([A-Za-z ]+Bank(?:ing)?|MUFG|SMBC|Mizuho|JPMorgan|Chase|HSBC|Wells Fargo|Citibank)",
                combined_text,
                re.I,
            ):
                fields["bank_name"] = {"value": m.group(1).strip(), "confidence": 0.82}

        if m := re.search(
            r"(?:account[ _]?holder|account[ _]?name|customer[ _]?name)\s*[:=]\s*([A-Za-z \-'\.]+?)(?:[\r\n,;]|$)",
            combined_text,
            re.I,
        ):
            fields["account_holder"] = {"value": m.group(1).strip().title(), "confidence": 0.88}

    elif doc_type_clean in ("employment_letter", "employment_contract", "pay_slips"):
        if m := re.search(
            r"(?:employer(?:'s)?[ _]?name|company(?:'s)?[ _]?name|organization|sponsor)\s*[:=]\s*([A-Za-z0-9 \.,&]+?)(?:[\r\n,]|$)",
            combined_text,
            re.I,
        ):
            fields["employer_name"] = {"value": m.group(1).strip(), "confidence": 0.9}

        if m := re.search(
            r"(?:monthly[ _]?salary|remuneration|salary|gross[ _]?pay|basic[ _]?pay)\s*[:=]?\s*([$¥€£A-Z]{0,3}\s*[0-9,]+(?:\.[0-9]{2})?)",
            combined_text,
            re.I,
        ):
            fields["monthly_salary"] = {"value": m.group(1).strip(), "confidence": 0.86}

        if m := re.search(
            r"(?:position|designation|job[ _]?title|role)\s*[:=]\s*([A-Za-z \-]+?)(?:[\r\n,]|$)",
            combined_text,
            re.I,
        ):
            fields["position"] = {"value": m.group(1).strip().title(), "confidence": 0.86}

    elif doc_type_clean in ("flight_itinerary", "travel_itinerary", "hotel_booking"):
        if m := re.search(
            r"(?:departure(?:[ _]?date)?|departing)\s*[:=]?\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})",
            combined_text,
            re.I,
        ):
            fields["departure_date"] = {"value": m.group(1).replace("/", "-"), "confidence": 0.85}
        if m := re.search(
            r"(?:destination|arrival|flying to|destination city)\s*[:=]\s*([A-Za-z ,]+?)(?:[\r\n]|$)",
            combined_text,
            re.I,
        ):
            fields["destination"] = {"value": m.group(1).strip().title(), "confidence": 0.85}

    elif doc_type_clean in (
        "indian_hospital_letter",
        "hospital_invitation",
        "medical_referral",
        "local_medical_referral",
    ):
        # Hospital name
        hospital_pats = [
            r"(?:hospital(?:\s*name)?|medical\s*cent(?:er|re)|institute)\s*[:=]\s*([A-Za-z0-9 \-\.,&']+?)(?:[\r\n,;]|$)",
            r"((?:Apollo|Fortis|Max|Medanta|Narayana|Manipal|CMC|AIIMS|Tata Memorial|Aster|BLK|Artemis|Kokilaben)[A-Za-z0-9 \-\.,&']*?)(?:[\r\n,;]|$)",
        ]
        for pat in hospital_pats:
            if m := re.search(pat, combined_text, re.IGNORECASE):
                fields["hospital_name"] = {"value": m.group(1).strip(), "confidence": 0.90}
                break

        # Treating doctor name
        doctor_pats = [
            r"(?:treating\s*(?:doctor|physician)|doctor(?:'s)?\s*name|consultant|attending\s*(?:doctor|physician))\s*[:=]\s*(?:Dr\.?\s*)?([A-Za-z \-\.]+?)(?:[\r\n,;]|$)",
            r"(?:Dr\.?\s+)([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})(?:[\r\n,;]|$)",
        ]
        for pat in doctor_pats:
            if m := re.search(pat, combined_text, re.IGNORECASE):
                fields["doctor_name"] = {"value": m.group(1).strip().title(), "confidence": 0.85}
                break

        # Patient passport number on hospital letter (for cross-check)
        if m := re.search(
            r"(?:passport(?:\s*(?:number|no|num))?\s*[:=#]?\s*)([A-Z0-9]{6,12})",
            combined_text,
            re.IGNORECASE,
        ):
            val = m.group(1).upper()
            if not val.startswith("HTTP") and len(val) >= 6:
                fields["patient_passport_number"] = {"value": val, "confidence": 0.92}

        # Patient name on hospital letter (for cross-check)
        patient_pats = [
            r"(?:patient(?:'s)?\s*name|name\s*of\s*(?:the\s*)?patient)\s*[:=]\s*([A-Za-z \-'\.]{3,60})(?:[\r\n,;]|$)",
        ]
        for pat in patient_pats:
            if m := re.search(pat, combined_text, re.IGNORECASE):
                fields["patient_name"] = {"value": m.group(1).strip().title(), "confidence": 0.88}
                break

        # Diagnosis / treatment
        diag_pats = [
            r"(?:diagnosis|condition|treatment\s*(?:for|plan)?|medical\s*condition|ailment)\s*[:=]\s*([A-Za-z0-9 \-\.,/\(\)]+?)(?:[\r\n;]|$)",
        ]
        for pat in diag_pats:
            if m := re.search(pat, combined_text, re.IGNORECASE):
                fields["diagnosis"] = {"value": m.group(1).strip(), "confidence": 0.85}
                break

        # Hospital registration number
        if m := re.search(
            r"(?:registration(?:\s*(?:number|no))?|reg\.?\s*no\.?|license\s*no\.?)\s*[:=#]?\s*([A-Z0-9\-/]{4,20})",
            combined_text,
            re.IGNORECASE,
        ):
            fields["hospital_registration_number"] = {
                "value": m.group(1).strip().upper(),
                "confidence": 0.85,
            }

    confidence = 0.9 if len(fields) >= 3 else (0.8 if len(fields) >= 1 else 0.5)
    return fields, confidence


async def extract_document_metadata(
    file_bytes: bytes,
    doc_type: str,
    filename: str,
    content_type: str,
    settings: Settings | None = None,
) -> tuple[dict[str, Any], float]:
    """Main extraction pipeline:
    1. For PDFs: Use PyMuPDF to extract text directly from the PDF file.
    2. Try AI service (torii_ai /ai/ocr/extract-file) if available.
    3. Apply robust regex & semantic heuristics to generate structured metadata.
    """
    is_pdf = (
        content_type == "application/pdf"
        or filename.lower().endswith(".pdf")
        or file_bytes[:4] == b"%PDF"
    )
    extracted_text = ""

    if is_pdf:
        extracted_text = extract_text_with_pymupdf(file_bytes)
        log.info("ocr.pymupdf_extracted_text", length=len(extracted_text), filename=filename)

    ai_fields: dict[str, Any] = {}
    ai_confidence = 0.0

    # Try torii_ai OCR service if configured
    ai_url = (
        getattr(settings, "ai_service_url", "http://localhost:8001")
        if settings
        else "http://localhost:8001"
    )
    if ai_url:
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                files = {"file": (filename, file_bytes, content_type or "application/octet-stream")}
                data = {"doc_type": doc_type}
                resp = await client.post(
                    f"{ai_url.rstrip('/')}/ai/ocr/extract-file", files=files, data=data
                )
                if resp.status_code == 200:
                    ai_data = resp.json()
                    raw_fields = ai_data.get("fields", {})
                    for k, v in raw_fields.items():
                        if isinstance(v, dict) and "value" in v:
                            ai_fields[k] = v
                        elif isinstance(v, str):
                            ai_fields[k] = {"value": v, "confidence": 0.85}
                    if ai_fields:
                        ai_confidence = 0.92
                        log.info("ocr.ai_service_success", fields=list(ai_fields.keys()))
        except Exception as e:
            log.debug("ocr.ai_service_skipped_or_failed", error=str(e))

    # Regex & heuristic extraction based on PDF text or filename hints
    regex_fields, regex_confidence = parse_structured_fields_from_text(
        doc_type=doc_type,
        text=extracted_text,
        filename=filename,
    )

    # Merge AI fields with regex fields (AI takes priority when available)
    merged_fields = {**regex_fields, **ai_fields}
    overall_confidence = max(ai_confidence, regex_confidence) if merged_fields else 0.5

    return merged_fields, overall_confidence
