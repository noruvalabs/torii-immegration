"""Vietnam eVisa payload mapping and fail-closed portal signals.

Official portal: https://evisa.gov.vn (Immigration Department, Ministry of Public Security).

This module does not invent confirmation numbers. A code is accepted only when it is
extracted from portal page text and does not match Torii's old simulated prefixes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

VN_PORTAL_URL = "https://evisa.gov.vn"
VN_PORTAL_NAME = "Vietnam Immigration Department eVisa (evisa.gov.vn)"

# Reject the simulated receipts the previous worker invented.
_FORBIDDEN_REFERENCE_PREFIXES = ("VN-EVISA-", "TORII-", "EVISA-")

_CHALLENGE_HINTS = (
    "recaptcha",
    "h-captcha",
    "hcaptcha",
    "g-recaptcha",
    "cf-challenge",
    "challenges.cloudflare.com",
    "turnstile",
    "captcha",
    "security code",
    "verification code",
    "access denied",
    "unusual traffic",
    "please verify you are",
)

_CONFIRMATION_PATTERNS = (
    re.compile(
        r"(?:registration|application|declaration|e-?visa)\s*"
        r"(?:code|number|no\.?|id)\s*[:#]?\s*([A-Z0-9][A-Z0-9\-]{5,24})",
        re.IGNORECASE,
    ),
    re.compile(r"\b(EV[A-Z0-9]{6,20})\b"),
)

# Accessible English labels as published on the 2025–2026 evisa.gov.vn apply flow.
# Vietnamese labels are included so a locale switch still matches.
FIELD_LABELS: dict[str, tuple[str, ...]] = {
    "surname": ("Surname", "Family name", "Họ"),
    "given_names": ("Middle and Given Name", "Given name", "First name", "Tên"),
    "date_of_birth": ("Date of Birth", "Date of birth", "Ngày sinh"),
    "sex": ("Sex", "Gender", "Giới tính"),
    "nationality": ("Nationality", "Quốc tịch"),
    "email": ("Email", "E-mail", "Thư điện tử"),
    "religion": ("Religion", "Tôn giáo"),
    "place_of_birth": ("Place of Birth", "Place of birth", "Nơi sinh"),
    "passport_number": ("Passport Number", "Passport number", "Số hộ chiếu"),
    "issuing_authority": ("Issuing Authority", "Issuing authority", "Cơ quan cấp"),
    "passport_type": ("Passport Type", "Passport type", "Loại hộ chiếu"),
    "passport_issue_date": ("Date of Issue", "Date of issue", "Ngày cấp"),
    "passport_expiry": ("Expiry Date", "Date of Expiry", "Expiry date", "Ngày hết hạn"),
    "permanent_address": (
        "Permanent Residential Address",
        "Permanent residential address",
        "Địa chỉ thường trú",
    ),
    "contact_address": ("Contact Address", "Contact address", "Địa chỉ liên hệ"),
    "telephone": ("Telephone Number", "Telephone", "Phone", "Điện thoại"),
    "emergency_name": ("Emergency Contact Name", "Emergency contact name"),
    "emergency_address": ("Emergency Contact Residential Address", "Emergency contact address"),
    "emergency_phone": ("Emergency Contact Telephone Number", "Emergency contact telephone"),
    "emergency_relationship": ("Emergency Contact Relationship", "Emergency contact relationship"),
    "purpose_of_entry": ("Purpose of Entry", "Purpose of entry", "Mục đích nhập cảnh"),
    "entry_date": ("Intended Date of Entry", "Intended date of entry", "Ngày dự kiến nhập cảnh"),
    "length_of_stay": (
        "Intended Length of Stay in Viet Nam",
        "Intended length of stay",
        "Thời gian lưu trú",
    ),
    "address_in_vietnam": (
        "Residential Address in Vietnam",
        "Residential address in Viet Nam",
        "Địa chỉ cư trú tại Việt Nam",
    ),
    "entry_gate": ("Intended border gate at entry", "Intended Border Gate of Entry"),
    "exit_gate": ("Intended Border Gate of Exit", "Intended border gate of exit"),
}

START_CLICK_PATTERNS = (
    r"Apply now",
    r"For foreign individuals",
    r"E-visa",
    r"I agree",
    r"Confirm",
    r"Next",
    r"Continue",
)

REQUIRED_PAYLOAD_KEYS = (
    "surname",
    "given_names",
    "passport_number",
    "date_of_birth",
    "nationality",
    "email",
    "entry_date",
)


@dataclass
class VietnamEvisaPayload:
    """Applicant data mapped onto the public evisa.gov.vn field set."""

    values: dict[str, str] = field(default_factory=dict)
    missing_required: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def is_complete(self) -> bool:
        return not self.missing_required


def _first_str(source: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = source.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def split_passport_name(full_name: str) -> tuple[str, str]:
    """Split a display name into (surname, given names).

    Intake usually stores Western order (given names, then family name). The last
    token is treated as surname. Prefer explicit surname/given keys when present.
    """
    parts = [p for p in full_name.strip().split() if p]
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], parts[0]
    return parts[-1], " ".join(parts[:-1])


def to_vn_date(value: str) -> str:
    """Convert ISO or already-local dates to DD/MM/YYYY as used on evisa.gov.vn."""
    text = value.strip()
    if not text:
        return ""
    iso = re.match(r"^(\d{4})-(\d{2})-(\d{2})", text)
    if iso:
        year, month, day = iso.groups()
        return f"{day}/{month}/{year}"
    slash = re.match(r"^(\d{2})/(\d{2})/(\d{4})$", text)
    if slash:
        return text
    return text


def normalize_sex(value: str) -> str:
    lowered = value.strip().lower()
    if lowered in {"m", "male", "nam"}:
        return "Male"
    if lowered in {"f", "female", "nữ", "nu"}:
        return "Female"
    return value.strip()


def build_payload(
    intake: dict[str, Any] | None, *, email_fallback: str = ""
) -> VietnamEvisaPayload:
    answers = intake or {}
    full_name = _first_str(answers, "full_name", "applicant_name", "name")
    surname = _first_str(answers, "surname", "family_name", "last_name")
    given = _first_str(answers, "given_names", "given_name", "first_name", "middle_and_given_name")
    if not surname or not given:
        split_surname, split_given = split_passport_name(full_name)
        surname = surname or split_surname
        given = given or split_given

    values = {
        "surname": surname,
        "given_names": given,
        "date_of_birth": to_vn_date(_first_str(answers, "date_of_birth", "dob", "birth_date")),
        "sex": normalize_sex(_first_str(answers, "sex", "gender")),
        "nationality": _first_str(answers, "nationality", "citizenship", "passport_nationality"),
        "email": _first_str(answers, "email", "applicant_email") or email_fallback.strip(),
        "religion": _first_str(answers, "religion") or "None",
        "place_of_birth": _first_str(answers, "place_of_birth", "birth_place"),
        "passport_number": _first_str(answers, "passport_number", "passport_no"),
        "issuing_authority": _first_str(answers, "issuing_authority", "passport_issuer"),
        "passport_type": _first_str(answers, "passport_type") or "Ordinary",
        "passport_issue_date": to_vn_date(
            _first_str(answers, "passport_issue_date", "date_of_issue")
        ),
        "passport_expiry": to_vn_date(
            _first_str(answers, "passport_expiry", "passport_expiry_date", "expiry_date")
        ),
        "permanent_address": _first_str(
            answers, "permanent_address", "home_address", "residential_address"
        ),
        "contact_address": _first_str(answers, "contact_address", "mailing_address"),
        "telephone": _first_str(answers, "telephone", "phone", "mobile", "phone_number"),
        "emergency_name": _first_str(answers, "emergency_contact_name", "emergency_name"),
        "emergency_address": _first_str(answers, "emergency_contact_address"),
        "emergency_phone": _first_str(answers, "emergency_contact_phone"),
        "emergency_relationship": _first_str(answers, "emergency_contact_relationship"),
        "purpose_of_entry": _first_str(answers, "purpose_of_entry", "travel_purpose") or "Tourism",
        "entry_date": to_vn_date(
            _first_str(answers, "intended_entry_date", "entry_date", "travel_date")
        ),
        "length_of_stay": _first_str(answers, "length_of_stay", "stay_days", "intended_stay_days"),
        "address_in_vietnam": _first_str(
            answers, "address_in_vietnam", "vietnam_address", "hotel_address"
        ),
        "entry_gate": _first_str(answers, "entry_gate", "intended_entry_gate"),
        "exit_gate": _first_str(answers, "exit_gate", "intended_exit_gate"),
    }
    if not values["contact_address"]:
        values["contact_address"] = values["permanent_address"]

    missing = [key for key in REQUIRED_PAYLOAD_KEYS if not values.get(key)]
    notes: list[str] = []
    if not values["place_of_birth"]:
        notes.append("place_of_birth is blank; the portal may block Next until it is filled.")
    if not values["length_of_stay"]:
        notes.append("length_of_stay is blank.")
    if not values["address_in_vietnam"]:
        notes.append("address_in_vietnam is blank.")

    return VietnamEvisaPayload(values=values, missing_required=missing, notes=notes)


def page_has_challenge(html: str, url: str = "") -> bool:
    blob = f"{url}\n{html}".lower()
    return any(hint in blob for hint in _CHALLENGE_HINTS)


def extract_confirmation_code(html: str) -> str | None:
    """Return a portal registration code from page text, or None.

    Never returns the simulated prefixes the old worker generated.
    """
    if not html:
        return None
    for pattern in _CONFIRMATION_PATTERNS:
        match = pattern.search(html)
        if not match:
            continue
        code = match.group(1).strip().upper()
        if any(
            code.startswith(prefix.rstrip("-")) or code.startswith(prefix)
            for prefix in _FORBIDDEN_REFERENCE_PREFIXES
        ):
            continue
        if code.startswith("VN-EVISA"):
            continue
        if len(code) < 6:
            continue
        return code
    return None
