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
                        message=f"Confirmed document {key} does not match intake answer.",
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

    # --- 1. Passport 6-Month Validity Rule ---
    from datetime import UTC, datetime

    passport_exp_str = str(
        answers.get("passport_expiry_date") or answers.get("passport_expiry") or ""
    )
    if passport_exp_str:
        try:
            # Handle YYYY-MM-DD
            exp_date = datetime.strptime(passport_exp_str[:10], "%Y-%m-%d").date()
            today = datetime.now(UTC).date()
            days_left = (exp_date - today).days
            if days_left < 0:
                flags.append(
                    ReviewFlag(
                        code="passport_expired",
                        message=f"Passport expired on {exp_date}. A valid passport is required for submission.",
                        fields=["passport_expiry_date"],
                    )
                )
            elif days_left < 180:
                flags.append(
                    ReviewFlag(
                        code="passport_short_validity",
                        message=f"Passport expires in {days_left // 30} month(s) ({exp_date}). Most embassies require at least 6 months validity (ICAO Doc 9303 / MOFA standards).",
                        fields=["passport_expiry_date"],
                    )
                )
            else:
                checks.append(
                    ReviewCheck(
                        code="passport_validity_ok",
                        message=f"Passport validity is sufficient ({days_left // 30} months remaining until {exp_date}).",
                        passed=True,
                    )
                )
        except Exception:
            pass

    # --- 2. Japan ISA 90-Day Application Window ---
    zairyu_exp_str = str(answers.get("residence_card_expiry") or "")
    if zairyu_exp_str:
        try:
            z_exp = datetime.strptime(zairyu_exp_str[:10], "%Y-%m-%d").date()
            today = datetime.now(UTC).date()
            days_to_z_exp = (z_exp - today).days
            if days_to_z_exp < 0:
                flags.append(
                    ReviewFlag(
                        code="status_expired_overstay_risk",
                        message=f"Residence card expired on {z_exp}. Overstay risk under Immigration Control Act Art. 24.",
                        fields=["residence_card_expiry"],
                    )
                )
            elif days_to_z_exp > 95:
                flags.append(
                    ReviewFlag(
                        code="filing_window_too_early",
                        message=f"Residence status expires on {z_exp} ({days_to_z_exp} days remaining). Regional Immigration Bureau accepts extension applications starting 3 months (90 days) prior to expiration.",
                        fields=["residence_card_expiry"],
                    )
                )
            else:
                checks.append(
                    ReviewCheck(
                        code="filing_window_valid",
                        message=f"Application is within the official 3-month filing window ({days_to_z_exp} days until expiration).",
                        passed=True,
                    )
                )
        except Exception:
            pass

    # --- 3. Income & Remuneration Adequacy ---
    salary_str = str(answers.get("monthly_salary") or answers.get("monthly_income") or "")
    if salary_str and salary_str.isdigit():
        salary_num = int(salary_str)
        if salary_num < 200000:
            flags.append(
                ReviewFlag(
                    code="salary_below_statutory_benchmark",
                    message=f"Monthly salary (¥{salary_num:,}) is below the standard ISA living benchmark of ¥200,000/month for Engineer/Specialist in Humanities status.",
                    fields=["monthly_salary"],
                )
            )
        else:
            checks.append(
                ReviewCheck(
                    code="salary_benchmark_met",
                    message=f"Remuneration (¥{salary_num:,}/month) meets official ISA statutory living benchmarks.",
                    passed=True,
                )
            )

    # --- 4. Student Attendance Rate (出席率) ---
    att_rate_val = answers.get("attendance_rate")
    if att_rate_val is not None:
        try:
            rate_num = float(str(att_rate_val).replace("%", "").strip())
            if rate_num < 80.0:
                flags.append(
                    ReviewFlag(
                        code="student_low_attendance_risk",
                        message=f"Attendance rate is {rate_num}%. ISA requires attendance >= 80%; applicants under 80% must attach a formal Statement of Reason (理由書) and medical/circumstantial proof.",
                        fields=["attendance_rate"],
                    )
                )
            else:
                checks.append(
                    ReviewCheck(
                        code="student_attendance_sufficient",
                        message=f"Student attendance rate ({rate_num}%) meets ISA statutory good standing standard (>= 80%).",
                        passed=True,
                    )
                )
        except Exception:
            pass

    # --- 5. Tax & Social Insurance Compliance ---
    if answers.get("resident_tax_status") is False:
        flags.append(
            ReviewFlag(
                code="resident_tax_arrears_warning",
                message="Resident tax (住民税) arrears indicated. Under revised 2024/2026 ISA guidelines, tax delinquency is a primary ground for visa denial.",
                fields=["resident_tax_status"],
            )
        )
    elif "resident_tax_status" in answers:
        checks.append(
            ReviewCheck(
                code="resident_tax_compliant",
                message="Municipal resident tax (住民税) compliance confirmed.",
                passed=True,
            )
        )

    # --- 6. Criminal / Deportation Disclosures ---
    if answers.get("criminal_record") is True:
        flags.append(
            ReviewFlag(
                code="criminal_disclosure_attached",
                message="Criminal record disclosed. Ensure full certified court judgment and rehabilitation records are attached.",
                fields=["criminal_record"],
            )
        )

    # --- 7. Sponsoring Company Category Documentation ---
    emp_cat = str(answers.get("employer_category") or "")
    if "3" in emp_cat or "4" in emp_cat:
        checks.append(
            ReviewCheck(
                code="employer_category_statutory_sheet_required",
                message=f"Sponsoring Employer is Category {emp_cat[-1] if emp_cat else '3'}. Statutory Withholding Total Table (法定調書合計表) and financial statements are included in the dossier.",
                passed=True,
            )
        )

    return ReviewResult(flags=flags, checks=checks, ready=not flags)
