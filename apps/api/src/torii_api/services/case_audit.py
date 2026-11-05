"""Case readiness audit — one report answering "can this case be filed yet?".

The audit aggregates what the applicant workflow already knows — intake
completeness, the deterministic eligibility evaluation, the document
checklist and uploaded documents — and adds explicit consistency checks
(passport validity window, stay length, return date, contact email, and
profile/intake identity agreement). It also carries the route-specific
filing instructions for the case (Phase 3 in-person track: Tasheer
consular filing and licensed-agent Umrah; online routes point at the
portal-bot track instead).

Framework-free: the API layer gathers rows and passes plain data in, so
the aggregation is unit-testable without a database.
"""

from __future__ import annotations

import calendar
from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field

from torii_api.services.eligibility import EligibilityResult
from torii_api.services.intake import IntakeQuestion, visible_questions
from torii_api.services.saudi_evisa import classify_route

CheckStatus = Literal["pass", "warn", "fail"]
OverallStatus = Literal["ready", "needs_attention", "blocked"]

TASHEER_CENTRE_DEFAULT = "Tasheer Saudi Visa Service Centre, Jamuna Future Park, Dhaka"
TASHEER_BOOKING_URL = "https://vc.tasheer.com"

# Routes whose applicants file in person at a Saudi visa service centre.
# Package Visa holders may instead buy the provider package, but the
# consular route (and therefore a Tasheer appointment) remains open to them.
APPOINTMENT_ROUTES: frozenset[str] = frozenset({"in_person", "online_package"})

_TASHEER_CITATION: dict[str, Any] = {
    "authority": "Tasheer — Saudi Visa Service Centre",
    "title": "Saudi Visa Service Centre (Tasheer) — appointment booking and in-person submission",
    "url": TASHEER_BOOKING_URL,
}
_NUSUK_CITATION: dict[str, Any] = {
    "authority": "Ministry of Hajj and Umrah — Nusuk",
    "title": "Nusuk Umrah platform — Umrah visas and packages for pilgrims outside the Kingdom",
    "url": "https://umrah.nusuk.sa",
}
_KSAVISA_CITATION: dict[str, Any] = {
    "authority": "Ministry of Foreign Affairs (MOFA) — KSA Visa platform",
    "title": "KSA Visa (ksavisa.sa) — unified national visa platform, visit visa application",
    "url": "https://ksavisa.sa",
}

# Why a route cannot book a Tasheer appointment, surfaced verbatim in the
# 400 response so the applicant/ops see the correct channel instead.
APPOINTMENT_BLOCK_MESSAGES: dict[str, str] = {
    "online_evisa": (
        "This case applies online on the KSA Visa portal (ksavisa.sa) — "
        "no visa-centre appointment is needed or available for it."
    ),
    "online_conditional": (
        "This case applies online on the KSA Visa portal (ksavisa.sa) via its "
        "existing visa/residence — no visa-centre appointment is needed or available for it."
    ),
    "agent_umrah": (
        "Umrah for this profile is filed by a travel agent licensed by the Saudi "
        "Ministry of Hajj & Umrah on Nusuk Masar — there is no Tasheer appointment for it."
    ),
    "visa_free": "GCC citizens enter Saudi Arabia visa-free — no appointment is needed.",
    "citizen": "Saudi citizens do not need a visa or an appointment.",
}


class AuditCheck(BaseModel):
    key: str
    status: CheckStatus
    message: str


class AuditStep(BaseModel):
    order: int
    title: str
    detail: str
    citation: dict[str, Any] | None = None


class IntakeAudit(BaseModel):
    total_required: int
    answered_required: int
    missing_required: list[str] = Field(default_factory=list)
    complete: bool


class DocumentAuditItem(BaseModel):
    code: str
    name: str
    is_required: bool
    status: str
    document_id: int | None = None
    document_confirmed: bool = False


class UploadedDocument(BaseModel):
    id: int
    doc_type: str
    filename: str
    confirmed: bool


class DocumentAudit(BaseModel):
    total_items: int
    required_total: int
    required_satisfied: int
    missing_required: list[str] = Field(default_factory=list)
    items: list[DocumentAuditItem] = Field(default_factory=list)


class CaseAudit(BaseModel):
    case_id: int
    reference: str
    jurisdiction_code: str | None = None
    route: str | None = None
    overall: OverallStatus
    summary: str
    intake: IntakeAudit
    eligibility: EligibilityResult | None = None
    documents: DocumentAudit
    uploaded: list[UploadedDocument] = Field(default_factory=list)
    checks: list[AuditCheck] = Field(default_factory=list)
    instructions: list[AuditStep] = Field(default_factory=list)


def route_for_case(jurisdiction_code: str | None, answers: dict[str, Any]) -> str | None:
    """Apply-route for a case, or ``None`` where routes are not modelled.

    Only Saudi Arabia has route classification (see services.saudi_evisa);
    other jurisdictions still get a generic audit without a route.
    """
    if (jurisdiction_code or "").upper() == "SA":
        return classify_route(answers)
    return None


# ── Intake completeness ──────────────────────────────────────────────────────


def _is_answered(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str) and value.strip() == "":
        return False
    return True


def intake_completeness(questions: list[IntakeQuestion], answers: dict[str, Any]) -> IntakeAudit:
    """Answered vs required among the questions visible for the current branch."""
    required = [q for q in visible_questions(questions, answers) if q.required]
    missing = [q.key for q in required if not _is_answered(answers.get(q.key))]
    return IntakeAudit(
        total_required=len(required),
        answered_required=len(required) - len(missing),
        missing_required=missing,
        complete=not missing,
    )


# ── Consistency checks ───────────────────────────────────────────────────────


def _parse_date(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _add_months(day: date, months: int) -> date:
    month_index = day.month - 1 + months
    year = day.year + month_index // 12
    month = month_index % 12 + 1
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(day.day, last_day))


def _first(answers: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = answers.get(key)
        if value is not None and str(value).strip() != "":
            return value
    return None


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "y", "1"}
    return False


def consistency_checks(
    answers: dict[str, Any],
    *,
    profile_full_name: str | None = None,
    profile_passport_number: str | None = None,
    contact_email: str | None = None,
) -> list[AuditCheck]:
    """Explicit cross-field checks; every check reports pass, warn, or fail.

    A check only fails on a positive contradiction (dates that cannot both
    be true, identity fields that disagree). Missing inputs warn — the
    intake-completeness section already reports what is missing.
    """
    checks: list[AuditCheck] = []

    # Passport valid at least 6 months beyond planned arrival.
    arrival = _parse_date(
        _first(answers, "planned_arrival_date", "arrival_date", "intended_entry_date")
    )
    expiry = _parse_date(_first(answers, "passport_expiry_date", "passport_expiry", "expiry_date"))
    if arrival is not None and expiry is not None:
        required_until = _add_months(arrival, 6)
        if expiry < arrival:
            checks.append(
                AuditCheck(
                    key="passport_six_month_validity",
                    status="fail",
                    message=(
                        f"Passport expires {expiry.isoformat()}, before the planned "
                        f"arrival {arrival.isoformat()} — renew the passport before filing."
                    ),
                )
            )
        elif expiry < required_until:
            checks.append(
                AuditCheck(
                    key="passport_six_month_validity",
                    status="fail",
                    message=(
                        f"Passport expires {expiry.isoformat()}, less than 6 months after "
                        f"arrival {arrival.isoformat()} (validity needed until "
                        f"{required_until.isoformat()}). Saudi Arabia requires 6 months "
                        "of validity from entry on every route."
                    ),
                )
            )
        else:
            checks.append(
                AuditCheck(
                    key="passport_six_month_validity",
                    status="pass",
                    message=(
                        f"Passport is valid until {expiry.isoformat()}, more than 6 months "
                        f"beyond arrival {arrival.isoformat()}."
                    ),
                )
            )
    elif "passport_valid_six_months" in answers:
        declared = _truthy(answers.get("passport_valid_six_months"))
        checks.append(
            AuditCheck(
                key="passport_six_month_validity",
                status="pass" if declared else "fail",
                message=(
                    "Applicant confirms the passport stays valid 6+ months beyond entry."
                    if declared
                    else "Applicant states the passport will NOT be valid 6 months beyond "
                    "entry — renew the passport before filing."
                ),
            )
        )
    else:
        checks.append(
            AuditCheck(
                key="passport_six_month_validity",
                status="warn",
                message=(
                    "Cannot verify the 6-month passport validity rule — passport expiry "
                    "and/or planned arrival date are not recorded."
                ),
            )
        )

    # Stay within the 90-day tourist maximum.
    stay_raw = _first(answers, "intended_length_of_stay_days", "length_of_stay", "stay_days")
    stay_days: int | None = None
    if stay_raw is not None:
        try:
            stay_days = int(stay_raw)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            stay_days = None
    if stay_days is None:
        checks.append(
            AuditCheck(
                key="stay_within_90_days",
                status="warn",
                message="Planned length of stay is not recorded, so the 90-day maximum cannot be checked.",
            )
        )
    elif stay_days > 90:
        checks.append(
            AuditCheck(
                key="stay_within_90_days",
                status="fail",
                message=(
                    f"Planned stay of {stay_days} days exceeds the 90-day maximum stay "
                    "for a Saudi tourist/visit visa, which cannot be extended."
                ),
            )
        )
    else:
        checks.append(
            AuditCheck(
                key="stay_within_90_days",
                status="pass",
                message=f"Planned stay of {stay_days} days is within the 90-day maximum.",
            )
        )

    # Return/departure not before arrival.
    departure = _parse_date(
        _first(
            answers, "return_date", "departure_date", "planned_departure_date", "return_flight_date"
        )
    )
    if departure is not None and arrival is not None:
        if departure < arrival:
            checks.append(
                AuditCheck(
                    key="return_not_before_arrival",
                    status="fail",
                    message=(
                        f"Recorded return date {departure.isoformat()} is before the "
                        f"arrival date {arrival.isoformat()} — fix the travel dates."
                    ),
                )
            )
        else:
            checks.append(
                AuditCheck(
                    key="return_not_before_arrival",
                    status="pass",
                    message=f"Return date {departure.isoformat()} is on or after arrival {arrival.isoformat()}.",
                )
            )
    elif _truthy(answers.get("has_return_ticket")):
        checks.append(
            AuditCheck(
                key="return_not_before_arrival",
                status="pass",
                message="A confirmed return or onward ticket is recorded for this trip.",
            )
        )
    elif "has_return_ticket" in answers:
        checks.append(
            AuditCheck(
                key="return_not_before_arrival",
                status="warn",
                message=(
                    "No return ticket is recorded yet — a confirmed round-trip ticket is "
                    "part of the Tasheer file and mandatory for Package Visa and Umrah routes."
                ),
            )
        )
    else:
        checks.append(
            AuditCheck(
                key="return_not_before_arrival",
                status="warn",
                message="No return date or return ticket is recorded, so the return leg cannot be checked.",
            )
        )

    # Contact email present (the eVisa is delivered by email; Tasheer notifies by email/SMS).
    if contact_email and "@" in contact_email:
        checks.append(
            AuditCheck(
                key="contact_email_present",
                status="pass",
                message=f"Contact email on file: {contact_email}.",
            )
        )
    else:
        checks.append(
            AuditCheck(
                key="contact_email_present",
                status="fail",
                message=(
                    "No usable contact email is recorded — the visa and appointment "
                    "notifications are delivered by email."
                ),
            )
        )

    # Identity: full name and passport number present, and profile/intake agree.
    full_name = _first(answers, "full_name", "applicant_name", "name")
    passport_number = _first(answers, "passport_number", "passport_no")
    if not full_name or not passport_number:
        missing_bits = [
            label
            for label, value in (("full name", full_name), ("passport number", passport_number))
            if not value
        ]
        checks.append(
            AuditCheck(
                key="identity_consistency",
                status="fail",
                message=f"Intake is missing the applicant's {' and '.join(missing_bits)}.",
            )
        )
    else:
        mismatches: list[str] = []
        if (
            profile_full_name
            and str(profile_full_name).strip().lower() != str(full_name).strip().lower()
        ):
            mismatches.append(
                f"full name differs between profile ('{profile_full_name}') and intake ('{full_name}')"
            )
        if (
            profile_passport_number
            and str(profile_passport_number).strip().upper() != str(passport_number).strip().upper()
        ):
            mismatches.append("passport number differs between profile and intake")
        if mismatches:
            checks.append(
                AuditCheck(
                    key="identity_consistency",
                    status="fail",
                    message="Identity mismatch: " + "; ".join(mismatches) + ".",
                )
            )
        elif profile_full_name or profile_passport_number:
            checks.append(
                AuditCheck(
                    key="identity_consistency",
                    status="pass",
                    message="Full name and passport number agree between the profile and the intake answers.",
                )
            )
        else:
            checks.append(
                AuditCheck(
                    key="identity_consistency",
                    status="warn",
                    message=(
                        "Full name and passport number are recorded in intake, but the "
                        "account profile holds neither, so they cannot be cross-checked."
                    ),
                )
            )

    return checks


# ── Documents ────────────────────────────────────────────────────────────────

_SATISFIED_STATUSES = frozenset({"gathered", "uploaded"})


def document_audit(
    checklist_items: list[dict[str, Any]], documents: list[dict[str, Any]]
) -> tuple[DocumentAudit, list[UploadedDocument]]:
    """Summarise checklist satisfaction and the uploaded documents behind it."""
    confirmed_by_id = {doc["id"]: bool(doc.get("confirmed")) for doc in documents}
    items: list[DocumentAuditItem] = []
    missing_required: list[str] = []
    required_total = 0
    required_satisfied = 0
    for raw in checklist_items:
        document_id = raw.get("document_id")
        item = DocumentAuditItem(
            code=str(raw.get("code") or "document"),
            name=str(raw.get("name") or "Document"),
            is_required=bool(raw.get("is_required", True)),
            status=str(raw.get("status") or "needed"),
            document_id=document_id,
            document_confirmed=bool(document_id and confirmed_by_id.get(document_id)),
        )
        items.append(item)
        if item.is_required:
            required_total += 1
            if item.status in _SATISFIED_STATUSES:
                required_satisfied += 1
            else:
                missing_required.append(item.name)
    uploaded = [
        UploadedDocument(
            id=int(doc["id"]),
            doc_type=str(doc.get("doc_type") or "document"),
            filename=str(doc.get("filename") or ""),
            confirmed=bool(doc.get("confirmed")),
        )
        for doc in documents
    ]
    audit = DocumentAudit(
        total_items=len(items),
        required_total=required_total,
        required_satisfied=required_satisfied,
        missing_required=missing_required,
        items=items,
    )
    return audit, uploaded


# ── Instructions ─────────────────────────────────────────────────────────────

_CONSULAR_STEPS: list[AuditStep] = [
    AuditStep(
        order=1,
        title="Complete your dossier in Torii",
        detail=(
            "Finish the intake questions and upload every required document. This audit "
            "should show no failed checks before you attend — the visa centre works from "
            "exactly this file."
        ),
    ),
    AuditStep(
        order=2,
        title="Book the Tasheer appointment online",
        detail=(
            "Appointments at the Saudi Visa Service Centre are booked on the Tasheer "
            "portal. Request your preferred date here in Torii; ops confirm the slot on "
            "vc.tasheer.com and record the booking reference on your case."
        ),
        citation=_TASHEER_CITATION,
    ),
    AuditStep(
        order=3,
        title="Attend the Tasheer centre in Dhaka",
        detail=(
            f"{TASHEER_CENTRE_DEFAULT}. Arrive 15 minutes before your slot with your "
            "passport, the originals of every document in the checklist, and a printed "
            "copy of the complete Torii dossier packet."
        ),
        citation=_TASHEER_CITATION,
    ),
    AuditStep(
        order=4,
        title="Give biometrics at the centre",
        detail="Your fingerprints and photograph are captured at the centre as part of submission.",
        citation=_TASHEER_CITATION,
    ),
    AuditStep(
        order=5,
        title="Pay the fees at the centre",
        detail=(
            "The visa fee, the mandatory medical insurance, and the Tasheer service fee "
            "are paid at the centre on the day of submission."
        ),
        citation=_TASHEER_CITATION,
    ),
    AuditStep(
        order=6,
        title="Wait for the embassy decision",
        detail=(
            "The application is decided by the Saudi Embassy in Dhaka, not by the centre. "
            "Decisions typically take about 5–10 working days — an estimate; the embassy "
            "does not publish a guaranteed timeline."
        ),
    ),
    AuditStep(
        order=7,
        title="Collect your passport",
        detail=(
            "Collect the passport from the same Tasheer centre when notified, and check "
            "the visa details (name, passport number, validity) before you leave."
        ),
        citation=_TASHEER_CITATION,
    ),
]

_UMRAH_AGENT_STEPS: list[AuditStep] = [
    AuditStep(
        order=1,
        title="Use a Ministry-licensed Umrah agent",
        detail=(
            "For this passport, a standalone Umrah visa cannot be self-applied on Nusuk. "
            "A travel agent licensed by the Saudi Ministry of Hajj & Umrah files the "
            "application — Torii works with licensed partner agents."
        ),
        citation=_NUSUK_CITATION,
    ),
    AuditStep(
        order=2,
        title="Book the complete verified package",
        detail=(
            "The package must combine a licensed-hotel booking for the whole stay, "
            "pre-booked ground transport, and a confirmed round-trip ticket. Since "
            "June 2025 no Umrah visa is issued without all three verified."
        ),
        citation=_NUSUK_CITATION,
    ),
    AuditStep(
        order=3,
        title="The agent files on Nusuk Masar",
        detail=(
            "Your agent submits the visa application on the Nusuk Masar platform "
            "against those verified bookings; the visa is issued electronically."
        ),
        citation=_NUSUK_CITATION,
    ),
    AuditStep(
        order=4,
        title="Book your Umrah permit in the Nusuk app",
        detail=(
            "After the visa is issued, book the free Umrah permit (and a Rawdah slot if "
            "you plan to visit) in the Nusuk app before entering Masjid al-Haram."
        ),
        citation=_NUSUK_CITATION,
    ),
]

_ONLINE_STEPS: list[AuditStep] = [
    AuditStep(
        order=1,
        title="Filed online — no appointment needed",
        detail=(
            "This route is filed on the official KSA Visa platform (ksavisa.sa) by "
            "Torii's portal worker once intake and documents are complete. The portal "
            "account sign-in/OTP, any captcha, and the government-fee payment are "
            "human checkpoints — they are never automated."
        ),
        citation=_KSAVISA_CITATION,
    ),
]


def build_instructions(route: str | None) -> list[AuditStep]:
    """Ordered filing instructions for the case's route (empty for other jurisdictions)."""
    if route in APPOINTMENT_ROUTES:
        return list(_CONSULAR_STEPS)
    if route == "agent_umrah":
        return list(_UMRAH_AGENT_STEPS)
    if route in ("online_evisa", "online_conditional"):
        return list(_ONLINE_STEPS)
    if route == "visa_free":
        return [
            AuditStep(
                order=1,
                title="No visa required",
                detail=(
                    "GCC citizens enter Saudi Arabia visa-free. If travelling for Umrah, "
                    "book the free Umrah permit in the Nusuk app before entering Masjid al-Haram."
                ),
                citation=_NUSUK_CITATION,
            )
        ]
    if route == "citizen":
        return [
            AuditStep(
                order=1,
                title="No visa required",
                detail="Saudi citizens travel on their Saudi passport or national ID — no application is needed.",
            )
        ]
    return []


# ── Assembly ─────────────────────────────────────────────────────────────────


def assemble_audit(
    *,
    case_id: int,
    reference: str,
    jurisdiction_code: str | None,
    route: str | None,
    intake: IntakeAudit,
    eligibility: EligibilityResult | None,
    documents: DocumentAudit,
    uploaded: list[UploadedDocument],
    checks: list[AuditCheck],
) -> CaseAudit:
    """Compute overall readiness and the one-line summary.

    ``blocked`` is reserved for positive contradictions and hard gaps: a
    failed consistency check, a failed eligibility rule, or missing
    required intake answers. Everything else that still needs work —
    an at-risk eligibility read, outstanding documents, unconfirmed
    uploads, a warning — is ``needs_attention``.
    """
    blocked_reasons: list[str] = []
    attention_reasons: list[str] = []

    if intake.missing_required:
        blocked_reasons.append(
            f"{len(intake.missing_required)} required intake answer(s) are still missing"
        )
    failed_checks = [c for c in checks if c.status == "fail"]
    if failed_checks:
        blocked_reasons.append(
            f"{len(failed_checks)} consistency check(s) failed "
            f"({', '.join(c.key.replace('_', ' ') for c in failed_checks)})"
        )
    if eligibility is not None and eligibility.result == "fail":
        blocked_reasons.append("the eligibility evaluation failed a hard requirement")

    if eligibility is None:
        attention_reasons.append("eligibility has not been evaluated for this scope")
    elif eligibility.result in ("at_risk", "out_of_scope"):
        attention_reasons.append(
            "the eligibility read is "
            + ("at risk" if eligibility.result == "at_risk" else "partly out of scope")
        )
    warn_checks = [c for c in checks if c.status == "warn"]
    if warn_checks:
        attention_reasons.append(f"{len(warn_checks)} check(s) need a second look")
    if documents.missing_required:
        attention_reasons.append(
            f"{len(documents.missing_required)} required document(s) are still outstanding"
        )
    unconfirmed_linked = [
        item
        for item in documents.items
        if item.is_required and item.document_id is not None and not item.document_confirmed
    ]
    if unconfirmed_linked:
        attention_reasons.append(
            f"{len(unconfirmed_linked)} uploaded document(s) are not yet confirmed"
        )

    if blocked_reasons:
        overall: OverallStatus = "blocked"
        summary = "Blocked: " + "; ".join(blocked_reasons) + "."
    elif attention_reasons:
        overall = "needs_attention"
        summary = "Needs attention: " + "; ".join(attention_reasons) + "."
    else:
        overall = "ready"
        summary = (
            "Ready to file: intake is complete, eligibility passes, documents are "
            "in place, and every consistency check passes."
        )

    return CaseAudit(
        case_id=case_id,
        reference=reference,
        jurisdiction_code=jurisdiction_code,
        route=route,
        overall=overall,
        summary=summary,
        intake=intake,
        eligibility=eligibility,
        documents=documents,
        uploaded=uploaded,
        checks=checks,
        instructions=build_instructions(route),
    )
