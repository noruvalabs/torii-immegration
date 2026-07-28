"""Small localized-string selector with predictable fallbacks (US-16)."""

from __future__ import annotations


def localized(value: str | dict[str, str], locale: str, fallback: str = "en") -> str:
    if isinstance(value, str):
        return value
    if locale in value:
        return value[locale]
    if fallback in value:
        return value[fallback]
    return next(iter(value.values()), "")
