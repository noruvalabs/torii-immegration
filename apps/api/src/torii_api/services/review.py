"""Packet consistency checks before assembly (US-09)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from torii_api.services.forms import is_stale


class ReviewFlag(BaseModel):
    code: str
    message: str
    fields: list[str]


class ReviewCheck(BaseModel):
    code: str
    message: str
    passed: bool


class ReviewResult(BaseModel):
    flags: list[ReviewFlag]
    checks: list[ReviewCheck]
    ready: bool


def review_packet(
    answers: dict[str, Any],
    documents: list[dict[str, Any]],
    generated_forms: list[dict[str, Any]],
    live_versions: dict[str, str],
) -> ReviewResult:
    flags: list[ReviewFlag] = []
    checks: list[ReviewCheck] = []

    # --- Intake completeness ---
    if answers:
        checks.append(
            ReviewCheck(
                code="intake_complete",
                message=f"Intake answers provided ({len(answers)} fields).",
                passed=True,
            )
        )
    else:
        flags.append(
            ReviewFlag(
                code="intake_missing",
                message="No intake answers found.",
                fields=[],
            )
        )

    # --- Form generation ---
    if generated_forms:
        checks.append(
            ReviewCheck(
                code="forms_generated",
                message=f"{len(generated_forms)} form(s) generated.",
                passed=True,
            )
        )
    else:
        flags.append(
            ReviewFlag(
                code="forms_missing",
                message="No forms have been generated yet.",
                fields=[],
            )
        )

    # --- Per-form checks ---
    for form in generated_forms:
        missing = list(form.get("missing_required_fields") or [])
        if missing:
            flags.append(
                ReviewFlag(
                    code="missing_form_fields",
                    message=f"{form['form_code']} has required fields missing: {', '.join(missing)}.",
                    fields=missing,
                )
            )
        else:
            checks.append(
                ReviewCheck(
                    code=f"form_{form['form_code']}_fields_ok",
                    message=f"{form['form_code']} — all required fields filled.",
                    passed=True,
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
        else:
            checks.append(
                ReviewCheck(
                    code=f"form_{form['form_code']}_version_ok",
                    message=f"{form['form_code']} v{form['form_version']} is current.",
                    passed=True,
                )
            )

    # --- Document checks ---
    confirmed_docs = [d for d in documents if d.get("confirmed")]
    unconfirmed_docs = [d for d in documents if not d.get("confirmed")]

    if confirmed_docs:
        checks.append(
            ReviewCheck(
                code="documents_confirmed",
                message=f"{len(confirmed_docs)} document(s) confirmed.",
                passed=True,
            )
        )

    if unconfirmed_docs:
        checks.append(
            ReviewCheck(
                code="documents_unconfirmed",
                message=f"{len(unconfirmed_docs)} document(s) not yet confirmed.",
                passed=False,
            )
        )

    # --- Cross-field mismatch ---
    for document in confirmed_docs:
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

    if not any(f.code == "cross_field_mismatch" for f in flags):
        checks.append(
            ReviewCheck(
                code="cross_field_match",
                message="Document fields match intake answers.",
                passed=True,
            )
        )

    return ReviewResult(flags=flags, checks=checks, ready=not flags)
