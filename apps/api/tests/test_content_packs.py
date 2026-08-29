"""Content pack loader and citation gate tests (M0 / NF-2)."""

from __future__ import annotations

import pytest

from torii_api.services.content_packs import (
    load_all_packs,
    load_jurisdiction_meta,
    load_pack_by_scope,
    resolve_packs_dir,
    workflow_rows_from_packs,
)
from torii_api.services.intake import parse_questions
from torii_api.services.ops_ingest import validated_for_promote

PACKS = resolve_packs_dir()


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
    work = next(c for c in uk.categories if c["code"] == "work")
    assert work["is_live"] is True
    student = next(c for c in uk.categories if c["code"] == "student")
    assert student["is_live"] is True
    cos_action = next(a for a in uk.actions if a["code"] == "change_of_status")
    assert cos_action["is_live"] is True


# ── The 技人国 certificate asks for a different bundle per employer category ────────
# The ministry publishes four categories and tells categories 1 and 2 in as many words
# that 「その他の資料は原則不要」. A flat list would send a listed company's new hire
# chasing a business plan and three months of tax receipts.


def _coe_documents() -> list[dict]:
    import yaml

    path = PACKS / "jp" / "work.new_application.yml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))["documents"]["items"]


def test_the_work_certificate_scope_has_a_checklist_at_all() -> None:
    """It was live with an empty one: it told the applicant to gather nothing."""
    assert len(_coe_documents()) >= 10


@pytest.mark.parametrize(
    ("category", "at_most", "at_least"),
    [
        ("category_1", 5, 3),
        ("category_2", 5, 3),
        ("category_3", 14, 10),
        ("category_4", 15, 11),
    ],
)
def test_a_smaller_employer_category_asks_for_more(
    category: str, at_most: int, at_least: int
) -> None:
    from torii_api.services.checklist import visible_requirement_items

    shown = visible_requirement_items(_coe_documents(), {"employer_category": category})
    assert at_least <= len(shown) <= at_most


def test_the_bundles_nest_the_way_the_ministry_describes_them() -> None:
    """Category 4 is category 3 plus the evidence that its withholding summary is absent."""
    from torii_api.services.checklist import visible_requirement_items

    three = {item.code for item in visible_requirement_items(
        _coe_documents(), {"employer_category": "category_3"}
    )}
    four = {item.code for item in visible_requirement_items(
        _coe_documents(), {"employer_category": "category_4"}
    )}
    # Everything substantive that category 3 gathers, category 4 gathers too.
    assert three - {"withholding_summary"} <= four
    assert "no_withholding_summary_reason" in four - three
    assert "withholding_summary" not in four


def test_every_certificate_document_cites_the_page_it_was_read_from() -> None:
    """NF-2: an applicant told to gather something can check who says so."""
    for item in _coe_documents():
        citation = item.get("citation") or {}
        assert str(citation.get("url", "")).startswith("http"), item["code"]
        assert citation.get("authority"), item["code"]


def test_the_category_question_is_asked_before_its_documents_are_gated_on_it() -> None:
    """Gating on an answer nobody is asked for makes those documents unreachable."""
    import yaml

    pack = yaml.safe_load(
        (PACKS / "jp" / "work.new_application.yml").read_text(encoding="utf-8")
    )
    asked = {q["key"] for q in pack["intake"]["questions"]}
    gated_on = {
        str((item.get("show_when") or {}).get("key"))
        for item in pack["documents"]["items"]
        if item.get("show_when")
    }
    assert gated_on <= asked, f"gated on unasked answers: {gated_on - asked}"


def test_tourist_is_parked_but_its_packs_are_still_there() -> None:
    """Turning a category off is a flag, not a deletion — it flips back in one line."""
    import yaml

    meta = yaml.safe_load((PACKS / "jp" / "_jurisdiction.yml").read_text(encoding="utf-8"))
    live = {c["code"] for c in meta["categories"] if c["is_live"]}
    assert "tourist" not in live
    assert {"work", "student", "dependent", "permanent_resident"} <= live
    # The content survives the flag, so nothing has to be rebuilt to turn it back on.
    assert (PACKS / "jp" / "tourist.new_application.yml").exists()
