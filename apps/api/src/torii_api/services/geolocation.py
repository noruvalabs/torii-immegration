"""IP-based geolocation service for country auto-detection."""

from __future__ import annotations

import structlog
from fastapi import Request
from pydantic import BaseModel

log = structlog.get_logger()


class GeoLocation(BaseModel):
    """Geolocation data from IP address."""

    ip: str
    country_code: str
    country_name: str
    city: str | None = None
    region: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    timezone: str | None = None
    is_japan: bool = False


# Country metadata — name, currency and flag — for every country this service can label,
# whether or not it is currently offered as a destination.
COUNTRY_META: dict[str, dict[str, str]] = {
    "JP": {"name": "Japan", "currency": "JPY", "flag": "🇯🇵"},
    "US": {"name": "United States", "currency": "USD", "flag": "🇺🇸"},
    "UK": {"name": "United Kingdom", "currency": "GBP", "flag": "🇬🇧"},
    "GB": {"name": "United Kingdom", "currency": "GBP", "flag": "🇬🇧"},
}

# Which of those are actually offered. US is parked (see
# docs/jurisdictions/us/_jurisdiction.yml); listing it here would put it back in the
# destination picker even though no live content pack backs it, so the applicant would
# pick a country and then hit an empty scope.
OFFERED_DESTINATIONS: tuple[str, ...] = ("JP", "UK", "GB")

# Retained under its original name for callers that only need the country labels.
SUPPORTED_DESTINATIONS = COUNTRY_META


def resolve_country_meta(code: str, name: str | None = None) -> dict[str, str]:
    """Resolve standard name, flag emoji, and currency for a country code."""
    code_upper = code.strip().upper()
    lookup_code = "UK" if code_upper == "GB" else code_upper

    if lookup_code in SUPPORTED_DESTINATIONS:
        dest = SUPPORTED_DESTINATIONS[lookup_code]
        return {
            "code": code_upper,
            "name": name or dest["name"],
            "currency": dest["currency"],
            "flag": dest["flag"],
        }
    if code_upper in SUPPORTED_NATIONALITIES:
        entry = SUPPORTED_NATIONALITIES[code_upper]
        return {
            "code": code_upper,
            "name": name or entry["name"],
            "currency": entry["currency"],
            "flag": entry["flag"],
        }

    # Generate flag emoji from 2-letter ISO code if available
    flag = "🌐"
    if len(code_upper) == 2 and code_upper.isalpha():
        flag = "".join(chr(127397 + ord(char)) for char in code_upper)

    return {
        "code": code_upper,
        "name": name or code_upper,
        "currency": "USD",
        "flag": flag,
    }


# Supported nationalities (country of origin / citizenship) for cross-border guidance.
# Destination codes are reused where possible, plus the most common origin countries.
SUPPORTED_NATIONALITIES: dict[str, dict[str, str]] = {
    **SUPPORTED_DESTINATIONS,
    "BD": {"name": "Bangladesh", "currency": "BDT", "flag": "🇧🇩"},
    "IN": {"name": "India", "currency": "INR", "flag": "🇮🇳"},
    "PK": {"name": "Pakistan", "currency": "PKR", "flag": "🇵🇰"},
    "LK": {"name": "Sri Lanka", "currency": "LKR", "flag": "🇱🇰"},
    "NP": {"name": "Nepal", "currency": "NPR", "flag": "🇳🇵"},
    "VN": {"name": "Vietnam", "currency": "VND", "flag": "🇻🇳"},
    "TH": {"name": "Thailand", "currency": "THB", "flag": "🇹🇭"},
    "MY": {"name": "Malaysia", "currency": "MYR", "flag": "🇲🇾"},
    "ID": {"name": "Indonesia", "currency": "IDR", "flag": "🇮🇩"},
    "PH": {"name": "Philippines", "currency": "PHP", "flag": "🇵🇭"},
    "CN": {"name": "China", "currency": "CNY", "flag": "🇨🇳"},
    "TW": {"name": "Taiwan", "currency": "TWD", "flag": "🇹🇼"},
    "HK": {"name": "Hong Kong", "currency": "HKD", "flag": "🇭🇰"},
    "BR": {"name": "Brazil", "currency": "BRL", "flag": "🇧🇷"},
    "MX": {"name": "Mexico", "currency": "MXN", "flag": "🇲🇽"},
    "TR": {"name": "Turkey", "currency": "TRY", "flag": "🇹🇷"},
    "EG": {"name": "Egypt", "currency": "EGP", "flag": "🇪🇬"},
    "SA": {"name": "Saudi Arabia", "currency": "SAR", "flag": "🇸🇦"},
    "AE": {"name": "United Arab Emirates", "currency": "AED", "flag": "🇦🇪"},
}

# Visa types
VISA_TYPES: dict[str, dict[str, str]] = {
    "tourist": {
        "name": "Tourist / Visitor",
        "description": "Short-term stay for tourism or visiting",
    },
    "student": {"name": "Student", "description": "Study at an educational institution"},
    "work": {"name": "Work / Employment", "description": "Employment or business activities"},
}

# Application types
APPLICATION_TYPES: dict[str, dict[str, str]] = {
    "new": {"name": "New Visa", "description": "First-time application"},
    "renewal": {"name": "Renewal / Extension", "description": "Extend or renew existing visa"},
    "change_of_status": {
        "name": "Change of status",
        "description": "Switch to a different status (e.g. student to work)",
    },
}


async def detect_country_from_ip(request: Request) -> GeoLocation:
    """Detect country from client IP. Defaults to Bangladesh for dev."""
    client_ip = request.client.host if request.client else "unknown"

    log.info("geo.detected", ip=client_ip, country_code="BD", is_japan=False)

    return GeoLocation(
        ip=client_ip,
        country_code="BD",
        country_name="Bangladesh",
        city="Dhaka",
        is_japan=False,
    )


def get_supported_destinations() -> list[dict[str, str | bool]]:
    """Get list of supported destination countries."""
    return [
        {
            "code": code,
            "name": info["name"],
            "currency": info["currency"],
            "flag": info["flag"],
        }
        for code, info in COUNTRY_META.items()
        if code in OFFERED_DESTINATIONS
    ]


def get_visa_types() -> list[dict[str, str]]:
    """Get list of supported visa types."""
    return [
        {"code": code, "name": info["name"], "description": info["description"]}
        for code, info in VISA_TYPES.items()
    ]


def get_application_types() -> list[dict[str, str]]:
    """Get list of application types."""
    return [
        {"code": code, "name": info["name"], "description": info["description"]}
        for code, info in APPLICATION_TYPES.items()
    ]


def get_nationalities() -> list[dict[str, str]]:
    """Get list of supported nationalities (country of origin)."""
    return [
        {
            "code": code,
            "name": info["name"],
            "currency": info["currency"],
            "flag": info["flag"],
        }
        for code, info in SUPPORTED_NATIONALITIES.items()
    ]


def get_destinations_excluding(exclude_code: str) -> list[dict[str, str]]:
    """Get destinations excluding the user's current country."""
    return [
        {
            "code": code,
            "name": info["name"],
            "currency": info["currency"],
            "flag": info["flag"],
        }
        for code, info in COUNTRY_META.items()
        if code in OFFERED_DESTINATIONS and code != exclude_code
    ]
