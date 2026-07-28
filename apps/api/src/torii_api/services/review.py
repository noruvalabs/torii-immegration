"""Packet consistency checks before assembly (US-09)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from torii_api.services.forms import is_stale


class ReviewFlag(BaseModel):
    code: str
    message: str
    fields: list[str]


class ReviewResult(BaseModel):
    flags: list[ReviewFlag]
    ready: bool


def review_packet(
    answers: dict[str, Any],
    documents: list[dict[str, Any]],
    generated_forms: list[dict[str, Any]],
    live_versions: dict[str, str],
) -> ReviewResult:
    flags: list[ReviewFlag] = []
    for form in generated_forms:
        missing = list(form.get("missing_required_fields") or [])
        if missing:
            flags.append(
                ReviewFlag(
                    code="missing_form_fields",
                    message=f"{form['form_code']} has required fields missing.",
                    fields=missing,
                )
            )
        if is_stale(str(form["form_code"]), str(form["form_version"]), live_versions):
            flags.append(
                ReviewFlag(
                    code="stale_form",
                    message=f"{form['form_code']} is not the current live version.",
                    fields=["form_version"],
                )
            )

    for document in documents:
        if not document.get("confirmed"):
            continue
        extracted = document.get("extracted_fields") or {}
        for key in ("full_name", "passport_number"):
            document_value = extracted.get(key)
            if isinstance(document_value, dict):
                document_value = document_value.get("value")
            answer_value = answers.get(key)
            if document_value and answer_value and str(document_value) != str(answer_value):
                flags.append(
                    ReviewFlag(
                        code="cross_field_mismatch",
                        message=f"Confirmed document {key} does not match intake.",
                        fields=[key],
                    )
                )
    return ReviewResult(flags=flags, ready=not flags)
