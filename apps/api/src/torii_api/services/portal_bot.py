"""Portal submission jobs — Vietnam eVisa and Saudi KSA Visa are live; other
corridors fail closed.

Vietnam: stock Playwright fills public fields on evisa.gov.vn.
Saudi Arabia: stock Playwright fills public fields on ksavisa.sa, but only for
cases whose route guard classifies them online (eVisa-eligible passports, or a
used US/UK/Schengen visa / Western permanent residence / GCC residence). The
portal files only inside the applicant's own account, so sign-in/OTP, captcha
and government-fee payment are never automated. Confirmation numbers are
stored only when extracted from the portal page — never generated here.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from torii_api.config import get_settings
from torii_api.db.models import (
    Case,
    CaseDocument,
    Jurisdiction,
    PortalSubmissionJob,
    SubmissionJobStatus,
)
from torii_api.services.saudi_evisa import (
    ONLINE_ROUTES,
    ROUTE_BLOCK_DETAILS,
    SA_PORTAL_NAME,
    SA_PORTAL_URL,
)
from torii_api.services.saudi_evisa import build_payload as build_saudi_payload
from torii_api.services.saudi_evisa import classify_route as classify_saudi_route
from torii_api.services.saudi_portal import run_saudi_portal
from torii_api.services.vietnam_evisa import (
    VN_PORTAL_NAME,
    VN_PORTAL_URL,
    build_payload,
)
from torii_api.services.vietnam_portal import (
    PlaywrightPortalSession,
    PortalSession,
    run_vietnam_portal,
)
from torii_api.services.wallet import save_document_content

PortalSessionFactory = Callable[[], Awaitable[PortalSession]]

PORTAL_CONFIGS: dict[str, dict[str, str]] = {
    "VN": {
        "portal_name": VN_PORTAL_NAME,
        "portal_url": VN_PORTAL_URL,
        "fee_usd": "25.00",
    },
    "SA": {
        "portal_name": SA_PORTAL_NAME,
        "portal_url": SA_PORTAL_URL,
        # SAR 395 incl. mandatory medical insurance ≈ USD 105 (eVisa Terms fix
        # no price; the portal checkout total is authoritative).
        "fee_usd": "105.00",
    },
}

DEFAULT_CONFIG: dict[str, str] = {
    "portal_name": "Official National Immigration eVisa Portal",
    "portal_url": "",
    "fee_usd": "0.00",
}


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def get_portal_config(jurisdiction_code: str) -> dict[str, str]:
    return PORTAL_CONFIGS.get(jurisdiction_code.upper(), DEFAULT_CONFIG)


async def _resolve_jurisdiction_code(session: AsyncSession, case: Case) -> str:
    if case.jurisdiction_id:
        jur = await session.get(Jurisdiction, case.jurisdiction_id)
        if jur and jur.code:
            return jur.code.upper()
    if case.reference and "-" in case.reference:
        return case.reference.split("-")[0].upper()
    return "UNKNOWN"


async def create_submission_job(
    session: AsyncSession,
    case_id: int,
) -> PortalSubmissionJob:
    """Create a new queued automated submission job for a case."""
    case = await session.get(Case, case_id)
    if case is None:
        raise ValueError(f"Case {case_id} not found")

    j_code = await _resolve_jurisdiction_code(session, case)
    cfg = get_portal_config(j_code)

    if j_code == "VN":
        queued_detail = "Waiting for the Vietnam eVisa worker (evisa.gov.vn)."
    elif j_code == "SA":
        queued_detail = "Waiting for the Saudi KSA Visa worker (ksavisa.sa)."
    else:
        queued_detail = f"Waiting for a portal worker ({j_code})."

    job = PortalSubmissionJob(
        case_id=case.id,
        jurisdiction_code=j_code,
        portal_name=cfg["portal_name"] or f"{j_code} eVisa portal",
        portal_url=cfg["portal_url"],
        status=SubmissionJobStatus.QUEUED,
        steps_log=[
            {
                "step": SubmissionJobStatus.QUEUED,
                "label": "Job queued",
                "detail": queued_detail,
                "timestamp": _now_iso(),
            }
        ],
        dispatched_at=datetime.now(UTC),
        captcha_solved=False,
    )
    session.add(job)
    await session.flush()
    return job


async def _add_step(
    job: PortalSubmissionJob,
    session: AsyncSession,
    step_name: str,
    label: str,
    detail: str,
) -> None:
    job.status = step_name
    steps = list(job.steps_log or [])
    steps.append(
        {
            "step": step_name,
            "label": label,
            "detail": detail,
            "timestamp": _now_iso(),
        }
    )
    job.steps_log = list(steps)
    await session.flush()


async def _finish(
    job: PortalSubmissionJob,
    session: AsyncSession,
    *,
    status: str,
    label: str,
    detail: str,
    error: str | None = None,
) -> PortalSubmissionJob:
    job.error_message = error
    job.completed_at = datetime.now(UTC)
    await _add_step(job, session, status, label, detail)
    return job


async def _store_screenshot(
    session: AsyncSession,
    job: PortalSubmissionJob,
    case: Case,
    png: bytes | None,
) -> None:
    if not png:
        return
    filename = f"{job.jurisdiction_code.lower()}_evisa_job_{job.id}.png"
    storage_key = f"portal_screenshots/{case.id}/{filename}"
    save_document_content(storage_key, png)
    doc = CaseDocument(
        case_id=case.id,
        doc_type="portal_screenshot",
        filename=filename,
        storage_key=storage_key,
        content_type="image/png",
        confirmed=True,
        extracted_fields={"job_id": job.id, "portal_url": job.portal_url},
    )
    session.add(doc)
    await session.flush()
    job.screenshot_url = f"/backend/v1/cases/{case.id}/documents"
    await session.flush()


async def _run_saudi_submission(
    session: AsyncSession,
    job: PortalSubmissionJob,
    case: Case,
    *,
    portal_session_factory: PortalSessionFactory | None = None,
    allow_submit: bool | None = None,
) -> PortalSubmissionJob:
    """Run one Saudi job. Route guard first: only online routes may file.

    Package Visa, in-person consular, licensed-agent Umrah, visa-free and
    citizen profiles fail closed with a route-specific explanation — the
    ksavisa.sa worker never files them.
    """
    answers = case.intake_answers or {}
    route = classify_saudi_route(answers)
    if route not in ONLINE_ROUTES:
        detail = ROUTE_BLOCK_DETAILS.get(
            route, "This profile does not apply online via ksavisa.sa."
        )
        return await _finish(
            job,
            session,
            status=SubmissionJobStatus.FAILED,
            label="Route is not an online KSA Visa application",
            detail=detail,
            error=f"route_not_online:{route}",
        )

    settings = get_settings()
    submit = settings.sa_evisa_allow_submit if allow_submit is None else allow_submit
    payload = build_saudi_payload(
        answers,
        email_fallback=case.applicant_email or "",
    )
    if not payload.is_complete:
        missing = ", ".join(payload.missing_required)
        return await _finish(
            job,
            session,
            status=SubmissionJobStatus.FAILED,
            label="Intake incomplete",
            detail=f"Cannot open ksavisa.sa until these fields exist on the case: {missing}.",
            error=f"missing_fields:{missing}",
        )

    await _add_step(
        job,
        session,
        SubmissionJobStatus.NAVIGATING,
        "Opening ksavisa.sa",
        "Stock Chromium, no proxy and no captcha solver. The portal files only "
        "inside the applicant's own account: a sign-in wall, OTP prompt, "
        "challenge page or payment step stops the job for manual takeover.",
    )

    browser: PortalSession | None = None
    try:
        if portal_session_factory is not None:
            browser = await portal_session_factory()
        else:
            browser = await PlaywrightPortalSession.launch(
                headless=settings.sa_evisa_headless,
                timeout_ms=settings.sa_evisa_timeout_ms,
            )

        await _add_step(
            job,
            session,
            SubmissionJobStatus.FILLING_FORM,
            "Filling public form fields",
            f"Mapped {len(payload.values)} intake fields onto KSA Visa portal labels.",
        )
        fill = await run_saudi_portal(
            browser,
            payload,
            portal_url=job.portal_url or SA_PORTAL_URL,
            allow_submit=submit,
        )
        await _store_screenshot(session, job, case, fill.screenshot)

        filled = ", ".join(fill.filled) or "(none)"
        unfilled = ", ".join(fill.unfilled) or "(none)"
        await _add_step(
            job,
            session,
            SubmissionJobStatus.FILLING_FORM,
            "Field write result",
            f"Filled: {filled}. Not found on page: {unfilled}.",
        )

        if fill.challenge:
            job.captcha_solved = False
            return await _finish(
                job,
                session,
                status=SubmissionJobStatus.MANUAL_TAKEOVER,
                label="Stopped at security checkpoint",
                detail=(
                    "The portal presented an account sign-in wall, an OTP prompt, "
                    "a captcha or a bot-check. Torii never creates portal "
                    "accounts, enters one-time codes, or solves those. The "
                    "applicant or an operator must sign in and finish the "
                    "application in a real browser."
                ),
                error="portal_challenge",
            )

        if fill.confirmation_code:
            job.portal_reference = fill.confirmation_code
            case.status = "submitted"
            case.submission_reference = fill.confirmation_code
            await session.flush()
            return await _finish(
                job,
                session,
                status=SubmissionJobStatus.SUCCEEDED,
                label="Portal confirmation captured",
                detail=f"Application number taken from the page: {fill.confirmation_code}",
            )

        reason = (
            "Fields were written where labels matched. Account sign-in/OTP, "
            "captcha and the government card payment are not automated, so this "
            "is not a filed visa. Finish on ksavisa.sa and save the real "
            "application number."
        )
        if payload.notes:
            reason += " Notes: " + "; ".join(payload.notes)
        return await _finish(
            job,
            session,
            status=SubmissionJobStatus.MANUAL_TAKEOVER,
            label="Human finish required",
            detail=reason,
            error="awaiting_human_captcha_or_payment",
        )
    except Exception as exc:
        return await _finish(
            job,
            session,
            status=SubmissionJobStatus.FAILED,
            label="Worker error",
            detail=str(exc),
            error=str(exc),
        )
    finally:
        if browser is not None:
            try:
                await browser.close()
            except Exception:
                pass


async def run_submission_job(
    session: AsyncSession,
    job_id: int,
    *,
    simulate_delay: bool = False,
    portal_session_factory: PortalSessionFactory | None = None,
    allow_submit: bool | None = None,
) -> PortalSubmissionJob:
    """Run one portal job. ``simulate_delay`` is ignored (kept for call-site compatibility)."""
    del simulate_delay
    job = await session.get(PortalSubmissionJob, job_id)
    if job is None:
        raise ValueError(f"Job {job_id} not found")

    case = await session.get(Case, job.case_id)
    if case is None:
        raise ValueError(f"Case {job.case_id} not found")

    if job.jurisdiction_code.upper() == "SA":
        return await _run_saudi_submission(
            session,
            job,
            case,
            portal_session_factory=portal_session_factory,
            allow_submit=allow_submit,
        )

    if job.jurisdiction_code.upper() != "VN":
        return await _finish(
            job,
            session,
            status=SubmissionJobStatus.FAILED,
            label="Corridor not automated",
            detail=(
                f"{job.jurisdiction_code} is not supported by the portal worker. "
                "Only Vietnam (evisa.gov.vn) and Saudi Arabia (ksavisa.sa, "
                "online routes only) are implemented."
            ),
            error=f"unsupported_jurisdiction:{job.jurisdiction_code}",
        )

    settings = get_settings()
    submit = settings.vn_evisa_allow_submit if allow_submit is None else allow_submit
    payload = build_payload(
        case.intake_answers or {},
        email_fallback=case.applicant_email or "",
    )
    if not payload.is_complete:
        missing = ", ".join(payload.missing_required)
        return await _finish(
            job,
            session,
            status=SubmissionJobStatus.FAILED,
            label="Intake incomplete",
            detail=f"Cannot open evisa.gov.vn until these fields exist on the case: {missing}.",
            error=f"missing_fields:{missing}",
        )

    await _add_step(
        job,
        session,
        SubmissionJobStatus.NAVIGATING,
        "Opening evisa.gov.vn",
        "Stock Chromium, no proxy and no captcha solver. A challenge page stops the job.",
    )

    browser: PortalSession | None = None
    try:
        if portal_session_factory is not None:
            browser = await portal_session_factory()
        else:
            browser = await PlaywrightPortalSession.launch(
                headless=settings.vn_evisa_headless,
                timeout_ms=settings.vn_evisa_timeout_ms,
            )

        await _add_step(
            job,
            session,
            SubmissionJobStatus.FILLING_FORM,
            "Filling public form fields",
            f"Mapped {len(payload.values)} intake fields onto published evisa.gov.vn labels.",
        )
        fill = await run_vietnam_portal(
            browser,
            payload,
            portal_url=job.portal_url or VN_PORTAL_URL,
            allow_submit=submit,
        )
        await _store_screenshot(session, job, case, fill.screenshot)

        filled = ", ".join(fill.filled) or "(none)"
        unfilled = ", ".join(fill.unfilled) or "(none)"
        await _add_step(
            job,
            session,
            SubmissionJobStatus.FILLING_FORM,
            "Field write result",
            f"Filled: {filled}. Not found on page: {unfilled}.",
        )

        if fill.challenge:
            job.captcha_solved = False
            return await _finish(
                job,
                session,
                status=SubmissionJobStatus.MANUAL_TAKEOVER,
                label="Stopped at security checkpoint",
                detail=(
                    "The portal presented a captcha or bot-check. Torii does not solve "
                    "those. An operator must finish the application in a real browser."
                ),
                error="portal_challenge",
            )

        if fill.confirmation_code:
            job.portal_reference = fill.confirmation_code
            case.status = "submitted"
            case.submission_reference = fill.confirmation_code
            await session.flush()
            return await _finish(
                job,
                session,
                status=SubmissionJobStatus.SUCCEEDED,
                label="Portal confirmation captured",
                detail=f"Registration code taken from the page: {fill.confirmation_code}",
            )

        reason = (
            "Fields were written where labels matched. Captcha and the government "
            "card payment are not automated, so this is not a filed visa. "
            "Finish on evisa.gov.vn and save the real registration code."
        )
        if payload.notes:
            reason += " Notes: " + "; ".join(payload.notes)
        return await _finish(
            job,
            session,
            status=SubmissionJobStatus.MANUAL_TAKEOVER,
            label="Human finish required",
            detail=reason,
            error="awaiting_human_captcha_or_payment",
        )
    except Exception as exc:
        return await _finish(
            job,
            session,
            status=SubmissionJobStatus.FAILED,
            label="Worker error",
            detail=str(exc),
            error=str(exc),
        )
    finally:
        if browser is not None:
            try:
                await browser.close()
            except Exception:
                pass


async def get_latest_job_for_case(
    session: AsyncSession,
    case_id: int,
) -> PortalSubmissionJob | None:
    """Return the most recent portal submission job for a case."""
    result = await session.scalars(
        select(PortalSubmissionJob)
        .where(PortalSubmissionJob.case_id == case_id)
        .order_by(PortalSubmissionJob.created_at.desc())
        .limit(1)
    )
    return result.first()


async def list_recent_jobs(
    session: AsyncSession,
    limit: int = 50,
) -> list[PortalSubmissionJob]:
    """Admin dashboard: list recent bot submission jobs."""
    result = await session.scalars(
        select(PortalSubmissionJob).order_by(PortalSubmissionJob.id.desc()).limit(limit)
    )
    return list(result.all())
