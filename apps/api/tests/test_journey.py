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

