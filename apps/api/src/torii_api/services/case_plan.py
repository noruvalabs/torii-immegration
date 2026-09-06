"""The applicant's action plan: prepare the case, ask the model once, keep the answer.

Three things go wrong if the browser calls the AI service directly with the raw case, and
all three were happening:

* **It fails loudly.** The browser reaches the AI service through a proxy hop; when that
  service is not running, the applicant is shown ``500`` and gets nothing. A plan is
  assembled from facts the API already holds, so being unable to reach the model should
  degrade the wording, never the answer.
* **It is slow.** Sending the whole case — every intake answer, all seventeen stages with
  their full prose — makes a prompt several thousand tokens long for a reply of a few
  hundred. Groq bills the *reserved* output budget against the per-minute allowance too,
  so an oversized request is both slow and liable to be refused outright.
* **It is repeated.** Nothing kept the result, so every visit to the step paid for the
  same plan again.

This module fixes all three: it reduces the case to the few facts a plan is actually made
of, calls the model once through the AI service, and hands back something the caller
stores on the case. When the service cannot be reached the deterministic plan below is
returned instead — the applicant's own outstanding items, ordered by lead time. That is
worse prose than the model writes, and it is never wrong.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx
import structlog

from torii_api.config import get_settings

log = structlog.get_logger()

DISCLAIMER = (
    "This plan is AI-assisted preparation guidance built from your own answers and the "
    "published requirements for this application. It is not legal advice and not a "
    "government decision."
)

# How much of the case the model is shown. Everything past these limits is detail it
# would have to skim anyway, and skimming it is what makes the request slow.
_MAX_OPEN_TASKS = 8
_MAX_HELD_TASKS = 12
_MAX_OPEN_DOCUMENTS = 12
_MAX_FILING_STEPS = 6
_MAX_ANSWER_CHARS = 1200
_DETAIL_CHARS = 220

# The plan is short and the applicant is waiting for it on screen.
_TIMEOUT = httpx.Timeout(25.0, connect=2.0)


def _is_open(item: dict[str, Any]) -> bool:
    return str(item.get("status") or "needed") not in ("gathered", "uploaded")


def _label(value: Any) -> str:
    """Checklist text is either a string or a locale map; read both."""
    if isinstance(value, dict):
        return str(value.get("en") or next(iter(value.values()), "")).strip()
    return str(value or "").strip()


def _trim(value: Any, limit: int = _DETAIL_CHARS) -> str:
    text = _label(value)
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _useful_answers(answers: dict[str, Any]) -> dict[str, Any]:
    """The answers, minus the ones that say nothing, capped to a readable size."""
    kept: dict[str, Any] = {}
    budget = _MAX_ANSWER_CHARS
    for key, value in answers.items():
        text = str(value or "").strip()
        # An unanswered question tells the model nothing but costs it tokens; a data URL
        # (an uploaded photo) costs thousands and means less than its own field name.
        if not text or text.startswith("data:"):
            continue
        text = text[:120]
        cost = len(key) + len(text) + 6
        if cost > budget:
            break
        kept[key] = text
        budget -= cost
    return kept


def build_payload(
    *,
    journey: dict[str, Any],
    checklist: list[dict[str, Any]],
    answers: dict[str, Any],
    jurisdiction_code: str | None,
    nationality: str | None,
    residence_country: str | None,
) -> dict[str, Any]:
    """Reduce the case to what a plan is made of, and nothing else."""
    tasks = [task for task in journey.get("external_tasks") or [] if isinstance(task, dict)]
    stages = [stage for stage in journey.get("stages") or [] if isinstance(stage, dict)]
    filing = [stage for stage in stages if str(stage.get("key") or "").startswith("filing")]

    return {
        "scope_label": journey.get("scope_label") or "",
        "destination_code": (jurisdiction_code or "").upper(),
        "nationality": nationality,
        "residence_country": residence_country,
        "case_reference": journey.get("reference") or "",
        "intake_answers": _useful_answers(answers),
        "checklist": [
            {
                "name": _trim(item.get("name"), 120),
                "is_required": bool(item.get("is_required", True)),
            }
            for item in checklist
            if _is_open(item)
        ][:_MAX_OPEN_DOCUMENTS],
        "external_tasks": [
            {
                "title": _trim(task.get("title"), 120),
                "arranged_with": _trim(task.get("arranged_with"), 120),
                "lead_time": _trim(task.get("lead_time")),
                "how_to_obtain": _trim(task.get("how_to_obtain")),
                "is_required": bool(task.get("is_required", True)),
                "status": task.get("status"),
            }
            for task in tasks
            if _is_open(task)
        ][:_MAX_OPEN_TASKS]
        + [
            {"title": _trim(task.get("title"), 120), "status": task.get("status")}
            for task in tasks
            if not _is_open(task)
        ][:_MAX_HELD_TASKS],
        "stages": [
            {
                "key": stage.get("key"),
                "title": _trim(stage.get("title"), 120),
                "detail": _trim(stage.get("detail")),
            }
            for stage in (filing or stages)
        ][:_MAX_FILING_STEPS],
        "office": _trim(journey.get("office"), 200) or None,
        "filed_by": _trim(journey.get("filed_by"), 200) or None,
        "fee_note": _trim(journey.get("fee_note"), 200) or None,
        "notes": [_trim(note) for note in (journey.get("notes") or [])][:3],
        "submitted": bool(journey.get("submitted")),
    }


def offline_plan(payload: dict[str, Any]) -> dict[str, Any]:
    """The plan without a model: the applicant's own open items, longest lead time first.

    ``build_payload`` has already put the outstanding third-party items in lead-time order
    and dropped everything they already hold, so this is a restatement of the case rather
    than a judgement about it. Nothing here is asserted that the case did not already say.
    """
    open_tasks = [
        task
        for task in payload.get("external_tasks") or []
        if _is_open(task) and task.get("lead_time")
    ]
    open_documents = [
        item for item in payload.get("checklist") or [] if item.get("is_required", True)
    ]
    filing = [
        stage
        for stage in payload.get("stages") or []
        if str(stage.get("key") or "").startswith("filing")
    ] or list(payload.get("stages") or [])

    if payload.get("submitted"):
        headline = (
            "Filed. From here it is the office's move — keep your receipt and answer any "
            "request for a further document quickly."
        )
    elif open_tasks or open_documents:
        outstanding = len(open_tasks) + len(open_documents)
        headline = (
            f"{outstanding} item{'' if outstanding == 1 else 's'} still outstanding before this "
            "application can be filed."
        )
    else:
        headline = "Everything on your checklist is recorded — the paperwork is ready to file."

    start_now = [
        {
            "title": str(task.get("title") or ""),
            "detail": str(task.get("how_to_obtain") or ""),
            "lead_time": str(task.get("lead_time") or ""),
        }
        for task in open_tasks[:5]
    ]
    if not start_now:
        start_now = [
            {"title": str(item.get("name") or ""), "detail": ""} for item in open_documents[:5]
        ]

    return {
        "headline": headline,
        "ready_to_file": not (open_tasks or open_documents),
        "time_to_ready": None,
        "start_now": start_now,
        "then": [
            {"title": str(stage.get("title") or ""), "detail": str(stage.get("detail") or "")}
            for stage in filing[:5]
        ],
        "risks": [],
        "questions": [],
        "disclaimer": DISCLAIMER,
        "model_used": "Torii planner (offline)",
        "generated_at": datetime.now(UTC).isoformat(),
    }


async def request_plan(payload: dict[str, Any]) -> dict[str, Any]:
    """Ask the AI service for the plan; fall back rather than fail.

    The applicant is standing in front of this button. A plan they can act on, written
    plainly from their own checklist, beats an error message every time — so an
    unreachable or slow AI service degrades the prose, not the answer.
    """
    settings = get_settings()
    service_url = (settings.ai_service_url or "").rstrip("/")
    if not service_url:
        return offline_plan(payload)

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.post(f"{service_url}/ai/agentic/case-plan", json=payload)
        if response.status_code != 200:
            log.info("case_plan.ai_service_rejected", status=response.status_code)
            return offline_plan(payload)
        data = response.json()
    except Exception as exc:
        log.info("case_plan.ai_service_unreachable", error=str(exc))
        return offline_plan(payload)

    if not isinstance(data, dict) or not data.get("headline"):
        return offline_plan(payload)
    return data


__all__ = ["DISCLAIMER", "build_payload", "offline_plan", "request_plan"]
