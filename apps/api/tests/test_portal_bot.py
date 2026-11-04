"""Tests for the Vietnam eVisa worker — fail closed, never invent a confirmation."""

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
    list_recent_jobs,
    run_submission_job,
)
from torii_api.services.vietnam_evisa import (
    build_payload,
    extract_confirmation_code,
    page_has_challenge,
    split_passport_name,
    to_vn_date,
)


class FakePortalSession:
    def __init__(self, html_pages: list[str], url: str = "https://evisa.gov.vn/") -> None:
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


async def _seed_case(session, *, code: str = "VN", intake: dict | None = None) -> dict:
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

    default_intake = {
        "full_name": "JOHN DOE",
        "passport_number": "B12345678",
        "nationality": "American",
        "date_of_birth": "1990-01-15",
        "email": "john@example.com",
        "intended_entry_date": "2026-12-01",
        "sex": "male",
    }
    case = Case(
        user_id=user.id,
        jurisdiction_id=jurisdiction.id,
        status="documents",
        reference=f"{code}-TOURIST-2026-0001",
        locale="en",
        host_locale="vi",
        applicant_email="john@example.com",
        intake_answers=intake if intake is not None else default_intake,
    )
    session.add(case)
    await session.flush()
    await session.commit()
    return {"user": user, "case": case, "jurisdiction": jurisdiction}


def test_portal_config_uses_official_vn_url():
    vn_cfg = get_portal_config("VN")
    assert vn_cfg["portal_url"] == "https://evisa.gov.vn"
    assert "evisa.gov.vn" in vn_cfg["portal_name"]


def test_name_and_date_mapping():
    assert split_passport_name("JOHN DOE") == ("DOE", "JOHN")
    assert to_vn_date("2026-12-01") == "01/12/2026"
    payload = build_payload(
        {
            "full_name": "JOHN DOE",
            "passport_number": "B12345678",
            "nationality": "American",
            "date_of_birth": "1990-01-15",
            "email": "john@example.com",
            "intended_entry_date": "2026-12-01",
        }
    )
    assert payload.is_complete
    assert payload.values["surname"] == "DOE"
    assert payload.values["given_names"] == "JOHN"
    assert payload.values["entry_date"] == "01/12/2026"


def test_extract_confirmation_rejects_simulated_prefixes():
    assert extract_confirmation_code("Registration number: AB12CD34") == "AB12CD34"
    assert extract_confirmation_code("code VN-EVISA-2026-9999999") is None
    assert extract_confirmation_code("TORII-DOC-000001") is None
    assert page_has_challenge("<div class='g-recaptcha'></div>", "https://evisa.gov.vn")
    assert page_has_challenge("Enter verification code", "")


@pytest.mark.asyncio
async def test_create_submission_job(session):
    seeded = await _seed_case(session)
    job = await create_submission_job(session, seeded["case"].id)
    assert job.case_id == seeded["case"].id
    assert job.jurisdiction_code == "VN"
    assert job.status == "queued"
    assert job.portal_url == "https://evisa.gov.vn"


@pytest.mark.asyncio
async def test_missing_intake_fails_without_fake_reference(session):
    seeded = await _seed_case(session, intake={"full_name": "JOHN DOE"})
    job = await create_submission_job(session, seeded["case"].id)
    executed = await run_submission_job(session, job.id)
    assert executed.status == "failed"
    assert executed.portal_reference is None
    assert executed.captcha_solved is False
    await session.refresh(seeded["case"])
    assert seeded["case"].status != "submitted"


@pytest.mark.asyncio
async def test_captcha_hands_off_to_human(session):
    seeded = await _seed_case(session)
    job = await create_submission_job(session, seeded["case"].id)

    async def factory() -> FakePortalSession:
        return FakePortalSession(["<html>please complete the captcha</html>"])

    executed = await run_submission_job(session, job.id, portal_session_factory=factory)
    assert executed.status == "manual_takeover"
    assert executed.portal_reference is None
    assert executed.captcha_solved is False
    assert executed.error_message == "portal_challenge"
    await session.refresh(seeded["case"])
    assert seeded["case"].submission_reference is None


@pytest.mark.asyncio
async def test_fill_without_confirmation_is_not_success(session):
    seeded = await _seed_case(session)
    job = await create_submission_job(session, seeded["case"].id)

    async def factory() -> FakePortalSession:
        return FakePortalSession(
            ["<html><label>Surname</label><input/></html>"],
        )

    executed = await run_submission_job(session, job.id, portal_session_factory=factory)
    assert executed.status == "manual_takeover"
    assert executed.portal_reference is None
    steps = [s["step"] for s in executed.steps_log]
    assert "navigating" in steps
    assert "filling_form" in steps
    assert "connecting_proxy" not in steps
    assert "solving_captcha" not in steps
    await session.refresh(seeded["case"])
    assert seeded["case"].status != "submitted"


@pytest.mark.asyncio
async def test_real_portal_code_marks_succeeded(session):
    seeded = await _seed_case(session)
    job = await create_submission_job(session, seeded["case"].id)

    async def factory() -> FakePortalSession:
        return FakePortalSession(
            [
                "<html>form</html>",
                "<html>Registration number: EV9K2M18AB</html>",
            ]
        )

    executed = await run_submission_job(
        session, job.id, portal_session_factory=factory, allow_submit=True
    )
    assert executed.status == "succeeded"
    assert executed.portal_reference == "EV9K2M18AB"
    await session.refresh(seeded["case"])
    assert seeded["case"].status == "submitted"
    assert seeded["case"].submission_reference == "EV9K2M18AB"


@pytest.mark.asyncio
async def test_non_vietnam_is_not_simulated(session):
    seeded = await _seed_case(session, code="EG")
    job = await create_submission_job(session, seeded["case"].id)
    executed = await run_submission_job(session, job.id)
    assert executed.status == "failed"
    assert executed.portal_reference is None
    detail = executed.steps_log[-1]["detail"]
    assert executed.error_message == "unsupported_jurisdiction:EG"
    assert "not supported" in detail


@pytest.mark.asyncio
async def test_get_latest_job(session):
    seeded = await _seed_case(session)
    job = await create_submission_job(session, seeded["case"].id)
    latest = await get_latest_job_for_case(session, seeded["case"].id)
    assert latest is not None
    assert latest.id == job.id


@pytest.mark.asyncio
async def test_list_recent_jobs(session):
    seeded = await _seed_case(session)
    job1 = await create_submission_job(session, seeded["case"].id)
    job2 = await create_submission_job(session, seeded["case"].id)
    jobs = await list_recent_jobs(session, limit=10)
    assert len(jobs) >= 2
    job_ids = [j.id for j in jobs]
    assert job_ids[0] == job2.id
    assert job_ids[1] == job1.id
