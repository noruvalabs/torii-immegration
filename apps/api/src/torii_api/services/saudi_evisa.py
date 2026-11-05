"""Saudi KSA Visa payload mapping, route guard, and fail-closed portal signals.

Official portal: https://ksavisa.sa (KSA Visa — unified national visa platform,
Ministry of Foreign Affairs). Unlike evisa.gov.vn, ksavisa.sa requires the
applicant's own account before an application can be filed, so an account
sign-in wall, an OTP prompt, a captcha, and the government-fee payment are all
manual-takeover signals — none of them is ever automated here.

Route rules are encoded from official Saudi sources (researched 2026-11-04)
and mirror the web route checker (apps/web/src/lib/apply-route.ts) and the
Phase 1 content pack (docs/jurisdictions/sa/tourist.new_application.yml):

- Saudi eVisa Terms & Conditions §3.3 "Permitted Country" list
  https://visa.visitsaudi.com/Home/TermsConditions
- Visit Saudi visa regulations (conditional eVisa / visa-on-arrival routes)
  https://www.visitsaudi.com/en/plan-your-trip/visa-regulations
- Visit Saudi Package Visa pilot (BD, EG, IN, ID, JO, MX, PK)
  https://www.visitsaudi.com/en/campaigns/package-visa
- Ministry of Hajj & Umrah / Nusuk (Umrah via licensed agents)
  https://umrah.nusuk.sa

This module does not invent confirmation numbers. A code is accepted only when
it is extracted from portal page text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from torii_api.services.vietnam_evisa import split_passport_name

SA_PORTAL_URL = "https://ksavisa.sa"
SA_PORTAL_NAME = "KSA Visa — Saudi Ministry of Foreign Affairs (ksavisa.sa)"

# Reject simulated receipts; a reference is stored only when read off the page.
_FORBIDDEN_REFERENCE_PREFIXES = ("TORII-", "SA-EVISA-")

# Passports eligible for the standard Saudi tourist eVisa by nationality alone
# (official eVisa Terms §3.3 Permitted Country list; same list as the Phase 1
# pack's eligibility rule and the web route checker).
EVISA_ELIGIBLE_PASSPORTS: frozenset[str] = frozenset(
    {
        "AL",
        "AD",
        "AU",
        "AT",
        "AZ",
        "BS",
        "BB",
        "BR",
        "BN",
        "BG",
        "CA",
        "CN",
        "HK",
        "MO",
        "HR",
        "CY",
        "CZ",
        "DK",
        "EE",
        "FI",
        "FR",
        "GE",
        "DE",
        "GR",
        "GD",
        "GY",
        "HU",
        "IS",
        "IE",
        "IT",
        "JP",
        "KZ",
        "KR",
        "XK",
        "KG",
        "LV",
        "LI",
        "LT",
        "LU",
        "MY",
        "MV",
        "MT",
        "MU",
        "MC",
        "ME",
        "NL",
        "NZ",
        "NO",
        "PA",
        "PL",
        "PT",
        "RO",
        "RU",
        "KN",
        "SM",
        "SC",
        "SG",
        "SK",
        "SI",
        "ZA",
        "ES",
        "SE",
        "CH",
        "TJ",
        "TH",
        "TR",
        "UA",
        "GB",
        "US",
        "UZ",
        "BA",
        "RS",
        "MX",
        "MK",
    }
)

# Passports in the Package Visa pilot: electronic visa bundled with a
# qualifying flight + hotel package bought from Ministry-approved providers —
# a provider checkout, not a ksavisa.sa filing.
PACKAGE_VISA_PASSPORTS: frozenset[str] = frozenset({"BD", "EG", "IN", "ID", "JO", "MX", "PK"})

# GCC member-state passports: visa-free entry to Saudi Arabia.
GCC_PASSPORTS: frozenset[str] = frozenset({"AE", "BH", "KW", "OM", "QA"})

# Routes the ksavisa.sa worker is allowed to file.
ONLINE_ROUTES: frozenset[str] = frozenset({"online_evisa", "online_conditional"})

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
    # ksavisa.sa files applications only inside the applicant's own account,
    # so a sign-in wall / OTP prompt is a manual-takeover signal, not a step
    # the worker may pass.
    "sign in",
    "sign-in",
    "log in",
    "login",
    "one-time password",
    "otp",
    "تسجيل الدخول",
)

_CONFIRMATION_PATTERNS = (
    re.compile(
        r"(?:application|request|visa)\s*"
        r"(?:number|no\.?|reference|id)\s*[:#]?\s*([A-Z0-9][A-Z0-9\-]{5,24})",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:reference|confirmation)\s*"
        r"(?:number|no\.?|code|id)\s*[:#]?\s*([A-Z0-9][A-Z0-9\-]{5,24})",
        re.IGNORECASE,
    ),
)

# Accessible labels for the KSA Visa visit-visa application (English + Arabic,
# so an Arabic-locale portal session still matches).
FIELD_LABELS: dict[str, tuple[str, ...]] = {
    "full_name": ("Full Name", "Full name", "الاسم الكامل"),
    "surname": ("Last Name", "Family Name", "Surname", "اسم العائلة"),
    "given_names": ("First Name", "Given Names", "Given name", "الاسم الأول"),
    "date_of_birth": ("Date of Birth", "Date of birth", "تاريخ الميلاد"),
    "nationality": ("Nationality", "الجنسية"),
    "residence_country": (
        "Country of Residence",
        "Current Residence",
        "Residence Country",
        "دولة الإقامة",
        "بلد الإقامة",
    ),
    "passport_number": ("Passport Number", "Passport number", "رقم جواز السفر"),
    "passport_expiry": (
        "Passport Expiry Date",
        "Passport Expiry",
        "Expiry Date",
        "تاريخ انتهاء جواز السفر",
    ),
    "email": ("Email Address", "Email", "E-mail", "البريد الإلكتروني"),
    "phone": (
        "Mobile Number",
        "Phone Number",
        "Phone",
        "رقم الجوال",
        "رقم الهاتف",
    ),
    "purpose": ("Purpose of Visit", "Visit Purpose", "Purpose", "الغرض من الزيارة"),
    "arrival_date": ("Arrival Date", "Date of Arrival", "تاريخ الوصول"),
    "length_of_stay": (
        "Length of Stay",
        "Duration of Stay",
        "مدة الإقامة",
    ),
    "accommodation": (
        "Accommodation",
        "Hotel Name",
        "Address in Saudi Arabia",
        "اسم الفندق",
        "عنوان السكن",
    ),
    "occupation": ("Occupation", "Profession", "المهنة"),
    "employment_status": ("Employment Status", "الحالة الوظيفية"),
}

START_CLICK_PATTERNS = (
    r"Apply for Visa",
    r"New Application",
    r"Visit Visa",
    r"Apply now",
    r"I agree",
    r"Continue",
    r"Next",
)

REQUIRED_PAYLOAD_KEYS = (
    "surname",
    "given_names",
    "passport_number",
    "date_of_birth",
    "nationality",
    "email",
    "arrival_date",
)


@dataclass
class SaudiEvisaPayload:
    """Applicant data mapped onto the KSA Visa (ksavisa.sa) field set."""

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


def _truthy(source: dict[str, Any], *keys: str) -> bool:
    """Read a boolean intake answer; accepts real bools and yes/true strings."""
    for key in keys:
        value = source.get(key)
        if value is None:
            continue
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value != 0
        text = str(value).strip().lower()
        if text in {"true", "yes", "y", "1"}:
            return True
        if text in {"false", "no", "n", "0", ""}:
            return False
    return False


def classify_route(answers: dict[str, Any] | None) -> str:
    """Classify how this applicant may apply for Saudi Arabia.

    Returns one of: "online_evisa", "online_conditional", "online_package",
    "in_person", "agent_umrah", "visa_free", "citizen". Only the two online
    routes may be filed by the ksavisa.sa worker; every other route fails
    closed in the job runner with a route-specific explanation.
    """
    answers = answers or {}
    nationality = _first_str(answers, "nationality", "citizenship").upper()
    purpose = _first_str(answers, "purpose_of_visit", "purpose").lower()
    has_condition = (
        _truthy(answers, "has_used_us_uk_schengen_visa", "used_western_visa")
        or _truthy(answers, "western_permanent_residence")
        or _truthy(answers, "gcc_residence")
    )

    if nationality == "SA":
        return "citizen"
    if nationality in GCC_PASSPORTS:
        return "visa_free"
    if nationality in EVISA_ELIGIBLE_PASSPORTS:
        return "online_evisa"
    if has_condition:
        return "online_conditional"
    if purpose == "umrah":
        return "agent_umrah"
    if nationality in PACKAGE_VISA_PASSPORTS:
        return "online_package"
    return "in_person"


# Why a non-online route cannot be filed by the ksavisa.sa worker. Keyed by
# classify_route() result; surfaced verbatim in the job's failure detail.
ROUTE_BLOCK_DETAILS: dict[str, str] = {
    "online_package": (
        "This passport qualifies for the Saudi Package Visa: an electronic visa "
        "bundled with a confirmed flight + 4-star hotel package bought from "
        "Ministry-approved providers (Reserval, Almosafer, Webook.com). It is a "
        "provider checkout, not a ksavisa.sa filing, so the portal worker does "
        "not file it."
    ),
    "in_person": (
        "This profile applies in person: a consular tourist visa via the Saudi "
        "embassy's visa service centre (Tasheer — appointment booked online, "
        "submission and biometrics in person). The ksavisa.sa worker only files "
        "online eVisa routes."
    ),
    "agent_umrah": (
        "Umrah for this passport is filed by a travel agent licensed by the "
        "Saudi Ministry of Hajj & Umrah on Nusuk Masar, tied to a verified "
        "hotel + transport + ticket package. There is no self-service "
        "ksavisa.sa application for this profile."
    ),
    "visa_free": (
        "GCC citizens enter Saudi Arabia visa-free — there is no visa "
        "application for the portal worker to file."
    ),
    "citizen": "Saudi citizens do not need a visa for Saudi Arabia.",
}


def build_payload(intake: dict[str, Any] | None, *, email_fallback: str = "") -> SaudiEvisaPayload:
    answers = intake or {}
    full_name = _first_str(answers, "full_name", "applicant_name", "name")
    surname = _first_str(answers, "surname", "family_name", "last_name")
    given = _first_str(answers, "given_names", "given_name", "first_name")
    if not surname or not given:
        split_surname, split_given = split_passport_name(full_name)
        surname = surname or split_surname
        given = given or split_given

    stay = _first_str(answers, "intended_length_of_stay_days", "length_of_stay", "stay_days")
    values = {
        "full_name": full_name,
        "surname": surname,
        "given_names": given,
        "date_of_birth": _first_str(answers, "date_of_birth", "dob", "birth_date"),
        "nationality": _first_str(
            answers, "nationality", "citizenship", "passport_nationality"
        ).upper(),
        "residence_country": _first_str(
            answers, "residence_country", "current_residence_country"
        ).upper(),
        "passport_number": _first_str(answers, "passport_number", "passport_no"),
        "passport_expiry": _first_str(
            answers, "passport_expiry_date", "passport_expiry", "expiry_date"
        ),
        "email": _first_str(answers, "email_address", "email", "applicant_email")
        or email_fallback.strip(),
        "phone": _first_str(answers, "phone_number", "phone", "mobile", "telephone"),
        "purpose": _first_str(answers, "purpose_of_visit", "purpose"),
        "arrival_date": _first_str(
            answers, "planned_arrival_date", "arrival_date", "intended_entry_date"
        ),
        "length_of_stay": stay,
        "accommodation": _first_str(answers, "accommodation_name", "accommodation", "hotel_name"),
        "occupation": _first_str(answers, "occupation", "profession"),
        "employment_status": _first_str(answers, "employment_status"),
    }

    missing = [key for key in REQUIRED_PAYLOAD_KEYS if not values.get(key)]
    notes: list[str] = []
    if not values["passport_expiry"]:
        notes.append("passport_expiry is blank; ksavisa.sa checks the 6-month validity rule.")
    if not values["accommodation"]:
        notes.append("accommodation is blank; the application asks where you will stay.")
    if not values["phone"]:
        notes.append("phone is blank; the portal account is verified against a mobile number.")
    if values["nationality"]:
        notes.append(
            "nationality is carried as an ISO code; the portal dropdown is matched by country name."
        )

    return SaudiEvisaPayload(values=values, missing_required=missing, notes=notes)


def page_has_challenge(html: str, url: str = "") -> bool:
    blob = f"{url}\n{html}".lower()
    return any(hint in blob for hint in _CHALLENGE_HINTS)


def extract_confirmation_code(html: str) -> str | None:
    """Return a portal application/reference number from page text, or None.

    Never returns a simulated prefix.
    """
    if not html:
        return None
    for pattern in _CONFIRMATION_PATTERNS:
        match = pattern.search(html)
        if not match:
            continue
        code = match.group(1).strip().upper()
        if any(code.startswith(prefix) for prefix in _FORBIDDEN_REFERENCE_PREFIXES):
            continue
        if len(code) < 6:
            continue
        return code
    return None
