"""The end-to-end journey, and what has to be arranged outside Torii.

Two properties matter here. The journey must not invent a requirement — every external
task traces back to a checklist item the case already has — and a stage the applicant has
not actually finished must never read as finished just because the workflow phase moved
past it.
"""

from __future__ import annotations

import json

from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from torii_api.services.case_plan import build_payload, offline_plan
from torii_api.services.intake import JP_WORK_RENEWAL_QUESTIONS
from torii_api.services.journey import build_journey, external_tasks

_CHECKLIST = [
    {
        "id": 1,
        "code": "passport_original",
        "name": "Original passport, valid for the whole stay",
        "how_to_obtain": "Bring the passport itself.",
        "why_required": "The visa is affixed to a page of this passport.",
        "is_required": True,
        "status": "gathered",
        "citation": {"url": "https://www.mofa.go.jp/j_info/visit/visa/short/index.html"},
    },
    {
        "id": 2,
        "code": "flight_hotel_reservations",
        "name": "Flight itinerary and accommodation bookings covering the whole stay",
        "how_to_obtain": "A reservation confirmation from the airline or agency, and the hotel.",
        "why_required": "A short stay is granted against a departure that is already booked.",
        "is_required": True,
        "status": "needed",
        "citation": {},
    },
    {
        "id": 3,
        "code": "bank_solvency_certificate",
        "name": "Bank balance certificate and the last six months of statements",
        "how_to_obtain": "Ask your bank for a balance certificate.",
        "why_required": "Means of support during the stay.",
        "is_required": True,
        "status": "needed",
        "citation": {},
    },
    {
        "id": 4,
        "code": "schedule_of_stay",
        "name": "Day-by-day schedule of stay",
        "how_to_obtain": "Write out each day of the trip.",
        "why_required": "A short stay is judged on whether the plan is coherent.",
        "is_required": True,
        "status": "needed",
        "citation": {},
    },
]


def _journey(**overrides: object) -> dict:
    kwargs: dict = {
        "reference": "JP-2026-000051",
        "scope_label": "Japan - Short-Stay Tourist",
        "phase": "packet",
        "case_status": "packet_ready",
        "checklist": _CHECKLIST,
        "forms": [],
        "submission_kit": None,
    }
    kwargs.update(overrides)
    return build_journey(**kwargs)  # type: ignore[arg-type]


def test_external_tasks_only_come_from_the_checklist() -> None:
    tasks = external_tasks(_CHECKLIST)
    codes = {task.code for task in tasks}
    # The schedule of stay is written by the applicant, not obtained from a third party.
    assert "schedule_of_stay" not in codes
    assert codes == {"passport_original", "flight_hotel_reservations", "bank_solvency_certificate"}
    # Nothing is asserted about a case whose checklist says nothing.
    assert external_tasks([]) == ()


def test_the_longest_lead_time_is_listed_first() -> None:
    checklist = [
        {"code": "bank", "name": "Bank balance certificate", "status": "needed"},
        {
            "code": "police_certificate",
            "name": "Police clearance certificate",
            "status": "needed",
        },
    ]
    assert [task.category for task in external_tasks(checklist)] == [
        "police_certificate",
        "funds",
    ]


def test_a_combined_requirement_describes_both_halves() -> None:
    task = next(
        item for item in external_tasks(_CHECKLIST) if item.code == "flight_hotel_reservations"
    )
    # Japan asks for the flight and the hotel as a single item; naming only the hotel
    # would drop the return flight out of the applicant's plan.
    assert set(task.categories) == {"accommodation", "travel_booking"}
    assert "airline" in task.arranged_with.lower()
    assert "hotel" in task.arranged_with.lower()
    # The requirement's own words are preserved; the category only adds the how and when.
    assert task.why_required.startswith("A short stay is granted")


def test_outstanding_documents_never_read_as_finished() -> None:
    journey = _journey()
    stages = {stage["key"]: stage for stage in journey["stages"]}
    # The phase has moved past the checklist, but three of four items are outstanding.
    assert stages["documents"]["status"] == "current"
    assert (stages["documents"]["done_count"], stages["documents"]["total_count"]) == (1, 4)
    assert stages["external"]["status"] == "current"
    assert stages["packet"]["status"] == "current"


def test_the_journey_reaches_past_submission() -> None:
    keys = [stage["key"] for stage in _journey()["stages"]]
    assert keys[0] == "scope"
    for expected in ("intake", "eligibility", "documents", "forms", "review", "packet"):
        assert expected in keys
    # It does not stop at "you have a PDF": filing, the wait, the decision and the next
    # renewal are part of the same picture.
    assert keys[-4:] == ["record", "await_decision", "outcome", "renewal"]


def test_a_submitted_case_shows_the_wait_as_the_live_stage() -> None:
    stages = {stage["key"]: stage for stage in _journey(case_status="submitted")["stages"]}
    assert stages["record"]["status"] == "done"
    assert stages["await_decision"]["status"] == "current"


def test_no_filing_route_is_invented_when_none_is_cited() -> None:
    stage = next(
        item
        for item in _journey(apply_url="https://www.moj.go.jp/isa/")["stages"]
        if item["key"] == "filing"
    )
    assert "will not invent one" in stage["detail"]
    assert stage["portal_url"] == "https://www.moj.go.jp/isa/"


async def _seed_scope(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.execute(
            text("INSERT INTO jurisdictions (code, name, is_live) VALUES ('JP', 'Japan', 1)")
        )
        jid = (
            await conn.execute(text("SELECT id FROM jurisdictions WHERE code = 'JP'"))
        ).scalar_one()
        await conn.execute(
            text(
                "INSERT INTO visa_categories (jurisdiction_id, code, name, is_live)"
                f" VALUES ({jid}, 'work', 'Work', 1)"
            )
        )
        await conn.execute(
            text(
                "INSERT INTO case_actions (jurisdiction_id, code, name, is_live)"
                f" VALUES ({jid}, 'renewal', 'Renewal', 1)"
            )
        )
        vc_id = (
            await conn.execute(
                text(f"SELECT id FROM visa_categories WHERE jurisdiction_id = {jid}")
            )
        ).scalar_one()
        ca_id = (
            await conn.execute(text(f"SELECT id FROM case_actions WHERE jurisdiction_id = {jid}"))
        ).scalar_one()
        await conn.execute(
            text(
                "INSERT INTO intake_definitions"
                " (jurisdiction_id, visa_category_id, case_action_id, questions, is_live)"
                f" VALUES ({jid}, {vc_id}, {ca_id}, :q, 1)"
            ),
            {"q": json.dumps(JP_WORK_RENEWAL_QUESTIONS)},
        )


async def test_journey_endpoint_describes_the_whole_case(
    client: AsyncClient, engine: AsyncEngine
) -> None:
    await _seed_scope(engine)
    register = await client.post(
        "/v1/auth/register", json={"email": "journey@example.com", "password": "secure-pass"}
    )
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    scoped = await client.post(
        "/v1/cases/scope",
        json={
            "jurisdiction_code": "JP",
            "visa_category_code": "work",
            "action_code": "renewal",
            "locale": "en",
        },
        headers=headers,
    )
    case_id = scoped.json()["id"]

    response = await client.get(f"/v1/cases/{case_id}/journey", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["reference"].startswith("JP-")
    assert body["stages"][0]["key"] == "scope"
    assert {stage["status"] for stage in body["stages"]} <= {"done", "current", "todo"}
    # Every stage carries who is doing the work, which is the point of the view.
    assert {stage["owner"] for stage in body["stages"]} <= {
        "torii",
        "you",
        "authority",
        "third_party",
    }


# -- The action plan -----------------------------------------------------------------


def test_payload_sent_to_the_model_is_small_and_relevant() -> None:
    """The prompt is the reason this was slow. Only what a plan is made of goes in."""
    journey = _journey()
    payload = build_payload(
        journey=journey,
        checklist=_CHECKLIST,
        answers={
            "full_name": "Hasib",
            "planned_arrival_date": "",
            "applicant_photo": "data:image/png;base64," + "A" * 50_000,
            "occupation": "Student",
        },
        jurisdiction_code="jp",
        nationality="BD",
        residence_country="JP",
    )

    # An unanswered question and an uploaded photo cost thousands of tokens and say
    # nothing a plan can act on.
    assert payload["intake_answers"] == {"full_name": "Hasib", "occupation": "Student"}
    assert payload["destination_code"] == "JP"
    # Only the filing steps, not all seventeen stages of the procedure.
    assert len(payload["stages"]) <= 6
    assert all(len(stage["detail"]) <= 220 for stage in payload["stages"])
    # Open items carry their lead time; held ones are named so the plan cannot re-ask.
    open_titles = [t["title"] for t in payload["external_tasks"] if t.get("lead_time")]
    assert "Flight itinerary and accommodation bookings covering the whole stay" in open_titles
    held = [t for t in payload["external_tasks"] if t["status"] == "gathered"]
    assert [t["title"] for t in held] == ["Original passport, valid for the whole stay"]


def test_offline_plan_restates_the_case_rather_than_inventing_one() -> None:
    payload = build_payload(
        journey=_journey(),
        checklist=_CHECKLIST,
        answers={},
        jurisdiction_code="JP",
        nationality=None,
        residence_country=None,
    )
    plan = offline_plan(payload)

    assert plan["ready_to_file"] is False
    assert "outstanding" in plan["headline"]
    # Longest lead time first: build_payload preserves the journey's own ordering.
    assert plan["start_now"][0]["title"].startswith("Flight itinerary")
    # Nothing is asserted that the case did not already say.
    assert plan["risks"] == []
    assert plan["questions"] == []
    assert "not legal advice" in plan["disclaimer"]


def test_offline_plan_does_not_tell_a_filed_case_to_gather_documents() -> None:
    payload = build_payload(
        journey=_journey(case_status="submitted"),
        checklist=_CHECKLIST,
        answers={},
        jurisdiction_code="JP",
        nationality=None,
        residence_country=None,
    )
    assert offline_plan(payload)["headline"].startswith("Filed.")


async def test_plan_is_built_once_and_kept_on_the_case(
    client: AsyncClient, engine: AsyncEngine
) -> None:
    """The applicant pays for the plan once; opening the step again reads it back."""
    await _seed_scope(engine)
    register = await client.post(
        "/v1/auth/register", json={"email": "plan@example.com", "password": "secure-pass"}
    )
    headers = {"Authorization": f"Bearer {register.json()['access_token']}"}
    scoped = await client.post(
        "/v1/cases/scope",
        json={
            "jurisdiction_code": "JP",
            "visa_category_code": "work",
            "action_code": "renewal",
            "locale": "en",
        },
        headers=headers,
    )
    case_id = scoped.json()["id"]

    # Nothing built yet.
    empty = await client.get(f"/v1/cases/{case_id}/plan", headers=headers)
    assert empty.status_code == 200
    assert empty.json()["plan"] is None

    built = await client.post(f"/v1/cases/{case_id}/plan", headers=headers)
    assert built.status_code == 200
    plan = built.json()["plan"]
    # No AI service is reachable from the tests, and the applicant still gets a plan
    # rather than the 500 they used to be shown.
    assert plan["headline"]
    assert plan["disclaimer"]
    assert plan["model_used"]

    stored = await client.get(f"/v1/cases/{case_id}/plan", headers=headers)
    assert stored.json()["plan"] == plan


async def test_plan_is_scoped_to_the_owner(client: AsyncClient, engine: AsyncEngine) -> None:
    await _seed_scope(engine)
    owner = await client.post(
        "/v1/auth/register", json={"email": "plan-owner@example.com", "password": "secure-pass"}
    )
    scoped = await client.post(
        "/v1/cases/scope",
        json={
            "jurisdiction_code": "JP",
            "visa_category_code": "work",
            "action_code": "renewal",
            "locale": "en",
        },
        headers={"Authorization": f"Bearer {owner.json()['access_token']}"},
    )
    intruder = await client.post(
        "/v1/auth/register", json={"email": "plan-intruder@example.com", "password": "secure-pass"}
    )
    response = await client.post(
        f"/v1/cases/{scoped.json()['id']}/plan",
        headers={"Authorization": f"Bearer {intruder.json()['access_token']}"},
    )
    assert response.status_code == 404


# -- Recording that the applicant filed it -------------------------------------------


async def _scoped_case(client: AsyncClient, email: str) -> tuple[dict[str, str], int]:
    register = await client.post(
        "/v1/auth/register", json={"email": email, "password": "secure-pass"}
    )
    headers = {"Authorization": f"Bearer {register.json()['access_token']}"}
    scoped = await client.post(
        "/v1/cases/scope",
        json={
            "jurisdiction_code": "JP",
            "visa_category_code": "work",
            "action_code": "renewal",
            "locale": "en",
        },
        headers=headers,
    )
    return headers, scoped.json()["id"]


async def test_filing_it_yourself_is_not_refused_for_lacking_e_file(
    client: AsyncClient, engine: AsyncEngine
) -> None:
    """Japan's bureau takes applications in person, so e-file is off — and irrelevant here.

    The packet step's button was calling the e-file endpoint, which answered someone who
    had been to the counter with "E-file is unavailable for this jurisdiction".
    """
    await _seed_scope(engine)
    headers, case_id = await _scoped_case(client, "filed@example.com")

    # E-filing really is unavailable, and still says so.
    refused = await client.post(f"/v1/cases/{case_id}/submit", headers=headers)
    assert refused.status_code == 400
    assert "E-file is unavailable" in refused.json()["detail"]

    # Recording your own filing is a different act, and it works.
    await client.post(f"/v1/cases/{case_id}/review", headers=headers)
    await client.post(f"/v1/cases/{case_id}/review/acknowledge", headers=headers)
    packet = await client.post(f"/v1/cases/{case_id}/packet", headers=headers)
    assert packet.status_code == 200
    filed = await client.post(f"/v1/cases/{case_id}/filed", headers=headers)
    assert filed.status_code == 200
    assert filed.json()["status"] == "submitted"
    assert filed.json()["filed_at"]
    # No receipt number is invented: that number comes from the office, not from Torii.
    assert filed.json()["submission_reference"] is None

    case = await client.get(f"/v1/cases/{case_id}", headers=headers)
    assert case.json()["status"] == "submitted"
    # And the journey moves on with it: the wait for a decision becomes the live stage.
    journey = await client.get(f"/v1/cases/{case_id}/journey", headers=headers)
    assert journey.json()["submitted"] is True
    stages = {stage["key"]: stage for stage in journey.json()["stages"]}
    assert stages["await_decision"]["status"] == "current"


async def test_a_case_with_no_packet_cannot_be_recorded_as_filed(
    client: AsyncClient, engine: AsyncEngine
) -> None:
    await _seed_scope(engine)
    headers, case_id = await _scoped_case(client, "no-packet@example.com")
    response = await client.post(f"/v1/cases/{case_id}/filed", headers=headers)
    assert response.status_code == 400
    assert "assemble your filing kit" in response.json()["detail"]


async def test_recording_a_filing_is_scoped_to_the_owner(
    client: AsyncClient, engine: AsyncEngine
) -> None:
    await _seed_scope(engine)
    _headers, case_id = await _scoped_case(client, "filed-owner@example.com")
    intruder = await client.post(
        "/v1/auth/register",
        json={"email": "filed-intruder@example.com", "password": "secure-pass"},
    )
    response = await client.post(
        f"/v1/cases/{case_id}/filed",
        headers={"Authorization": f"Bearer {intruder.json()['access_token']}"},
    )
    assert response.status_code == 404
