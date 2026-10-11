"""Cross-validation for Indian Medical Visa document uploads.

Compares OCR-extracted fields from the hospital invitation letter against the
applicant's intake answers and passport data to catch mismatches before the
applicant pays a consular fee or visits the visa centre.
"""

from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Any

import structlog

log = structlog.get_logger()


# ── Public types ───────────────────────────────────────────────────────────────

class DocumentAlert:
    """One flagged issue on an uploaded document."""

    __slots__ = ("severity", "field", "message")

    def __init__(self, severity: str, field: str, message: str) -> None:
        self.severity = severity  # "error" | "warning" | "info"
        self.field = field
        self.message = message

    def as_dict(self) -> dict[str, str]:
        return {"severity": self.severity, "field": self.field, "message": self.message}


# ── Helpers ────────────────────────────────────────────────────────────────────

def _normalise(value: str | None) -> str:
    """Lowercase, collapse whitespace, strip punctuation for fuzzy matching."""
    if not value:
        return ""
    return re.sub(r"[^a-z0-9 ]", "", value.lower()).strip()


def _parse_date_loose(raw: str | None) -> date | None:
    """Best-effort parse of a date string from OCR or intake (YYYY-MM-DD, DD/MM/YYYY, etc.)."""
    if not raw:
        return None
    raw = raw.strip().replace("/", "-")
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%m-%d-%Y"):
        try:
            return date.fromisoformat(raw) if fmt == "%Y-%m-%d" else date(*map(int, raw.split("-")))
        except (ValueError, TypeError):
            continue
    return None


# ── Passport validity ──────────────────────────────────────────────────────────

def check_passport_validity(
    passport_expiry: str | None,
    *,
    min_months: int = 6,
    reference_date: date | None = None,
) -> list[DocumentAlert]:
    """Verify passport has enough remaining validity."""
    alerts: list[DocumentAlert] = []
    expiry = _parse_date_loose(passport_expiry)
    ref = reference_date or date.today()
    if expiry is None:
        alerts.append(
            DocumentAlert(
                "warning",
                "passport_expiry",
                "Could not parse passport expiry date. Please verify manually.",
            )
        )
        return alerts
    min_valid_until = ref + timedelta(days=min_months * 30)
    if expiry < ref:
        alerts.append(
            DocumentAlert(
                "error",
                "passport_expiry",
                f"Passport expired on {expiry.isoformat()}. A valid passport is required.",
            )
        )
    elif expiry < min_valid_until:
        alerts.append(
            DocumentAlert(
                "error",
                "passport_expiry",
                f"Passport expires on {expiry.isoformat()}, which is less than {min_months} months "
                f"from now. Indian consular authorities require at least {min_months} months validity.",
            )
        )
    return alerts


# ── Hospital letter cross-check ────────────────────────────────────────────────

def check_hospital_letter(
    ocr_fields: dict[str, Any],
    intake_answers: dict[str, Any],
) -> list[DocumentAlert]:
    """Cross-check the OCR-extracted hospital letter fields against the intake answers.

    Returns a list of alerts for any mismatches found:
    - Patient name on letter vs. intake full_name
    - Patient passport number on letter vs. intake passport_number
    - Hospital name on letter vs. intake destination_hospital
    """
    alerts: list[DocumentAlert] = []

    # 1. Patient name match
    letter_name = _normalise(_ocr_value(ocr_fields, "patient_name") or _ocr_value(ocr_fields, "full_name"))
    intake_name = _normalise(str(intake_answers.get("full_name") or ""))
    if letter_name and intake_name:
        if letter_name not in intake_name and intake_name not in letter_name:
            alerts.append(
                DocumentAlert(
                    "error",
                    "patient_name",
                    f"Patient name on hospital letter ('{_ocr_value(ocr_fields, 'patient_name') or _ocr_value(ocr_fields, 'full_name')}') "
                    f"does not match your intake name ('{intake_answers.get('full_name')}'). "
                    "The embassy will reject a mismatch.",
                )
            )
    elif not letter_name:
        alerts.append(
            DocumentAlert(
                "warning",
                "patient_name",
                "Could not detect patient name on the hospital letter. "
                "Ensure the letter clearly states the patient's full name.",
            )
        )

    # 2. Passport number match
    letter_passport = (_ocr_value(ocr_fields, "patient_passport_number") or "").upper().strip()
    intake_passport = str(intake_answers.get("passport_number") or "").upper().strip()
    if letter_passport and intake_passport:
        if letter_passport != intake_passport:
            alerts.append(
                DocumentAlert(
                    "error",
                    "passport_number",
                    f"Passport number on hospital letter ('{letter_passport}') does not match "
                    f"your passport number ('{intake_passport}'). This will cause rejection.",
                )
            )
    elif not letter_passport:
        alerts.append(
            DocumentAlert(
                "warning",
                "passport_number",
                "Could not detect passport number on the hospital letter. "
                "The letter must include the patient's passport number.",
            )
        )

    # 3. Hospital name match
    letter_hospital = _normalise(_ocr_value(ocr_fields, "hospital_name"))
    intake_hospital = _normalise(str(intake_answers.get("destination_hospital") or ""))
    if letter_hospital and intake_hospital:
        if letter_hospital not in intake_hospital and intake_hospital not in letter_hospital:
            # Fuzzy: check if major keywords overlap
            letter_words = set(letter_hospital.split())
            intake_words = set(intake_hospital.split())
            if not letter_words & intake_words:
                alerts.append(
                    DocumentAlert(
                        "warning",
                        "hospital_name",
                        f"Hospital name on the letter ('{_ocr_value(ocr_fields, 'hospital_name')}') "
                        f"may not match the hospital you selected ('{intake_answers.get('destination_hospital')}'). "
                        "Please verify.",
                    )
                )

    # 4. Doctor name presence
    if not _ocr_value(ocr_fields, "doctor_name"):
        alerts.append(
            DocumentAlert(
                "info",
                "doctor_name",
                "Could not detect the treating doctor's name on the hospital letter. "
                "Make sure the letter includes the doctor's name and registration details.",
            )
        )

    log.info(
        "medical_visa.hospital_letter_check",
        alerts_count=len(alerts),
        fields_found=list(ocr_fields.keys()),
    )
    return alerts


def _ocr_value(fields: dict[str, Any], key: str) -> str | None:
    """Extract the raw string value from an OCR field dict."""
    entry = fields.get(key)
    if isinstance(entry, dict):
        return entry.get("value")
    if isinstance(entry, str):
        return entry
    return None


# ── Full validation pipeline ──────────────────────────────────────────────────

def validate_medical_visa_documents(
    passport_ocr: dict[str, Any],
    hospital_letter_ocr: dict[str, Any],
    intake_answers: dict[str, Any],
) -> list[dict[str, str]]:
    """Run the full cross-validation suite for an Indian Medical Visa application.

    Returns a list of alert dicts suitable for returning in the API response.
    """
    alerts: list[DocumentAlert] = []

    # Passport validity check
    expiry = (
        _ocr_value(passport_ocr, "passport_expiry")
        or _ocr_value(passport_ocr, "expiry_date")
        or str(intake_answers.get("passport_expiry") or "")
    )
    alerts.extend(check_passport_validity(expiry))

    # Hospital letter cross-check
    alerts.extend(check_hospital_letter(hospital_letter_ocr, intake_answers))

    # Passport name vs. intake name
    passport_name = _normalise(_ocr_value(passport_ocr, "full_name"))
    intake_name = _normalise(str(intake_answers.get("full_name") or ""))
    if passport_name and intake_name:
        if passport_name not in intake_name and intake_name not in passport_name:
            alerts.append(
                DocumentAlert(
                    "error",
                    "full_name",
                    f"Name on passport ('{_ocr_value(passport_ocr, 'full_name')}') does not match "
                    f"the name you entered ('{intake_answers.get('full_name')}'). "
                    "All documents must use the exact same legal name.",
                )
            )

    return [a.as_dict() for a in alerts]
