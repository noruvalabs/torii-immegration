"""Content pack loader and citation gate tests (M0 / NF-2)."""

from __future__ import annotations

from torii_api.services.content_packs import (
    load_all_packs,
    load_jurisdiction_meta,
    load_pack_by_scope,
    workflow_rows_from_packs,
)
from torii_api.services.intake import parse_questions
from torii_api.services.ops_ingest import validated_for_promote


def test_all_packs_load_and_parse() -> None:
    packs = load_all_packs()
    assert "jp/work.renewal" in packs
    assert "jp/student.new_application" in packs
    assert "jp/tourist.new_application" in packs
    assert "us/h1b.renewal" in packs
    assert "us/h1b.new_application" in packs
    assert "uk/tourist.new_application" in packs

    for pack in packs.values():
        parse_questions(pack.questions)
        assert pack.rules
        assert pack.document_items
        assert pack.forms
        assert pack.scope.jurisdiction
        assert pack.stages


def test_every_rule_document_fee_has_http_citation() -> None:
    for pack in load_all_packs().values():
        assert validated_for_promote(
            rules=pack.rules,
            documents=pack.document_items,
            questions=pack.questions,
        ), f"{pack.scope_id} failed promote validation"
        for form in pack.forms:
            url = form.citation.get("url")
            assert isinstance(url, str) and url.startswith("http"), pack.scope_id
        for fee in pack.fees:
            if fee.published:
                assert fee.citation is not None
                assert fee.citation.url.startswith("http")
                assert fee.amount is not None
            # unpublished fee placeholders may omit amount (NF-2: no guessed numbers)


def test_jp_work_renewal_matches_seed_shape() -> None:
    pack = load_pack_by_scope("jp/work.renewal")
    row = next(r for r in workflow_rows_from_packs() if r["scope_id"] == "jp/work.renewal")
    assert row["jurisdiction"] == "JP"
    assert row["visa_category"] == "work"
    assert row["action"] == "renewal"
    assert row["form"]["code"] == "extension_of_stay"
    assert any(q["key"] == "nationality" for q in pack.questions)
    assert any(q["key"] == "years_in_japan" for q in pack.questions)


def test_nationality_in_rules_on_tourist_pack() -> None:
    pack = load_pack_by_scope("jp/tourist.new_application")
    rule = next(r for r in pack.rules if r["key"] == "visitor_nationality")
    assert rule["operator"] == "nationality_in"
    assert "US" in rule["value"]
    assert "BD" not in rule["value"]


def test_jurisdiction_meta_from_packs() -> None:
    jp = load_jurisdiction_meta("jp")
    us = load_jurisdiction_meta("us")
    assert jp is not None and jp.code == "JP" and jp.is_live
    assert us is not None and us.code == "US"
    assert any(c["code"] == "h1b" for c in us.categories)


def test_uk_tourist_is_research_enabled_placeholder() -> None:
    pack = load_pack_by_scope("uk/tourist.new_application")
    assert pack.scope.jurisdiction == "UK"
    assert pack.scope.visa_category == "tourist"
    assert pack.scope.action == "new_application"
    assert pack.scope.research_enabled is True
    assert pack.scope.is_live is False
    # Research-driven scopes are not flattened into live workflow rows.
    row_ids = {r["scope_id"] for r in workflow_rows_from_packs()}
    assert "uk/tourist.new_application" not in row_ids


def test_uk_meta_flags_research_enabled() -> None:
    uk = load_jurisdiction_meta("uk")
    assert uk is not None and uk.code == "UK" and uk.is_live
    tourist = next(c for c in uk.categories if c["code"] == "tourist")
    assert tourist["is_live"] is False
    assert tourist["research_enabled"] is True
    new_action = next(a for a in uk.actions if a["code"] == "new")
    assert new_action["is_live"] is False
    assert new_action["research_enabled"] is True
