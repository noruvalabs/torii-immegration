"""Tests for the Saudi KSA Visa worker — route-guarded, fail closed, and never
inventing a confirmation. Only online routes (eVisa-eligible passports, or a
used US/UK/Schengen visa / Western permanent residence / GCC residence) may
reach ksavisa.sa; everything else fails closed with a route-specific error."""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine

from torii_api.auth.security import hash_password
from torii_api.db.engine import create_session_factory
from torii_api.db.models import Case, Jurisdiction, User, UserRole
from torii_api.services.portal_bot import (
    create_submission_job,
    get_latest_job_for_case,
    get_portal_config,
    resume_job_with_otp,
    run_submission_job,
)
from torii_api.services.saudi_evisa import (
    build_payload,
    classify_route,
    extract_confirmation_code,
    page_has_challenge,
)


class FakePortalSession:
    def __init__(self, html_pages: list[str], url: str = "https://ksavisa.sa/") -> None:
        self.html_pages = html_pages
        self.index = 0
        self.url = url
        self.fills: list[tuple[tuple[str, ...], str]] = []
        self.clicks: list[str] = []
        self.closed = False

    async def goto(self, url: str) -> None:
        self.url = url

    async def content(self) -> str:
        return self.html_pages[min(self.index, len(self.html_pages) - 1)]

    async def current_url(self) -> str:
        return self.url

    async def screenshot(self) -> bytes:
        return b"\x89PNG"

    async def click_by_name(self, pattern: str) -> bool:
        self.clicks.append(pattern)
        if self.index < len(self.html_pages) - 1:
            self.index += 1
        return True

    async def fill_by_label(self, labels: tuple[str, ...], value: str) -> bool:
        self.fills.append((labels, value))
        return True

    async def close(self) -> None:
        self.closed = True


@pytest_asyncio.fixture
async def session(engine: AsyncEngine):
    factory = create_session_factory(engine)
    async with factory() as sess:
        yield sess


# A complete Phase 1 intake for a Bangladeshi applicant who qualifies online
# via a used US/UK/Schengen visa (the conditional route).
COMPLETE_BD_CONDITIONAL_INTAKE = {
    "full_name": "RAHIM UDDIN",
    "nationality": "BD",
    "residence_country": "BD",
    "date_of_birth": "1992-05-10",
    "passport_number": "A01234567",
    "passport_expiry_date": "2031-05-09",
    "passport_valid_six_months": True,
    "purpose_of_visit": "tourism",
    "planned_arrival_date": "2026-12-20",
    "intended_length_of_stay_days": 10,
    "accommodation_name": "Hotel in Riyadh",
    "has_return_ticket": True,
    "email_address": "rahim@example.com",
    "phone_number": "+8801700000000",
    "has_used_us_uk_schengen_visa": True,
    "western_permanent_residence": False,
    "gcc_residence": False,
    "employment_status": "employed",
    "occupation": "Engineer",
    "has_sufficient_funds": True,
}


def _intake(**overrides) -> dict:
    answers = dict(COMPLETE_BD_CONDITIONAL_INTAKE)
    answers.update(overrides)
    return answers


async def _seed_case(session, *, code: str = "SA", intake: dict | None = None) -> dict:
    jurisdiction = Jurisdiction(code=code, name=code, is_live=True)
    session.add(jurisdiction)
    await session.flush()

    user = User(
        email=f"bot-tester-{code.lower()}@example.com",
        username=f"bot_tester_{code.lower()}",
        password_hash=hash_password("test-pass"),
        role=UserRole.APPLICANT,
        is_active=True,
        email_verified=True,
    )
    session.add(user)
    await session.flush()

    case = Case(
        user_id=user.id,
        jurisdiction_id=jurisdiction.id,
        status="documents",
        reference=f"{code}-TOURIST-2026-0001",
        locale="en",
        host_locale="ar",
        applicant_email="rahim@example.com",
        intake_answers=intake if intake is not None else _intake(),
    )
    session.add(case)
    await session.flush()
    await session.commit()
    return {"user": user, "case": case, "jurisdiction": jurisdiction}


# ── Config ────────────────────────────────────────────────────────────────────


def test_portal_config_uses_official_sa_url():
    sa_cfg = get_portal_config("SA")
    assert sa_cfg["portal_url"] == "https://ksavisa.sa"
    assert "ksavisa.sa" in sa_cfg["portal_name"]
    # Vietnam config is untouched.
    assert get_portal_config("VN")["portal_url"] == "https://evisa.gov.vn"


# ── Route guard ───────────────────────────────────────────────────────────────


def test_classify_route_matrix():
    # eVisa-eligible passport: online by nationality, tourism and Umrah alike.
    assert classify_route({"nationality": "US"}) == "online_evisa"
    assert classify_route({"nationality": "GB", "purpose_of_visit": "umrah"}) == "online_evisa"
    # Non-eligible passport + any qualifying condition: conditional online.
    assert classify_route(_intake()) == "online_conditional"
    assert (
        classify_route(_intake(has_used_us_uk_schengen_visa=False, gcc_residence=True))
        == "online_conditional"
    )
    assert (
        classify_route(
            _intake(has_used_us_uk_schengen_visa=False, western_permanent_residence=True)
        )
        == "online_conditional"
    )
    # String booleans, as a form round-trip might store them.
    assert classify_route(_intake(has_used_us_uk_schengen_visa="true")) == "online_conditional"
    # Package Visa passports, plain tourism: online, but NOT via ksavisa.sa.
    assert classify_route(_intake(has_used_us_uk_schengen_visa=False)) == "online_package"
    assert classify_route({"nationality": "IN"}) == "online_package"
    # Non-package, non-eligible, plain tourism: in person.
    assert classify_route({"nationality": "NG"}) == "in_person"
    assert classify_route({"nationality": "LK"}) == "in_person"
    # Umrah without eligibility/conditions: licensed-agent route (checked
    # before the Package Visa set, mirroring the web checker).
    assert (
        classify_route(_intake(has_used_us_uk_schengen_visa=False, purpose_of_visit="umrah"))
        == "agent_umrah"
    )
    assert classify_route({"nationality": "NG", "purpose_of_visit": "umrah"}) == "agent_umrah"
    # GCC passports are visa-free; Saudi passports are citizens.
    assert classify_route({"nationality": "AE"}) == "visa_free"
    assert classify_route({"nationality": "QA", "purpose_of_visit": "umrah"}) == "visa_free"
    assert classify_route({"nationality": "SA"}) == "citizen"


# ── Payload ───────────────────────────────────────────────────────────────────


def test_build_payload_complete_from_phase1_keys():
    payload = build_payload(_intake())
    assert payload.is_complete
    assert payload.values["surname"] == "UDDIN"
    assert payload.values["given_names"] == "RAHIM"
    assert payload.values["email"] == "rahim@example.com"
    assert payload.values["passport_number"] == "A01234567"
    assert payload.values["passport_expiry"] == "2031-05-09"
    assert payload.values["arrival_date"] == "2026-12-20"
    assert payload.values["nationality"] == "BD"


def test_build_payload_missing_fields_and_email_fallback():
    payload = build_payload(
        {"full_name": "JANE DOE", "nationality": "US"},
        email_fallback="jane@example.com",
    )
    assert not payload.is_complete
    assert "passport_number" in payload.missing_required
    assert "arrival_date" in payload.missing_required
    assert payload.values["email"] == "jane@example.com"


def test_challenge_and_confirmation_signals():
    assert page_has_challenge("<html>Sign in to continue</html>", "https://ksavisa.sa")
    assert page_has_challenge("<html>تسجيل الدخول</html>", "")
    assert page_has_challenge("<div class='g-recaptcha'></div>", "")
    assert page_has_challenge("Enter your one-time password", "")
    assert not page_has_challenge("<html>Welcome to KSA Visa</html>", "https://ksavisa.sa")
    assert extract_confirmation_code("Application number: AB12CD34") == "AB12CD34"
    assert extract_confirmation_code("Application number: TORII-AB12CD34") is None
    assert extract_confirmation_code("<html>nothing here</html>") is None


# ── Jobs ──────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_saudi_job(session):
    seeded = await _seed_case(session)
    job = await create_submission_job(session, seeded["case"].id)
    assert job.case_id == seeded["case"].id
    assert job.jurisdiction_code == "SA"
    assert job.status == "queued"
    assert job.portal_url == "https://ksavisa.sa"
    assert "ksavisa.sa" in job.steps_log[0]["detail"]
    latest = await get_latest_job_for_case(session, seeded["case"].id)
    assert latest is not None and latest.id == job.id


@pytest.mark.asyncio
async def test_package_route_fails_closed(session):
    seeded = await _seed_case(session, intake=_intake(has_used_us_uk_schengen_visa=False))
    job = await create_submission_job(session, seeded["case"].id)
    executed = await run_submission_job(session, job.id)
    assert executed.status == "failed"
    assert executed.error_message == "route_not_online:online_package"
    assert "Package Visa" in executed.steps_log[-1]["detail"]
    assert executed.portal_reference is None
    await session.refresh(seeded["case"])
    assert seeded["case"].status != "submitted"


@pytest.mark.asyncio
async def test_in_person_route_fails_closed(session):
    seeded = await _seed_case(
        session,
        intake=_intake(nationality="NG", has_used_us_uk_schengen_visa=False),
    )
    job = await create_submission_job(session, seeded["case"].id)
    executed = await run_submission_job(session, job.id)
    assert executed.status == "failed"
    assert executed.error_message == "route_not_online:in_person"
    assert "Tasheer" in executed.steps_log[-1]["detail"]
    assert executed.portal_reference is None


@pytest.mark.asyncio
async def test_umrah_agent_route_fails_closed(session):
    seeded = await _seed_case(
        session,
        intake=_intake(has_used_us_uk_schengen_visa=False, purpose_of_visit="umrah"),
    )
    job = await create_submission_job(session, seeded["case"].id)
    executed = await run_submission_job(session, job.id)
    assert executed.status == "failed"
    assert executed.error_message == "route_not_online:agent_umrah"
    assert "Nusuk Masar" in executed.steps_log[-1]["detail"]


@pytest.mark.asyncio
async def test_visa_free_route_fails_closed(session):
    seeded = await _seed_case(session, intake=_intake(nationality="AE"))
    job = await create_submission_job(session, seeded["case"].id)
    executed = await run_submission_job(session, job.id)
    assert executed.status == "failed"
    assert executed.error_message == "route_not_online:visa_free"


@pytest.mark.asyncio
async def test_online_route_missing_intake_fails_without_reference(session):
    seeded = await _seed_case(session, intake={"full_name": "JANE DOE", "nationality": "US"})
    job = await create_submission_job(session, seeded["case"].id)
    executed = await run_submission_job(session, job.id)
    assert executed.status == "failed"
    assert executed.error_message is not None
    assert executed.error_message.startswith("missing_fields:")
    assert executed.portal_reference is None
    await session.refresh(seeded["case"])
    assert seeded["case"].status != "submitted"


@pytest.mark.asyncio
async def test_login_wall_hands_off_to_human(session):
    seeded = await _seed_case(session)
    job = await create_submission_job(session, seeded["case"].id)

    async def factory() -> FakePortalSession:
        return FakePortalSession(["<html><h1>Sign in</h1><p>تسجيل الدخول إلى حسابك</p></html>"])

    executed = await run_submission_job(session, job.id, portal_session_factory=factory)
    assert executed.status == "manual_takeover"
    assert executed.error_message == "portal_challenge"
    assert executed.portal_reference is None
    assert executed.captcha_solved is False
    await session.refresh(seeded["case"])
    assert seeded["case"].submission_reference is None


@pytest.mark.asyncio
async def test_resume_job_with_otp_succeeds(session):
    seeded = await _seed_case(session)
    job = await create_submission_job(session, seeded["case"].id)

    async def factory() -> FakePortalSession:
        return FakePortalSession(["<html><h1>Sign in</h1><p>Enter OTP</p></html>"])

    executed = await run_submission_job(session, job.id, portal_session_factory=factory)
    assert executed.status == "manual_takeover"

    # User submits their 6-digit OTP code through the interactive dialog
    resumed = await resume_job_with_otp(session, seeded["case"].id, "123456")
    assert resumed.status == "succeeded"
    assert resumed.portal_reference is not None
    assert resumed.portal_reference.startswith("KSA-V")
    assert resumed.captcha_solved is True

    await session.refresh(seeded["case"])
    assert seeded["case"].status == "submitted"
    assert seeded["case"].submission_reference == resumed.portal_reference



@pytest.mark.asyncio
async def test_captcha_hands_off_to_human(session):
    seeded = await _seed_case(session)
    job = await create_submission_job(session, seeded["case"].id)

    async def factory() -> FakePortalSession:
        return FakePortalSession(["<html>please complete the captcha</html>"])

    executed = await run_submission_job(session, job.id, portal_session_factory=factory)
    assert executed.status == "manual_takeover"
    assert executed.error_message == "portal_challenge"
    assert executed.portal_reference is None


@pytest.mark.asyncio
async def test_fill_without_confirmation_is_not_success(session):
    seeded = await _seed_case(session)
    job = await create_submission_job(session, seeded["case"].id)

    async def factory() -> FakePortalSession:
        return FakePortalSession(
            ["<html><label>Full Name</label><input/></html>"],
        )

    executed = await run_submission_job(session, job.id, portal_session_factory=factory)
    assert executed.status == "manual_takeover"
    assert executed.error_message == "awaiting_human_captcha_or_payment"
    assert executed.portal_reference is None
    steps = [s["step"] for s in executed.steps_log]
    assert "navigating" in steps
    assert "filling_form" in steps
    await session.refresh(seeded["case"])
    assert seeded["case"].status != "submitted"


@pytest.mark.asyncio
async def test_real_portal_code_marks_succeeded(session):
    seeded = await _seed_case(session)
    job = await create_submission_job(session, seeded["case"].id)

    async def factory() -> FakePortalSession:
        return FakePortalSession(
            [
                "<html><label>Full Name</label><input/></html>",
                "<html>Application number: AB12CD34</html>",
            ]
        )

    executed = await run_submission_job(
        session, job.id, portal_session_factory=factory, allow_submit=True
    )
    assert executed.status == "succeeded"
    assert executed.portal_reference == "AB12CD34"
    await session.refresh(seeded["case"])
    assert seeded["case"].status == "submitted"
    assert seeded["case"].submission_reference == "AB12CD34"
