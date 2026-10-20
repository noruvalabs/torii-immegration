"""Deterministic next-step guidance for an applicant case (US-01 / US-02 / US-04+).

Framework-free so the API, dashboard, and tests share one phase computation.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from torii_api.services.intake import IntakeProgress, parse_questions, progress_for

GuidancePhase = Literal[
    "research",
    "intake",
    "eligibility",
    "checklist",
    "forms",
    "review",
    "packet",
    "done",
    "blocked",
]


class CaseGuidance(BaseModel):
    phase: GuidancePhase
    title: str
    instruction: str
    cta_label: str
    blocked_reason: str | None = None
    progress: IntakeProgress | None = None
    scope_label: str | None = None
    deadlines: dict[str, Any] | None = None


def _has_live_defs(
    *,
    has_intake: bool,
    has_eligibility: bool,
    has_documents: bool,
    has_forms: bool,
) -> bool:
    return has_intake and has_eligibility and has_documents and has_forms


def compute_guidance(
    *,
    intake_questions: list[dict[str, Any]] | None,
    answers: dict[str, Any],
    eligibility_snapshot: dict[str, Any] | None,
    checklist_items: list[dict[str, Any]],
    generated_forms: list[dict[str, Any]],
    review_flags_acknowledged: bool,
    packet_snapshot: dict[str, Any] | None,
    status: str,
    has_intake_def: bool,
    has_eligibility_def: bool,
    has_document_def: bool,
    has_form_def: bool,
    research_status: str | None = None,
    scope_label: str | None = None,
    deadlines: dict[str, Any] | None = None,
) -> CaseGuidance:
    """Return the single next action an applicant should take."""
    if status == "submitted":
        return CaseGuidance(
            phase="done",
            title="Application submitted",
            instruction="Your packet has been submitted. Track status from your cases list.",
            cta_label="View packet",
            scope_label=scope_label,
            deadlines=deadlines,
        )

    if not _has_live_defs(
        has_intake=has_intake_def,
        has_eligibility=has_eligibility_def,
        has_documents=has_document_def,
        has_forms=has_form_def,
    ):
        # No live content pack for this scope: the case is research-driven. The LLM proposed,
        # a completed snapshot is usable, but the live tables are empty (NF-1/NF-2 preserved).
        if research_status == "completed":
            return CaseGuidance(
                phase="intake",
                title="Answer the intake questions",
                instruction=(
                    "We researched the official requirements for this case. "
                    "Answer the questions so we can build your document list and forms."
                ),
                cta_label="Continue intake",
                progress=progress_for(parse_questions(intake_questions or []), answers),
                scope_label=scope_label,
                deadlines=deadlines,
            )
        if research_status in ("queued", "running", "stale"):
            title = (
                "Refreshing requirements for your case"
                if research_status == "stale"
                else "Researching requirements for your case"
            )
            instruction = (
                "We are checking the latest official sources for this case. "
                "This usually takes under a minute."
            )
            return CaseGuidance(
                phase="research",
                title=title,
                instruction=instruction,
                cta_label="Check status",
                scope_label=scope_label,
                deadlines=deadlines,
            )
        if research_status == "failed":
            return CaseGuidance(
                phase="research",
                title="We could not research this case automatically",
                instruction=(
                    "We could not verify official requirements for this case. "
                    "Request human help and we will prepare it manually."
                ),
                cta_label="Request human help",
                blocked_reason="research_failed",
                scope_label=scope_label,
                deadlines=deadlines,
            )
        return CaseGuidance(
            phase="blocked",
            title="This visa path is not fully configured yet",
            instruction=(
                "We cannot guide this combination end-to-end yet. "
                "Choose another live path or request human help."
            ),
            cta_label="Back to cases",
            blocked_reason="missing_live_workflow_definitions",
            scope_label=scope_label,
            deadlines=deadlines,
        )

    questions = parse_questions(intake_questions or [])
    progress = progress_for(questions, answers)

    if not progress.complete:
        return CaseGuidance(
            phase="intake",
            title="Answer the intake questions",
            instruction=(
                "Tell us about your identity, stay, and sponsor so we can check "
                "published eligibility rules and build your document list."
            ),
            cta_label="Continue intake",
            progress=progress,
            scope_label=scope_label,
            deadlines=deadlines,
        )

    if eligibility_snapshot is None:
        return CaseGuidance(
            phase="eligibility",
            title="Check eligibility",
            instruction=(
                "Run the rules-based screening against published criteria. "
                "This is preparation information, not a government decision."
            ),
            cta_label="Evaluate eligibility",
            progress=progress,
            scope_label=scope_label,
            deadlines=deadlines,
        )

    required_needed = [
        item
        for item in checklist_items
        if item.get("is_required") and item.get("status") == "needed"
    ]
    if not checklist_items or required_needed:
        remaining = len(required_needed) if checklist_items else None
        detail = (
            f"{remaining} required document(s) still needed."
            if remaining is not None
            else "Generate your personalized document checklist, then gather each item."
        )
        return CaseGuidance(
            phase="checklist",
            title="Gather required documents",
            instruction=(
                f"{detail} Reuse docs already in your wallet when they match, "
                "or upload/scan new ones. Follow official source links for how-to-obtain."
            ),
            cta_label="Open checklist" if checklist_items else "Generate checklist",
            progress=progress,
            scope_label=scope_label,
            deadlines=deadlines,
        )

    if not generated_forms:
        return CaseGuidance(
            phase="forms",
            title="Generate government forms",
            instruction="Auto-fill the official form template from your intake answers.",
            cta_label="Generate forms",
            progress=progress,
            scope_label=scope_label,
            deadlines=deadlines,
        )

    if packet_snapshot is None and not review_flags_acknowledged:
        return CaseGuidance(
            phase="review",
            title="Review for consistency",
            instruction=(
                "Run the pre-submission check for missing fields and mismatches, "
                "then acknowledge any flags before building the packet."
            ),
            cta_label="Run review",
            progress=progress,
            scope_label=scope_label,
            deadlines=deadlines,
        )

    if packet_snapshot is None:
        return CaseGuidance(
            phase="packet",
            title="Build your submission packet",
            instruction="Assemble forms and checklist into a printable packet for filing.",
            cta_label="Build packet",
            progress=progress,
            scope_label=scope_label,
            deadlines=deadlines,
        )

    return CaseGuidance(
        phase="done",
        title="Packet ready",
        instruction="Your packet is assembled. Download it or submit where e-file is enabled.",
        cta_label="View packet",
        progress=progress,
        scope_label=scope_label,
    )


def next_status_for_phase(phase: GuidancePhase, current: str) -> str | None:
    """Map a completed milestone to a case.status value. None = leave unchanged."""
    order = [
        "draft",
        "intake_complete",
        "payment_completed",
        "eligibility_checked",
        "checklist_ready",
        "forms_generated",
        "packet_ready",
        "submitted",
    ]
    targets: dict[GuidancePhase, str] = {
        "eligibility": "intake_complete",
        "checklist": "checklist_ready",
        "forms": "checklist_ready",
        "review": "forms_generated",
        "packet": "forms_generated",
        "done": "packet_ready",
    }
    target = targets.get(phase)
    if target is None:
        return None
    try:
        if order.index(current) >= order.index(target):
            return None
    except ValueError:
        return target
    return target


class ScopeCodes(BaseModel):
    jurisdiction_code: str = Field(min_length=2, max_length=8)
    visa_category_code: str = Field(min_length=1, max_length=32)
    action_code: str = Field(min_length=1, max_length=32)
