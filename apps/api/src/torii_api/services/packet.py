"""Deterministic downloadable packet snapshot assembly (US-10)."""

from __future__ import annotations

from typing import Any


def assemble_packet(
    case_reference: str,
    forms: list[dict[str, Any]],
    checklist: list[dict[str, Any]],
    submission_reference: str | None = None,
) -> dict[str, Any]:
    return {
        "case_reference": case_reference,
        "submission_reference": submission_reference,
        "forms": forms,
        "checklist": checklist,
    }
