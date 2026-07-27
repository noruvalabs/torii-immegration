"""Unit tests for the citation engine."""

from datetime import UTC, datetime

from torii_ai.citations.engine import filter_instructions, sanitize_bubble
from torii_ai.citations.models import Citation, Instruction


def _cite() -> Citation:
    return Citation(
        authority="isa.go.jp",
        title="Extension",
        url="https://www.isa.go.jp/example",
        retrieved_at=datetime.now(UTC),
        source_version="2026-07",
    )


def test_filter_drops_empty_sources() -> None:
    good = Instruction(text="File the extension form.", sources=[_cite()])
    bad = Instruction(text="You must do X.", sources=[])
    assert filter_instructions([good, bad]) == [good]


def test_sanitize_drops_uncited_requirement() -> None:
    assert (
        sanitize_bubble(
            text="You must file form X.",
            instructions=[Instruction(text="File form X.", sources=[])],
            claims_requirement=True,
        )
        is None
    )


def test_sanitize_allows_conversation_without_instructions() -> None:
    result = sanitize_bubble(
        text="Want me to walk through the steps?",
        instructions=[],
        claims_requirement=False,
    )
    assert result == ("Want me to walk through the steps?", [])


def test_sanitize_keeps_sourced_requirement() -> None:
    instr = Instruction(text="File the extension form.", sources=[_cite()])
    result = sanitize_bubble(
        text="For renewal you file the extension form.",
        instructions=[instr],
        claims_requirement=True,
    )
    assert result is not None
    text, kept = result
    assert "extension" in text
    assert len(kept) == 1
