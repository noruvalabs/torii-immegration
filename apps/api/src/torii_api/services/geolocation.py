"""IP-based geolocation service for country auto-detection."""

from __future__ import annotations

import structlog
from fastapi import Request
from pydantic import BaseModel

log = structlog.get_logger()

# Free IP geolocation API (no key required)
GEO_API_URL = "https://ipapi.co/json/"


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


# Supported countries for destination selection
SUPPORTED_DESTINATIONS: dict[str, dict[str, str]] = {
    "US": {"name": "United States", "currency": "USD", "flag": "🇺🇸"},
    "UK": {"name": "United Kingdom", "currency": "GBP", "flag": "🇬🇧"},
    "CA": {"name": "Canada", "currency": "CAD", "flag": "🇨🇦"},
    "AU": {"name": "Australia", "currency": "AUD", "flag": "🇦🇺"},
    "DE": {"name": "Germany", "currency": "EUR", "flag": "🇩🇪"},
    "FR": {"name": "France", "currency": "EUR", "flag": "🇫🇷"},
    "JP": {"name": "Japan", "currency": "JPY", "flag": "🇯🇵"},
    "SG": {"name": "Singapore", "currency": "SGD", "flag": "🇸🇬"},
    "KR": {"name": "South Korea", "currency": "KRW", "flag": "🇰🇷"},
    "NZ": {"name": "New Zealand", "currency": "NZD", "flag": "🇳🇿"},
    "IE": {"name": "Ireland", "currency": "EUR", "flag": "🇮🇪"},
    "NL": {"name": "Netherlands", "currency": "EUR", "flag": "🇳🇱"},
    "SE": {"name": "Sweden", "currency": "SEK", "flag": "🇸🇪"},
    "NO": {"name": "Norway", "currency": "NOK", "flag": "🇳🇴"},
    "CH": {"name": "Switzerland", "currency": "CHF", "flag": "🇨🇭"},
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
}


async def detect_country_from_ip(request: Request) -> GeoLocation:
    """Detect country from client IP address using free geolocation API."""
    import httpx

    # Get client IP
    client_ip = request.client.host if request.client else "unknown"

    # Handle localhost/development
    if client_ip in ("127.0.0.1", "::1", "localhost", "unknown"):
        log.info("geo.localhost_detected", ip=client_ip)
        return GeoLocation(
            ip=client_ip,
            country_code="JP",
            country_name="Japan",
            is_japan=True,
        )

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(GEO_API_URL)
            resp.raise_for_status()
            data = resp.json()

        country_code = data.get("country_code", "JP")
        is_japan = country_code == "JP"

        log.info(
            "geo.detected",
            ip=client_ip,
            country_code=country_code,
            is_japan=is_japan,
        )

        return GeoLocation(
            ip=client_ip,
            country_code=country_code,
            country_name=data.get("country_name", "Unknown"),
            city=data.get("city"),
            region=data.get("region"),
            latitude=data.get("latitude"),
            longitude=data.get("longitude"),
            timezone=data.get("timezone"),
            is_japan=is_japan,
        )
    except Exception as e:
        log.error("geo.detection_failed", error=str(e))
        # Default to Japan on failure
        return GeoLocation(
            ip=client_ip,
            country_code="JP",
            country_name="Japan",
            is_japan=True,
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
        for code, info in SUPPORTED_DESTINATIONS.items()
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


def get_destinations_excluding(exclude_code: str) -> list[dict[str, str]]:
    """Get destinations excluding the user's current country."""
    return [
        {
            "code": code,
            "name": info["name"],
            "currency": info["currency"],
            "flag": info["flag"],
        }
        for code, info in SUPPORTED_DESTINATIONS.items()
        if code != exclude_code
    ]
