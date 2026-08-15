"""Tests for the per-stage agentic research resolution helpers (docs/plan/03_corridor_bd_jp.md)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from torii_api.db.models import CaseStageResearch, ScopeResearchStatus
from torii_api.services.agentic import (
    admissibility_is_valid,
    scope_key,
    stage_expiry,
    stage_is_usable,
    stage_is_valid,
    stage_items,
)

CITED = {"authority": "gov.uk", "title": "Standard Visitor", "url": "https://www.gov.uk/x"}


def test_scope_key_is_deterministic_and_case_insensitive() -> None:
    a = scope_key(
        destination_code="jp",
        purpose_code="Tourist",
        action_code="New_Application",
        nationality="bd",
        residence_country="bd",
    )
    b = scope_key(
        destination_code="JP",
        purpose_code="tourist",
        action_code="new_application",
        nationality="BD",
        residence_country="BD",
    )
    assert a == b == "JP|tourist|new_application|BD|BD"


def test_scope_key_differs_by_nationality() -> None:
    bd = scope_key(
        destination_code="JP",
        purpose_code="tourist",
        action_code="new_application",
        nationality="BD",
        residence_country="BD",
    )
    us = scope_key(
        destination_code="JP",
        purpose_code="tourist",
        action_code="new_application",
        nationality="US",
        residence_country="US",
    )
    assert bd != us


def test_stage_expiry_admissibility_longer_than_case_stage() -> None:
    admissibility = stage_expiry("admissibility")
    intake = stage_expiry("intake")
    assert admissibility > intake


def _research(
    *, status: str = ScopeResearchStatus.COMPLETED, expires_in_days: float | None = 1.0
) -> CaseStageResearch:
    research = CaseStageResearch(stage="intake", status=status)
    research.payload = {"questions": [{"key": "full_name"}]}
    if expires_in_days is None:
        research.expires_at = None
    else:
        research.expires_at = datetime.now(UTC) + timedelta(days=expires_in_days)
    return research


def test_stage_is_usable_true_for_completed_unexpired() -> None:
    assert stage_is_usable(_research()) is True


def test_stage_is_usable_false_for_none() -> None:
    assert stage_is_usable(None) is False


def test_stage_is_usable_false_for_not_completed() -> None:
    assert stage_is_usable(_research(status=ScopeResearchStatus.RUNNING)) is False


def test_stage_is_usable_false_for_expired() -> None:
    assert stage_is_usable(_research(expires_in_days=-1.0)) is False


def test_stage_is_usable_false_without_expiry() -> None:
    assert stage_is_usable(_research(expires_in_days=None)) is False


def test_stage_items_returns_list_slice_when_usable() -> None:
    research = _research()
    assert stage_items(research, "intake") == [{"key": "full_name"}]


def test_stage_items_empty_when_not_usable() -> None:
    research = _research(status=ScopeResearchStatus.FAILED)
    assert stage_items(research, "intake") == []


def test_stage_items_empty_for_none() -> None:
    assert stage_items(None, "intake") == []


def test_admissibility_is_valid_requires_at_least_one_cited_object() -> None:
    assert admissibility_is_valid({}) is False
    assert admissibility_is_valid({"admission": {}}) is False
    assert admissibility_is_valid({"admission": {"visa_required": True}}) is False
    assert admissibility_is_valid({"admission": {"visa_required": True, "citation": CITED}}) is True


def test_admissibility_is_valid_rejects_uncited_fee() -> None:
    payload = {"admission": {"visa_required": True, "citation": CITED}, "fees": [{"amount": 100}]}
    assert admissibility_is_valid(payload) is False


def test_admissibility_is_valid_accepts_cited_fee() -> None:
    payload = {
        "admission": {"visa_required": True, "citation": CITED},
        "fees": [{"amount": 100, "citation": CITED}],
    }
    assert admissibility_is_valid(payload) is True


def test_stage_is_valid_intake_requires_citations_and_parseable_questions() -> None:
    good = {
        "questions": [
            {"key": "full_name", "prompt": "Name?", "type": "string", "citation": CITED}
        ]
    }
    assert stage_is_valid("intake", good) is True

    uncited = {"questions": [{"key": "full_name", "prompt": "Name?", "type": "string"}]}
    assert stage_is_valid("intake", uncited) is False

    empty = {"questions": []}
    assert stage_is_valid("intake", empty) is False

    malformed = {"questions": [{"key": "x", "prompt": "?", "type": "enum", "citation": CITED}]}
    assert stage_is_valid("intake", malformed) is False  # enum with no options


def test_stage_is_valid_eligibility_requires_citation() -> None:
    good = {
        "rules": [
            {
                "key": "purpose",
                "operator": "equals",
                "value": "tourism",
                "failure_status": "fail",
                "message": "...",
                "citation": CITED,
            }
        ]
    }
    assert stage_is_valid("eligibility", good) is True
    assert stage_is_valid("eligibility", {"rules": []}) is False


def test_stage_is_valid_documents_requires_citation() -> None:
    good = {"documents": [{"code": "passport", "is_required": True, "citation": CITED}]}
    assert stage_is_valid("documents", good) is True
    bad = {"documents": [{"code": "passport", "is_required": True}]}
    assert stage_is_valid("documents", bad) is False


def test_stage_is_valid_forms_requires_field_mappings() -> None:
    good = {
        "forms": [
            {
                "code": "ds160",
                "citation": CITED,
                "field_mappings": [{"form_field": "a.b", "answer_key": "full_name"}],
            }
        ]
    }
    assert stage_is_valid("forms", good) is True

    no_mappings = {"forms": [{"code": "ds160", "citation": CITED, "field_mappings": []}]}
    assert stage_is_valid("forms", no_mappings) is False
