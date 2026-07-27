"""Unit tests for information-not-advice guardrails."""

from torii_ai.guardrails.policy import classify_user_message


def test_allows_procedural_question() -> None:
    result = classify_user_message("What documents are listed for a work visa renewal in Japan?")
    assert result.kind == "allow"


def test_refuses_advice_seeking() -> None:
    result = classify_user_message("Should I apply for a change of status or renewal?")
    assert result.kind == "refusal"
    assert result.message is not None
    lowered = result.message.lower()
    assert "legal advice" in lowered or "cannot give legal advice" in lowered


def test_refuses_empty() -> None:
    result = classify_user_message("   ")
    assert result.kind == "refusal"
