"""Small localized-string selector with predictable fallbacks (US-16)."""

from __future__ import annotations


def localized(value: str | dict[str, str] | None, locale: str, fallback: str = "en") -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        if locale in value and value[locale] is not None:
            return str(value[locale])
        if fallback in value and value[fallback] is not None:
            return str(value[fallback])
        for v in value.values():
            if v is not None:
                return str(v)
        return ""
    return str(value)
