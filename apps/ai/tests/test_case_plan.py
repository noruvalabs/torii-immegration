"""The short case plan that replaces a sixteen-step process diagram.

The two properties that matter: the plan is ordered by what actually delays a filing
(the third-party lead times, longest first), and when the model is unavailable the
fallback restates the applicant's own outstanding items rather than inventing a plan.
"""

from __future__ import annotations

import json

import pytest
from httpx import ASGITransport, AsyncClient

from torii_ai.config import Settings
from torii_ai.llm.groq import FakeChatClient
from torii_ai.main import create_app
from torii_ai.services.case_plan import AICasePlanner, CasePlanRequest

_EXTERNAL = [
    {
        "title": "Police clearance certificate",
        "arranged_with": "The police of every country you have lived in",
        "lead_time": "Two to eight weeks.",
        "how_to_obtain": "Apply at the police authority.",
        "is_required": True,
        "status": "needed",
    },
    {
        "title": "Bank balance certificate",
        "arranged_with": "Your bank",
        "lead_time": "A few days.",
        "how_to_obtain": "Ask your bank for a balance certificate.",
        "is_required": True,
        "status": "needed",
    },
    {
        "title": "Original passport",
        "arranged_with": "Your own passport authority",
        "lead_time": "Weeks if it needs renewing.",
        "is_required": True,
        "status": "gathered",
    },
]

_CHECKLIST = [
    {"name": "Day-by-day schedule of stay", "is_required": True, "status": "needed"},
    {"name": "Original passport", "is_required": True, "status": "gathered"},
]

_STAGES = [
    {"key": "documents", "title": "Gather the documents on your checklist", "detail": "..."},
    {
        "key": "filing_1",
        "title": "File at your Regional Immigration Services Bureau",
        "detail": "Applications are accepted in person on weekdays.",
    },
    {"key": "filing_2", "title": "Collect the decision", "detail": "The bureau notifies you."},
]


def _request(**overrides: object) -> CasePlanRequest:
    base = {
        "scope_label": "Japan - Student Visa - Renewal",
        "destination_code": "JP",
        "nationality": "BD",
        "case_reference": "JP-2026-000051",
        "intake_answers": {"full_name": "Hasib", "nationality": "BD"},
        "checklist": _CHECKLIST,
        "external_tasks": _EXTERNAL,
        "stages": _STAGES,
        "office": "Regional Immigration Services Bureau",
        "fee_note": "4,000 JPY",
    }
    base.update(overrides)
    return CasePlanRequest(**base)  # type: ignore[arg-type]


def _planner(reply: str) -> AICasePlanner:
    return AICasePlanner(chat=FakeChatClient(reply=reply), settings=Settings())


_GOOD_REPLY = json.dumps(
    {
        "headline": "Two documents stand between you and filing; the police certificate is the long pole.",
        "ready_to_file": False,
        "time_to_ready": "about 4-8 weeks, driven by the police certificate",
        "start_now": [
            {
                "title": "Request your police clearance certificate",
                "detail": "Apply at the police authority of every country you have lived in.",
                "lead_time": "Two to eight weeks.",
            },
            {
                "title": "Ask your bank for a balance certificate",
                "detail": "Request the certificate and the statement history.",
                "lead_time": "A few days.",
            },
        ],
        "then": [
            {
                "title": "File at your Regional Immigration Services Bureau",
                "detail": "In person, on a weekday.",
            }
        ],
        "risks": [
            {
                "title": "Police certificates expire",
                "detail": "Many are valid three to six months from issue.",
            }
        ],
        "questions": ["Which countries have you lived in for more than six months?"],
    }
)


async def test_plan_is_short_and_lead_time_ordered() -> None:
    plan = await _planner(_GOOD_REPLY).plan(_request())

    assert plan["ready_to_file"] is False
    assert plan["headline"]
    assert len(plan["start_now"]) <= 5
    # The item that takes weeks comes before the one that takes days.
    assert "police" in plan["start_now"][0]["title"].lower()
    assert plan["questions"] == ["Which countries have you lived in for more than six months?"]
    assert "not legal advice" in plan["disclaimer"]


async def test_the_model_is_shown_only_the_facts_of_this_case() -> None:
    chat = FakeChatClient(reply=_GOOD_REPLY)
    await AICasePlanner(chat=chat, settings=Settings()).plan(_request())
    prompt = chat.calls[0]["user"]

    # Outstanding work, with its lead time, is what the plan is built from.
    assert "Police clearance certificate" in prompt
    assert "Two to eight weeks." in prompt
    # Something already held is named as held, so the plan cannot ask for it again.
    assert "ALREADY OBTAINED" in prompt
    assert "Original passport" in prompt.split("ALREADY OBTAINED")[1]
    # Published facts are passed through; the prompt forbids inventing any others.
    assert "4,000 JPY" in prompt
    assert "Never state a fee" in chat.calls[0]["system"]


async def test_fallback_restates_the_case_rather_than_inventing_one() -> None:
    """With no usable model reply, the plan is the applicant's own open items, in order."""
    plan = await _planner("the model is unavailable").plan(_request())

    assert plan["model_used"] == "Torii planner (offline)"
    assert plan["ready_to_file"] is False
    titles = [action["title"] for action in plan["start_now"]]
    assert titles == ["Police clearance certificate", "Bank balance certificate"]
    # Nothing is asserted that the case did not already say.
    assert plan["risks"] == []
    assert plan["questions"] == []
    assert [action["title"] for action in plan["then"]] == [
        "File at your Regional Immigration Services Bureau",
        "Collect the decision",
    ]


async def test_a_case_with_nothing_outstanding_reads_as_ready() -> None:
    plan = await _planner("no json here").plan(
        _request(
            external_tasks=[{**_EXTERNAL[2]}],
            checklist=[{"name": "Original passport", "is_required": True, "status": "gathered"}],
        )
    )
    assert plan["ready_to_file"] is True
    assert "ready to file" in plan["headline"]


async def test_a_filed_case_is_not_told_to_start_gathering() -> None:
    plan = await _planner("no json here").plan(_request(submitted=True))
    assert "Filed." in plan["headline"]


@pytest.mark.asyncio
async def test_case_plan_endpoint() -> None:
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/ai/agentic/case-plan",
            json={
                "scope_label": "Japan - Student Visa - Renewal",
                "destination_code": "JP",
                "external_tasks": _EXTERNAL,
                "checklist": _CHECKLIST,
                "stages": _STAGES,
            },
        )
    assert response.status_code == 200
    body = response.json()
    assert body["headline"]
    assert isinstance(body["start_now"], list)
    assert body["disclaimer"]
