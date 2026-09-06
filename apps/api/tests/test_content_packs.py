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
    rule = next(r for r in pack.rules if r["key"] == "nationality")
    assert rule["operator"] == "nationality_in"
    assert "US" in rule["value"]
    assert "BD" not in rule["value"]


def test_tourist_nationality_rule_evaluates_against_the_answer_intake_collects() -> None:
    """The rule has to key on the question intake actually asks.

    It keyed on ``visitor_nationality``, which no question defines, so the evaluator
    could not resolve an answer for it and returned ``out_of_scope`` -- which outranks
    ``at_risk`` -- on every Japanese tourist case, waiver country or not.
    """
    from torii_api.services.eligibility import evaluate_eligibility
    from torii_api.services.jp_official_forms import merge_form_questions

    pack = load_pack_by_scope("jp/tourist.new_application")
    # What the applicant is actually asked is the pack's own questions plus the items the
    # consular form adds, which is where the graded declarations come from.
    asked = {q["key"] for q in merge_form_questions(pack.questions, "tourist", "new_application")}
    for rule in pack.rules:
        assert rule["key"] in asked, f"rule '{rule['key']}' keys on a question nobody is asked"

    answers = {
        "nationality": "BD",
        "intended_length_of_stay_days": 14,
        "criminal_record": False,
        "prior_deportation": False,
    }
    result = evaluate_eligibility(answers, pack.rules)
    assert result.result == "at_risk"
    nationality = next(f for f in result.findings if f.key == "nationality")
    assert nationality.status == "at_risk"

    # A visa-waiver passport clears the same rule instead of stalling on it.
    waiver = evaluate_eligibility({**answers, "nationality": "US"}, pack.rules)
    assert waiver.result == "pass"


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

    three = {
        item.code
        for item in visible_requirement_items(_coe_documents(), {"employer_category": "category_3"})
    }
    four = {
        item.code
        for item in visible_requirement_items(_coe_documents(), {"employer_category": "category_4"})
    }
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
    """Gating on an answer nobody is asked for makes those documents unreachable.

    Checked across every Japanese pack rather than the one that first needed it: a gate
    keyed on a question the pack does not ask hides those documents from every applicant,
    and it does so silently.
    """
    import yaml

    for path in sorted((PACKS / "jp").glob("*.yml")):
        if path.name.startswith("_"):
            continue
        pack = yaml.safe_load(path.read_text(encoding="utf-8"))
        asked = {q["key"] for q in (pack.get("intake") or {}).get("questions") or []}
        documents = pack.get("documents") or {}
        items = documents.get("items") or documents.get("requirements") or []
        gated_on = {
            str((item.get("show_when") or {}).get("key")) for item in items if item.get("show_when")
        }
        assert gated_on <= asked, f"{path.name}: gated on unasked answers: {gated_on - asked}"


def test_a_conviction_is_graded_the_way_article_5_grades_it() -> None:
    """Any conviction anywhere, ever, used to fail the case outright.

    Article 5(1) does not work that way: it turns on the sentence — one year or more,
    item (iv) — and on the offence — narcotics and stimulants, item (v), at any sentence.
    A fine for a traffic offence twenty years ago is a disclosure, not a bar.
    """
    from torii_api.services.eligibility import evaluate_eligibility

    rules = load_pack_by_scope("jp/tourist.new_application").rules
    base = {
        "nationality": "US",
        "intended_length_of_stay_days": 14,
        "criminal_record": False,
        "prior_deportation": False,
    }

    assert evaluate_eligibility(base, rules).result == "pass"

    disclosed = {
        **base,
        "criminal_record": True,
        "imprisoned_one_year_or_more": False,
        "drug_offence_conviction": False,
    }
    assert evaluate_eligibility(disclosed, rules).result == "at_risk"

    # The two statutory grounds do fail, and each on its own.
    assert (
        evaluate_eligibility({**disclosed, "imprisoned_one_year_or_more": True}, rules).result
        == "fail"
    )
    assert (
        evaluate_eligibility({**disclosed, "drug_offence_conviction": True}, rules).result == "fail"
    )

    # Neither is evaluated at all for an applicant with nothing to declare, so a clean
    # case is never stalled on a follow-up question it was right to skip.
    clean = evaluate_eligibility(base, rules)
    assert {finding.key for finding in clean.findings} == {
        "nationality",
        "intended_length_of_stay_days",
        "criminal_record",
        "prior_deportation",
    }

    # Removal bars landing for a period counted from the date, not for life, and the
    # pack does not collect that date — so it is a risk to check, not a decided failure.
    removed = evaluate_eligibility({**base, "prior_deportation": True}, rules)
    assert removed.result == "at_risk"


def test_a_short_stay_applicant_gathers_the_bundle_for_their_own_trip() -> None:
    """The tourist checklist was flat, so it demanded an employment certificate of students
    and never asked the inviting side of a family visit for anything at all."""
    from torii_api.services.checklist import visible_requirement_items
    from torii_api.services.pack_exports import pack_documents

    documents = pack_documents("jp/tourist.new_application")

    def codes(answers: dict) -> set[str]:
        return {item.code for item in visible_requirement_items(documents, answers)}

    tourist = codes(
        {
            "purpose_of_visit": "tourism",
            "trip_payer": "self_funded",
            "employment_status": "employed",
        }
    )
    visit = codes(
        {
            "purpose_of_visit": "visiting_family",
            "trip_payer": "guarantor_in_japan",
            "employment_status": "student",
        }
    )

    # Everyone files the application itself, whatever the trip is.
    always = {
        "passport_original",
        "visa_application_form",
        "schedule_of_stay",
        "flight_hotel_reservations",
    }
    assert always <= tourist and always <= visit

    # A self-funded tourist proves their own funds and their own job, and is asked for
    # nothing about an inviter they do not have.
    assert {"bank_solvency_certificate", "employment_certificate"} <= tourist
    assert not tourist & {"letter_of_invitation", "letter_of_guarantee", "relationship_evidence"}

    # A guaranteed family visit is the other way round: the Japanese side documents the
    # invitation and the money, and the student is not asked to certify employment.
    assert {
        "letter_of_invitation",
        "inviter_residence_certificate",
        "relationship_evidence",
        "letter_of_guarantee",
        "guarantor_income_evidence",
        "student_enrolment_certificate",
    } <= visit
    assert not visit & {"employment_certificate", "bank_solvency_certificate"}


def test_every_japanese_category_is_offered() -> None:
    """Short stay included: a Bangladeshi national filing from Dhaka is the founding case."""
    import yaml

    meta = yaml.safe_load((PACKS / "jp" / "_jurisdiction.yml").read_text(encoding="utf-8"))
    live = {c["code"] for c in meta["categories"] if c["is_live"]}
    assert {
        "work",
        "student",
        "dependent",
        "permanent_resident",
        "spouse",
        "hsp",
        "designated_activities",
        "tourist",
    } <= live


def test_the_change_of_status_scope_has_a_checklist_too() -> None:
    """It was live with an empty one, exactly as the certificate scope was."""
    import yaml

    items = yaml.safe_load(
        (PACKS / "jp" / "work.change_of_status.yml").read_text(encoding="utf-8")
    )["documents"]["items"]
    assert len(items) >= 10
    codes = {item["code"] for item in items}
    # What the ministry prints differently for somebody already in Japan.
    assert "passport_and_residence_card" in codes
    assert "return_envelope" not in codes, "the certificate is posted back; this is not"
    for item in items:
        assert str((item.get("citation") or {}).get("url", "")).startswith("http")


def test_the_two_work_scopes_share_the_employer_category_bundle() -> None:
    """They are the same requirement, so they must not drift apart."""
    import yaml

    def codes(scope: str) -> set[str]:
        items = yaml.safe_load((PACKS / "jp" / f"{scope}.yml").read_text(encoding="utf-8"))[
            "documents"
        ]["items"]
        return {item["code"] for item in items if item.get("show_when")}

    assert codes("work.new_application") == codes("work.change_of_status")


def test_the_short_stay_actions_with_no_form_are_parked() -> None:
    """A live scope that hands over nothing is worse than one that is not offered."""
    rows = {row["scope_id"] for row in workflow_rows_from_packs(load_all_packs())}
    assert "jp/tourist.new_application" in rows, "the BD->JP corridor this was built for"
    assert "jp/tourist.renewal" not in rows
    assert "jp/tourist.change_of_status" not in rows
