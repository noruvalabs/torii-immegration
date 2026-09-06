"""One short plan for the whole application, the way an adviser would give it.

The packet step used to draw every stage of the process as a numbered list — sixteen of
them, most of which say something the applicant either already did or cannot act on
today. That is a process diagram, not advice. What a person filing an application
actually wants is the answer to three questions: what do I start today, what happens
after that, and what is going to get this refused.

This planner takes everything the case already holds — scope, answers, checklist, the
items that come from a bank or an airline, the cited filing steps, deadlines — and
reduces it to that. It is deliberately short: five things to start, a handful of filing
steps, the real risks, and the questions Torii could not answer from the data.

Two rules hold throughout:

* Nothing is invented. The planner is given the case's own facts and told to work only
  from them; anything it cannot determine goes in ``questions`` for the applicant to
  answer rather than being guessed at.
* When the model is unavailable or returns something unusable, the deterministic
  fallback builds the same shape from the journey data directly. A degraded plan is the
  applicant's own checklist re-ordered by lead time — never a plausible-sounding
  invention.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import structlog

from torii_ai.config import Settings
from torii_ai.llm.groq import ChatClient
from torii_ai.services.ops_scraper import country_label, extract_json

log = structlog.get_logger()

DISCLAIMER = (
    "This plan is AI-assisted preparation guidance built from your own answers and the "
    "published requirements for this application. It is not legal advice and not a "
    "government decision."
)

CASE_PLAN_SYSTEM_PROMPT = """You are a senior immigration case adviser writing a short action plan for one applicant.

You are given everything known about their case: the visa route, their answers, their document checklist, the items that must be obtained from third parties (banks, airlines, hotels, employers, other governments) with the lead time each one takes, the official filing steps, and where it is filed.

Write the plan the way an experienced adviser briefs a client: direct, specific to THIS case, and short. Not a description of the process — a list of what to do.

Hard rules:
- Use ONLY the facts you are given. Never state a fee, an office, a processing time, a deadline or a requirement that does not appear in the input.
- If something important is unknown, put it in "questions" as a question for the applicant. Do not guess it.
- Never say a document has been provided or verified unless its status says so.
- Order "start_now" by lead time, longest first. Those items decide the filing date.
- Refer to the applicant as "you".
- Keep every field short: a title is under 10 words, a detail is one or two sentences.

Return STRICT JSON only, with no markdown fences:
{
  "headline": "One sentence saying where this application stands right now.",
  "ready_to_file": true or false,
  "time_to_ready": "Plain-language estimate built from the lead times given, e.g. 'about 3-4 weeks, driven by the police certificate'. Use null if the input does not support an estimate.",
  "start_now": [
    {"title": "Short action", "detail": "What to ask for and from whom.", "lead_time": "How long this takes, from the input."}
  ],
  "then": [
    {"title": "Short step", "detail": "One or two sentences."}
  ],
  "risks": [
    {"title": "Short risk", "detail": "Why this gets applications handed back, and what to do about it."}
  ],
  "questions": ["A question only the applicant can answer."]
}

Limits: at most 5 items in "start_now", 5 in "then", 4 in "risks", 3 in "questions". Fewer is better."""


@dataclass
class CasePlanRequest:
    """Everything the planner is allowed to reason from."""

    scope_label: str = "Immigration application"
    destination_code: str = ""
    nationality: str | None = None
    residence_country: str | None = None
    case_reference: str = ""
    intake_answers: dict[str, Any] = field(default_factory=dict)
    checklist: list[dict[str, Any]] = field(default_factory=list)
    external_tasks: list[dict[str, Any]] = field(default_factory=list)
    stages: list[dict[str, Any]] = field(default_factory=list)
    office: str | None = None
    filed_by: str | None = None
    fee_note: str | None = None
    notes: list[str] = field(default_factory=list)
    submitted: bool = False
    custom_instructions: str | None = None
    locale: str = "en"


def _is_open(item: dict[str, Any]) -> bool:
    return str(item.get("status") or "needed") not in ("gathered", "uploaded")


def _clip(items: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    return items[:limit]


def _text(value: Any, limit: int = 400) -> str:
    return str(value or "").strip()[:limit]


class AICasePlanner:
    """Reduces a whole case to a short, ordered plan."""

    def __init__(self, *, chat: ChatClient, settings: Settings) -> None:
        self._chat = chat
        self._settings = settings

    async def plan(self, req: CasePlanRequest) -> dict[str, Any]:
        prompt = self._user_prompt(req)
        model_name = getattr(self._chat, "_model", "Torii AI")

        data: dict[str, Any] | None = None
        try:
            raw = await self._chat.complete(system=CASE_PLAN_SYSTEM_PROMPT, user=prompt)
            data = extract_json(raw)
        except Exception as exc:  # pragma: no cover - depends on the provider being reachable
            log.warning("case_plan.llm_failed", error=str(exc))

        if not isinstance(data, dict) or not data.get("headline"):
            log.info("case_plan.fallback", case=req.case_reference)
            return {
                **self._fallback(req),
                "model_used": "Torii planner (offline)",
                "generated_at": datetime.now(UTC).isoformat(),
                "disclaimer": DISCLAIMER,
            }

        return {
            "headline": _text(data.get("headline")),
            "ready_to_file": bool(data.get("ready_to_file")),
            "time_to_ready": _text(data.get("time_to_ready"), 160) or None,
            "start_now": self._actions(data.get("start_now"), 5),
            "then": self._actions(data.get("then"), 5),
            "risks": self._actions(data.get("risks"), 4),
            "questions": [
                _text(question, 240)
                for question in (data.get("questions") or [])
                if isinstance(question, str) and question.strip()
            ][:3],
            "model_used": model_name,
            "generated_at": datetime.now(UTC).isoformat(),
            "disclaimer": DISCLAIMER,
        }

    @staticmethod
    def _actions(raw: Any, limit: int) -> list[dict[str, Any]]:
        actions: list[dict[str, Any]] = []
        if not isinstance(raw, list):
            return actions
        for item in raw:
            if not isinstance(item, dict):
                continue
            title = _text(item.get("title"), 120)
            if not title:
                continue
            action: dict[str, Any] = {"title": title, "detail": _text(item.get("detail"))}
            lead_time = _text(item.get("lead_time"), 160)
            if lead_time:
                action["lead_time"] = lead_time
            actions.append(action)
        return actions[:limit]

    def _user_prompt(self, req: CasePlanRequest) -> str:
        nationality = country_label(req.nationality) or req.nationality or "not stated"
        residence = country_label(req.residence_country) or req.residence_country or nationality
        open_tasks = [task for task in req.external_tasks if _is_open(task)]
        held_tasks = [task for task in req.external_tasks if not _is_open(task)]
        open_documents = [item for item in req.checklist if _is_open(item)]

        lines = [
            f"Visa route: {req.scope_label}",
            f"Applicant nationality: {nationality}",
            f"Applicant lives in: {residence}",
            f"Today: {datetime.now(UTC).strftime('%Y-%m-%d')}",
            f"Already filed: {'yes' if req.submitted else 'no'}",
        ]
        if req.office:
            lines.append(f"Filed at: {req.office}")
        if req.filed_by:
            lines.append(f"Filed by: {req.filed_by}")
        if req.fee_note:
            lines.append(f"Official fee: {req.fee_note}")
        if req.notes:
            lines.append("Notes on this route: " + " | ".join(str(note) for note in req.notes))

        lines += [
            "",
            "ITEMS THAT MUST COME FROM SOMEONE ELSE (these decide the filing date):",
            json.dumps(
                [
                    {
                        "title": task.get("title"),
                        "from": task.get("arranged_with"),
                        "lead_time": task.get("lead_time"),
                        "must_show": task.get("how_to_obtain") or task.get("guidance"),
                        "required": task.get("is_required", True),
                    }
                    for task in _clip(open_tasks, 12)
                ],
                indent=2,
                default=str,
            )
            or "[]",
        ]
        if held_tasks:
            lines += [
                "",
                "ALREADY OBTAINED (do not ask for these again): "
                + ", ".join(str(task.get("title")) for task in held_tasks[:12]),
            ]

        lines += [
            "",
            "OTHER CHECKLIST ITEMS STILL OPEN:",
            json.dumps(
                [
                    {"name": item.get("name"), "required": item.get("is_required", True)}
                    for item in _clip(open_documents, 15)
                ],
                indent=2,
                default=str,
            ),
            "",
            "OFFICIAL FILING STEPS FOR THIS ROUTE:",
            json.dumps(
                [
                    {"title": stage.get("title"), "detail": stage.get("detail")}
                    for stage in req.stages
                    if str(stage.get("key") or "").startswith("filing")
                ]
                or [
                    {"title": stage.get("title"), "detail": stage.get("detail")}
                    for stage in _clip(req.stages, 8)
                ],
                indent=2,
                default=str,
            ),
            "",
            "APPLICANT'S OWN ANSWERS:",
            json.dumps(req.intake_answers, indent=2, default=str)[:4000],
        ]

        if req.custom_instructions:
            lines += ["", f"THE APPLICANT ALSO ASKS: {req.custom_instructions}"]

        lines += ["", "Write the plan. Return strict JSON only."]
        return "\n".join(lines)

    def _fallback(self, req: CasePlanRequest) -> dict[str, Any]:
        """The same plan, assembled from the case data with no model involved.

        Every line here is a restatement of something the case already says. It is worse
        prose than the model produces and it is meant to be — a plan that stayed silent
        or, worse, filled the gap with a plausible invention would be far more damaging
        than one that simply repeats the applicant's own checklist in the right order.
        """
        open_tasks = [task for task in req.external_tasks if _is_open(task)]
        open_required = [
            item for item in req.checklist if _is_open(item) and item.get("is_required", True)
        ]
        filing_steps = [
            stage for stage in req.stages if str(stage.get("key") or "").startswith("filing")
        ]

        if req.submitted:
            headline = "Filed. From here it is the office's move — keep your receipt and answer any request quickly."
        elif open_tasks or open_required:
            headline = (
                f"{len(open_required) or len(open_tasks)} item(s) still outstanding before this "
                "application can be filed."
            )
        else:
            headline = "Everything on your checklist is recorded — the paperwork is ready to file."

        start_now = [
            {
                "title": _text(task.get("title"), 120),
                "detail": _text(task.get("how_to_obtain")) or _text(task.get("guidance")),
                "lead_time": _text(task.get("lead_time"), 160),
            }
            for task in open_tasks[:5]
        ]
        if not start_now and open_required:
            start_now = [
                {"title": _text(item.get("name"), 120), "detail": _text(item.get("how_to_obtain"))}
                for item in open_required[:5]
            ]

        return {
            "headline": headline,
            "ready_to_file": not (open_tasks or open_required),
            "time_to_ready": None,
            "start_now": start_now,
            "then": [
                {"title": _text(stage.get("title"), 120), "detail": _text(stage.get("detail"))}
                for stage in filing_steps[:5]
            ],
            "risks": [],
            "questions": [],
        }


__all__ = ["AICasePlanner", "CasePlanRequest", "DISCLAIMER"]
