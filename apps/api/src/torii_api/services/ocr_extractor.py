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


MONTHS_MAP = {
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sep": 9,
    "sept": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
}

DEMONYM_TO_COUNTRY = {
    "bangladeshi": "Bangladesh",
    "japanese": "Japan",
    "american": "United States",
    "indian": "India",
    "chinese": "China",
    "filipino": "Philippines",
    "vietnamese": "Vietnam",
    "nepalese": "Nepal",
    "nepali": "Nepal",
    "sri lankan": "Sri Lanka",
    "korean": "South Korea",
    "south korean": "South Korea",
    "british": "United Kingdom",
    "canadian": "Canada",
    "australian": "Australia",
    "german": "Germany",
    "french": "France",
    "pakistani": "Pakistan",
    "indonesian": "Indonesia",
    "malaysian": "Malaysia",
    "thai": "Thailand",
    "myanmarese": "Myanmar",
    "burmese": "Myanmar",
    "singaporean": "Singapore",
}


def normalize_date_to_iso(val: str) -> str:
    """Normalize any date format (e.g. 15 March 2002, 15/03/2002, 2002-03-15) to YYYY-MM-DD."""
    if not val:
        return ""
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


def extract_country_from_text(text: str) -> str:
    """Extract standard country name from text or city, country string."""
    clean = text.strip()
    lower = clean.lower()
    for dem, ctry in DEMONYM_TO_COUNTRY.items():
        if dem in lower:
            return ctry
    if "," in clean:
        parts = [p.strip() for p in clean.split(",")]
        if len(parts) > 1:
            last = parts[-1]
            return DEMONYM_TO_COUNTRY.get(last.lower(), last.title())
    return DEMONYM_TO_COUNTRY.get(lower, clean.title())


def parse_structured_fields_from_text(
    doc_type: str, text: str, filename: str = ""
) -> tuple[dict[str, Any], float]:
    """Parse key-value immigration fields using robust table/block KV analysis and regex rules."""
    combined_text = f"{filename}\n{text}"
    fields: dict[str, Any] = {}

    # Pass 1: Parse key-value pairs from lines (supports 'Key: Value' and 2-line table blocks 'Key\nValue')
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
            next_line = lines[i + 1]
            if len(line) <= 45 and not line.endswith(":"):
                kv[line.lower()] = next_line

    # Common fields: Full Name
    # 1. From KV
    for k in (
        "full name",
        "applicant name",
        "holder name",
        "name",
        "full legal name",
        "taxpayer name",
    ):
        if k in kv:
            v = kv[k].splitlines()[0].strip()
            if len(v) >= 3 and not re.match(
                r"^(passport|republic|state|document|field|sample|dummy)", v, re.I
            ):
                fields["full_name"] = {"value": v.title(), "confidence": 0.95}
                break

    # 2. From Regex if not in KV
    if "full_name" not in fields:
        name_patterns = [
            r"(?:full[ _]?name|holder(?:'s)?[ _]?name|applicant[ _]?name|surname[,\s]+given[ _]?names?|given[ _]?names?)\s*[:=]\s*([A-Za-z \-'\.]{3,40})(?:[\r\n,;]|$)",
            r"(?:p<[a-z]{3})([a-z\<\s]+)",  # MRZ name pattern
            r"(?:^|[\r\n])Name[ \t]+([A-Z][a-z]+(?:[ \t]+[A-Z][a-z]+)+)(?:[\r\n]|$)",
        ]
        for pat in name_patterns:
            if m := re.search(pat, combined_text, re.IGNORECASE):
                raw_name = m.group(1).replace("<", " ").splitlines()[0].strip()
                if len(raw_name) >= 3 and not re.match(
                    r"^(passport|republic|state|document|field|sample|dummy)", raw_name, re.I
                ):
                    fields["full_name"] = {"value": raw_name.title(), "confidence": 0.9}
                    break

    # Date of Birth (normalized to YYYY-MM-DD)
    for k in ("date of birth", "dob", "birth date", "born"):
        if k in kv:
            iso_dob = normalize_date_to_iso(kv[k])
            if re.match(r"^\d{4}-\d{2}-\d{2}$", iso_dob):
                fields["date_of_birth"] = {"value": iso_dob, "confidence": 0.95}
                break

    if "date_of_birth" not in fields:
        dob_patterns = [
            r"(?:date[ _]?of[ _]?birth|dob|birth[ _]?date|born)\s*[:=]?\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})",
            r"(?:date[ _]?of[ _]?birth|dob|birth[ _]?date|born)\s*[:=]?\s*(\d{1,2}[-/]\d{1,2}[-/]\d{4})",
            r"(?:date[ _]?of[ _]?birth|dob)\s*[:=]?\s*([0-3]?\d\s+[A-Za-z]{3,9}\s+\d{4})",
        ]
        for pat in dob_patterns:
            if m := re.search(pat, combined_text, re.IGNORECASE):
                iso_dob = normalize_date_to_iso(m.group(1))
                fields["date_of_birth"] = {"value": iso_dob, "confidence": 0.9}
                break

    # Expiry Date / Passport Expiry (normalized to YYYY-MM-DD)
    for k in (
        "passport expiry",
        "expiry date",
        "expiration date",
        "valid until",
        "period of stay (expiry)",
    ):
        if k in kv:
            iso_exp = normalize_date_to_iso(kv[k])
            if re.match(r"^\d{4}-\d{2}-\d{2}$", iso_exp):
                fields["passport_expiry"] = {"value": iso_exp, "confidence": 0.95}
                fields["expiry_date"] = {"value": iso_exp, "confidence": 0.95}
                break

    if "passport_expiry" not in fields:
        exp_patterns = [
            r"(?:passport[ _]?expiry|expiry[ _]?date|expiration[ _]?date|valid[ _]?until|expires)\s*[:=]?\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})",
            r"(?:passport[ _]?expiry|expiry[ _]?date|expiration[ _]?date|valid[ _]?until|expires)\s*[:=]?\s*(\d{1,2}[-/]\d{1,2}[-/]\d{4})",
            r"(?:expiry[ _]?date|valid[ _]?until)\s*[:=]?\s*([0-3]?\d\s+[A-Za-z]{3,9}\s+\d{4})",
        ]
        for pat in exp_patterns:
            if m := re.search(pat, combined_text, re.IGNORECASE):
                iso_exp = normalize_date_to_iso(m.group(1))
                fields["passport_expiry"] = {"value": iso_exp, "confidence": 0.92}
                fields["expiry_date"] = {"value": iso_exp, "confidence": 0.92}
                break

    # Nationality / Citizenship
    for k in ("nationality", "citizenship", "country of citizenship", "national of"):
        if k in kv:
            clean_nat = extract_country_from_text(kv[k])
            if len(clean_nat) >= 3 and not re.match(
                r"^(the|and|or|date|sex|dummy)", clean_nat, re.I
            ):
                fields["nationality"] = {"value": clean_nat, "confidence": 0.92}
                break

    if "nationality" not in fields:
        nat_patterns = [
            r"(?:nationality|citizenship|country[ _]?of[ _]?citizenship|national of)\s*[:=]\s*([A-Za-z ]+?)(?:[\r\n,;\.]|$)",
        ]
        for pat in nat_patterns:
            if m := re.search(pat, combined_text, re.IGNORECASE):
                clean_nat = extract_country_from_text(m.group(1))
                if len(clean_nat) >= 3 and not re.match(
                    r"^(the|and|or|date|sex|dummy)", clean_nat, re.I
                ):
                    fields["nationality"] = {"value": clean_nat, "confidence": 0.88}
                    break

    # Sex / Gender (male / female)
    for k in ("sex", "gender"):
        if k in kv:
            v = kv[k].strip().lower()
            if v in ("male", "m"):
                fields["sex"] = {"value": "male", "confidence": 0.95}
                break
            elif v in ("female", "f"):
                fields["sex"] = {"value": "female", "confidence": 0.95}
                break

    if "sex" not in fields:
        if m := re.search(r"(?:sex|gender)\s*[:=\t]?\s*(male|female|m|f)\b", combined_text, re.I):
            v = m.group(1).lower()
            fields["sex"] = {"value": "male" if v in ("male", "m") else "female", "confidence": 0.9}

    # Marital Status (single / married / divorced / widowed)
    for k in ("marital status", "marital_status", "marital"):
        if k in kv:
            v = kv[k].strip().lower()
            if v in ("single", "married", "divorced", "widowed"):
                fields["marital_status"] = {"value": v, "confidence": 0.95}
                break

    if "marital_status" not in fields:
        if m := re.search(
            r"(?:marital[ _]?status)\s*[:=\t]?\s*(single|married|divorced|widowed)\b",
            combined_text,
            re.I,
        ):
            fields["marital_status"] = {"value": m.group(1).lower(), "confidence": 0.9}

    # Occupation / Profession
    for k in ("occupation", "profession", "job title", "current occupation"):
        if k in kv:
            v = kv[k].splitlines()[0].strip()
            if len(v) >= 2 and not re.match(r"^(field|sample|dummy)", v, re.I):
                fields["occupation"] = {"value": v.title(), "confidence": 0.92}
                break

    if "occupation" not in fields:
        if m := re.search(
            r"(?:occupation|profession|job[ _]?title|position)\s*[:=\t]\s*([A-Za-z \-\/]+?)(?:[\r\n;]|$)",
            combined_text,
            re.I,
        ):
            clean_occ = m.group(1).strip()
            if len(clean_occ) >= 3 and not re.match(
                r"^(field|sample|dummy|the|and)", clean_occ, re.I
            ):
                fields["occupation"] = {"value": clean_occ.title(), "confidence": 0.88}

    # Current Location / Residence Country
    for k in (
        "current residing",
        "current residence",
        "current location",
        "current country",
        "residing in",
    ):
        if k in kv:
            raw_loc = kv[k].splitlines()[0].strip()
            fields["current_residence"] = {"value": raw_loc, "confidence": 0.9}
            fields["current_country"] = {
                "value": extract_country_from_text(raw_loc),
                "confidence": 0.9,
            }
            break

    if "current_country" not in fields:
        if m := re.search(
            r"(?:current(?:ly)?[ _]?(?:residing|residence|location|country)|residing in)\s*[:=\t]\s*([A-Za-z0-9 ,\-]+?)(?:[\r\n;]|$)",
            combined_text,
            re.I,
        ):
            raw_loc = m.group(1).strip()
            fields["current_residence"] = {"value": raw_loc, "confidence": 0.88}
            fields["current_country"] = {
                "value": extract_country_from_text(raw_loc),
                "confidence": 0.88,
            }

    # Phone Number
    for k in ("phone number", "phone", "mobile number", "mobile", "contact number"):
        if k in kv:
            v = kv[k].splitlines()[0].strip()
            if any(c.isdigit() for c in v) and len(v) >= 7:
                fields["phone_number"] = {"value": v, "confidence": 0.9}
                break

    # Document-specific extraction
    doc_type_clean = (doc_type or "").lower().strip()

    INVALID_PASSPORT_WORDS = {
        "PASSPORT",
        "PASSEPORT",
        "DOCUMENT",
        "REPUBLIC",
        "TRAVEL",
        "NATIONAL",
        "GOVERNMENT",
        "JAPAN",
        "MINISTRY",
        "UNITED",
        "STATES",
        "OFFICIAL",
        "SPECIMEN",
        "AUTHORITY",
        "DUMMY",
    }
    INVALID_RC_WORDS = {
        "RESIDENCE",
        "RESIDENT",
        "ENGINEER",
        "MINISTRY",
        "JUSTICE",
        "GOVERNMENT",
        "PERMISSION",
        "SPECIMEN",
        "HUMANITIES",
    }

    # Also check KV for passport number directly
    for k in ("passport number", "passport no", "passport num", "travel document number"):
        if k in kv:
            val_p = kv[k].strip().upper()
            if (
                val_p not in INVALID_PASSPORT_WORDS
                and any(c.isdigit() for c in val_p)
                and len(val_p) >= 6
            ):
                fields["passport_number"] = {"value": val_p, "confidence": 0.95}
                break

    if doc_type_clean in ("passport", "identity"):
        # 1. MRZ line 2 (ICAO 9303 passports)
        if mrz := re.search(r"(?:^|\n)([A-Z0-9]{6,10})<*[0-9][A-Z]{3}[0-9]{6}", combined_text):
            mrz_val = mrz.group(1).upper()
            if (
                mrz_val not in INVALID_PASSPORT_WORDS
                and any(c.isdigit() for c in mrz_val)
                and len(mrz_val) >= 6
            ):
                fields["passport_number"] = {"value": mrz_val, "confidence": 0.98}

        if "passport_number" not in fields:
            passport_pats = [
                r"(?:passport\s*(?:number|no|num|\#)|doc(?:ument)?\s*(?:number|no|\#))\s*[:=#\-]\s*([A-Z0-9]{6,12})",
                r"(?:passport\s*(?:number|no|num))\s+([A-Z0-9]{6,12})",
                r"\b([A-Z]{1,2}[0-9]{7,9})\b",
            ]
            for pat in passport_pats:
                if m := re.search(pat, combined_text, re.IGNORECASE):
                    val = m.group(1).upper()
                    if (
                        val not in INVALID_PASSPORT_WORDS
                        and not val.startswith("HTTP")
                        and any(c.isdigit() for c in val)
                        and len(val) >= 6
                    ):
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
            r"(?:card\s*(?:number|no|num|\#)|residence\s*card\s*(?:number|no|num|\#))\s*[:=#\-]\s*([A-Z0-9]{8,14})",
            r"\b([A-Z]{2}[0-9]{8}[A-Z]{2})\b",
            r"(?:card\s*(?:number|no))\s+([A-Z0-9]{8,14})",
        ]
        for pat in rc_pats:
            if m := re.search(pat, combined_text, re.IGNORECASE):
                val = m.group(1).upper()
                if val not in INVALID_RC_WORDS and any(c.isdigit() for c in val) and len(val) >= 8:
                    fields["residence_card_number"] = {"value": val, "confidence": 0.95}
                    break

        if m := re.search(
            r"(?:status[ _]?of[ _]?residence|residence[ _]?status|visa[ _]?status)\s*[:=]\s*([A-Za-z0-9 \(\)\/\-]+?)(?:[\r\n,;]|$)",
            combined_text,
            re.I,
        ):
            fields["status_of_residence"] = {
                "value": m.group(1).strip().title(),
                "confidence": 0.88,
            }

        if m := re.search(
            r"(?:address|current[ _]?address|japan[ _]?address)\s*[:=]\s*([A-Za-z0-9 \-,]+?)(?:[\r\n;]|$)",
            combined_text,
            re.I,
        ):
            fields["current_japan_address"] = {"value": m.group(1).strip(), "confidence": 0.85}

    elif doc_type_clean in ("bank_statement", "proof_of_funds"):
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

        if m := re.search(
            r"(?:account[ _]?(?:number|no|num))\s*[:=]?\s*([0-9A-Z\-]{6,20})",
            combined_text,
            re.I,
        ):
            fields["account_number"] = {"value": m.group(1).strip(), "confidence": 0.88}

    elif doc_type_clean == "tax_return":
        if m := re.search(
            r"(?:tax[ _]?year|assessment[ _]?year|fiscal[ _]?year)\s*[:=]?\s*(\d{4})",
            combined_text,
            re.I,
        ):
            fields["tax_year"] = {"value": m.group(1).strip(), "confidence": 0.9}

        if m := re.search(
            r"(?:gross[ _]?salary|gross[ _]?remuneration|gross[ _]?income|annual[ _]?income|total[ _]?income)\s*[:=]?\s*([$¥€£A-Z]{0,3}\s*[0-9,]+(?:\.[0-9]{2})?)",
            combined_text,
            re.I,
        ):
            fields["annual_income"] = {"value": m.group(1).strip(), "confidence": 0.88}
            fields["gross_income"] = {"value": m.group(1).strip(), "confidence": 0.88}

        if m := re.search(
            r"(?:taxable[ _]?amount|taxable[ _]?income)\s*[:=]?\s*([$¥€£A-Z]{0,3}\s*[0-9,]+(?:\.[0-9]{2})?)",
            combined_text,
            re.I,
        ):
            fields["taxable_income"] = {"value": m.group(1).strip(), "confidence": 0.86}

        if m := re.search(
            r"(?:total[ _]?income[ _]?tax[ _]?paid|balance|tax[ _]?paid|paid[ _]?tax)\s*[:=]?\s*([$¥€£A-Z]{0,3}\s*[0-9,]+(?:\.[0-9]{2})?)",
            combined_text,
            re.I,
        ):
            fields["tax_paid"] = {"value": m.group(1).strip(), "confidence": 0.86}

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

        if m := re.search(
            r"(?:start[ _]?date|employment[ _]?start[ _]?date)\s*[:=]?\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})",
            combined_text,
            re.I,
        ):
            fields["start_date"] = {"value": m.group(1).replace("/", "-"), "confidence": 0.85}

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
