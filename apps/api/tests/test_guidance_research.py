"""Tests for research-driven guidance (a scope with no live content pack)."""

from __future__ import annotations

from torii_api.services.guidance import compute_guidance

RESEARCH_QUESTIONS = [
    {
        "key": "purpose",
        "prompt": "Why are you visiting the UK?",
        "type": "string",
    }
]


def _guidance(*, research_status: str | None = None, questions=None) -> object:
    return compute_guidance(
        intake_questions=questions,
        answers={},
        eligibility_snapshot=None,
        checklist_items=[],
        generated_forms=[],
        review_flags_acknowledged=False,
        packet_snapshot=None,
        status="draft",
        has_intake_def=False,
        has_eligibility_def=False,
        has_document_def=False,
        has_form_def=False,
        research_status=research_status,
        scope_label="UK · Standard Visitor · Apply",
    )


def test_completed_research_leads_to_intake() -> None:
    guidance = _guidance(research_status="completed", questions=RESEARCH_QUESTIONS)
    assert guidance.phase == "intake"
    assert guidance.progress is not None
    assert guidance.progress.complete is False
    assert "researched" in guidance.instruction.lower()


def test_queued_research_shows_research_phase() -> None:
    guidance = _guidance(research_status="queued")
    assert guidance.phase == "research"
    assert guidance.cta_label == "Check status"
    assert guidance.blocked_reason is None


def test_running_research_shows_research_phase() -> None:
    assert _guidance(research_status="running").phase == "research"


def test_stale_research_prompts_refresh() -> None:
    guidance = _guidance(research_status="stale")
    assert guidance.phase == "research"
    assert "refreshing" in guidance.title.lower()


def test_failed_research_requests_human_help() -> None:
    guidance = _guidance(research_status="failed")
    assert guidance.phase == "research"
    assert guidance.blocked_reason == "research_failed"
    assert guidance.cta_label == "Request human help"


def test_no_research_and_no_defs_blocks() -> None:
    guidance = _guidance(research_status=None)
    assert guidance.phase == "blocked"
    assert guidance.blocked_reason == "missing_live_workflow_definitions"


def test_research_status_ignored_when_live_defs_present() -> None:
    guidance = compute_guidance(
        intake_questions=RESEARCH_QUESTIONS,
        answers={},
        eligibility_snapshot=None,
        checklist_items=[],
        generated_forms=[],
        review_flags_acknowledged=False,
        packet_snapshot=None,
        status="draft",
        has_intake_def=True,
        has_eligibility_def=True,
        has_document_def=True,
        has_form_def=True,
        research_status="failed",
    )
    assert guidance.phase == "intake"
