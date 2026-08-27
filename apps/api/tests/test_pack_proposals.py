"""The agent proposes, ops promote.

Research either went live automatically or not at all. These cover the middle: a diff
against the pack, with the source for each changed line, that a human accepts or rejects.
The tests that matter here are the ones about what the store *refuses* — an uncited line,
a second decision, a path that reaches outside its own scope.
"""

from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

from torii_api.services.pack_proposals import (
    STATUS_ACCEPTED,
    STATUS_PENDING,
    STATUS_REJECTED,
    Change,
    ProposalError,
    decide,
    diff_against_pack,
    list_proposals,
    load_proposal,
    propose,
)

CITATION = {
    "authority": "Immigration Services Agency of Japan",
    "title": "Application for Extension of Period of Stay",
    "url": "https://www.moj.go.jp/isa/applications/procedures/16-3.html",
}

SCOPE = "jp/work.renewal"


@pytest.fixture
def packs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A throwaway copy of the packs, so accepting a proposal never edits the repo."""
    from torii_api.services import content_packs, pack_proposals

    source = content_packs.resolve_packs_dir()
    destination = tmp_path / "jurisdictions"
    shutil.copytree(source, destination)
    monkeypatch.setattr(pack_proposals, "resolve_packs_dir", lambda: destination)
    return destination


def _pack(packs: Path) -> dict:
    return yaml.safe_load((packs / "jp" / "work.renewal.yml").read_text(encoding="utf-8"))


def _question(packs: Path, key: str) -> dict:
    return next(q for q in _pack(packs)["intake"]["questions"] if q["key"] == key)


# ── Proposing ──────────────────────────────────────────────────────────────────────


def test_a_proposal_records_what_the_pack_says_now(packs: Path) -> None:
    before = _question(packs, "full_name")["prompt"]
    proposal = propose(
        scope=SCOPE,
        changes=[
            Change(
                path="intake.questions[key=full_name].prompt",
                to="What is your full name, exactly as printed on your passport?",
                citation=CITATION,
            )
        ],
        source="agentic_research",
        summary="Match the ministry's own wording.",
    )
    assert proposal.status == STATUS_PENDING
    assert len(proposal.changes) == 1
    # The reviewer sees both sides without having to go and look.
    assert proposal.changes[0].from_ == before
    assert proposal.changes[0].to != before


def test_an_uncited_change_is_refused_rather_than_queued(packs: Path) -> None:
    """NF-2 at write time: a reviewer should never be shown a line with no source."""
    with pytest.raises(ProposalError, match="official source"):
        propose(
            scope=SCOPE,
            changes=[
                Change(
                    path="intake.questions[key=full_name].prompt",
                    to="Anything at all",
                    citation={},
                )
            ],
            source="agentic_research",
        )
    assert list_proposals() == []


def test_a_citation_without_an_http_url_does_not_count(packs: Path) -> None:
    with pytest.raises(ProposalError):
        propose(
            scope=SCOPE,
            changes=[
                Change(
                    path="intake.questions[key=full_name].prompt",
                    to="Anything",
                    citation={"authority": "ISA", "title": "Somewhere", "url": "see the notice"},
                )
            ],
            source="agentic_research",
        )


def test_a_change_that_changes_nothing_is_not_queued(packs: Path) -> None:
    current = _question(packs, "full_name")["prompt"]
    with pytest.raises(ProposalError, match="already matches"):
        propose(
            scope=SCOPE,
            changes=[
                Change(
                    path="intake.questions[key=full_name].prompt",
                    to=current,
                    citation=CITATION,
                )
            ],
            source="agentic_research",
        )


def test_a_scope_outside_the_packs_directory_is_refused(packs: Path) -> None:
    for scope in ("../secrets", "jp/../../etc.passwd", "JP/work.renewal", "jp/work"):
        with pytest.raises(ProposalError):
            propose(
                scope=scope,
                changes=[Change(path="a.b", to="x", citation=CITATION)],
                source="agentic_research",
            )


# ── Deciding ───────────────────────────────────────────────────────────────────────


def test_accepting_rewrites_the_pack(packs: Path) -> None:
    wording = "What is your full name, exactly as printed on your passport?"
    proposal = propose(
        scope=SCOPE,
        changes=[
            Change(
                path="intake.questions[key=full_name].prompt", to=wording, citation=CITATION
            )
        ],
        source="agentic_research",
    )
    decided = decide(proposal.id, accept=True, reviewer="ops@aurev.ai", note="Reads better.")

    assert decided.status == STATUS_ACCEPTED
    assert decided.decided_by == "ops@aurev.ai"
    assert _question(packs, "full_name")["prompt"] == wording


def test_rejecting_leaves_the_pack_alone(packs: Path) -> None:
    before = _question(packs, "full_name")["prompt"]
    proposal = propose(
        scope=SCOPE,
        changes=[
            Change(path="intake.questions[key=full_name].prompt", to="Nope", citation=CITATION)
        ],
        source="agentic_research",
    )
    decided = decide(proposal.id, accept=False, reviewer="ops@aurev.ai", note="Wrong.")

    assert decided.status == STATUS_REJECTED
    assert _question(packs, "full_name")["prompt"] == before


def test_a_proposal_is_decided_once(packs: Path) -> None:
    proposal = propose(
        scope=SCOPE,
        changes=[
            Change(path="intake.questions[key=full_name].prompt", to="Once", citation=CITATION)
        ],
        source="agentic_research",
    )
    decide(proposal.id, accept=False, reviewer="ops@aurev.ai")
    with pytest.raises(ProposalError, match="already"):
        decide(proposal.id, accept=True, reviewer="someone.else@aurev.ai")


def test_accepting_touches_only_the_lines_that_were_reviewed(packs: Path) -> None:
    """The reviewer approved a diff, not a rewrite of the file."""
    before = _pack(packs)
    proposal = propose(
        scope=SCOPE,
        changes=[
            Change(
                path="intake.questions[key=full_name].prompt", to="Reviewed", citation=CITATION
            )
        ],
        source="agentic_research",
    )
    decide(proposal.id, accept=True, reviewer="ops@aurev.ai")
    after = _pack(packs)

    assert after["scope"] == before["scope"]
    assert len(after["intake"]["questions"]) == len(before["intake"]["questions"])
    changed = [
        q["key"]
        for q, was in zip(after["intake"]["questions"], before["intake"]["questions"], strict=True)
        if q != was
    ]
    assert changed == ["full_name"]


def test_an_unknown_proposal_cannot_be_decided(packs: Path) -> None:
    with pytest.raises(ProposalError, match="no such proposal"):
        decide("2026-01-01-jp-work-renewal-deadbeef", accept=True, reviewer="ops@aurev.ai")


# ── Diffing a whole researched pack ────────────────────────────────────────────────


def test_a_researched_pack_becomes_the_lines_it_would_change(packs: Path) -> None:
    """The agent returns a pack; ops review lines."""
    current = _pack(packs)
    proposed = {
        "intake": {
            "questions": [
                {
                    "key": "full_name",
                    "prompt": "Your full name as printed on your passport",
                    "citation": CITATION,
                },
                # Unchanged, so it is not a line to review.
                {
                    "key": "nationality",
                    "prompt": next(
                        q["prompt"]
                        for q in current["intake"]["questions"]
                        if q["key"] == "nationality"
                    ),
                    "citation": CITATION,
                },
            ]
        }
    }
    changes = diff_against_pack(SCOPE, proposed)
    assert [change.path for change in changes] == ["intake.questions[key=full_name].prompt"]


def test_a_proposal_survives_a_restart(packs: Path) -> None:
    """It is a file beside the packs, not something held in a process."""
    proposal = propose(
        scope=SCOPE,
        changes=[
            Change(path="intake.questions[key=full_name].prompt", to="Stored", citation=CITATION)
        ],
        source="agentic_research",
        proposed_at=datetime(2026, 8, 27, tzinfo=UTC),
    )
    reloaded = load_proposal(proposal.id)
    assert reloaded is not None
    assert reloaded.changes[0].to == "Stored"
    assert reloaded.changes[0].citation["url"] == CITATION["url"]
    assert [item.id for item in list_proposals(status=STATUS_PENDING)] == [proposal.id]
