"""Official Japanese form resolution, intake derivation, and rule-anchored filling.

The filling tests need the published PDFs, which are fetched into the template cache by
``torii-fetch-forms``; they skip cleanly when the cache is cold so the suite stays
offline-safe.
"""

from __future__ import annotations

import io
from pathlib import Path

import pypdf
import pytest

from torii_api.services.intake import parse_questions
from torii_api.services.jp_form_layouts import LAYOUTS
from torii_api.services.jp_official_forms import (
    CONSULAR_VISA_FORM,
    QUESTION_SPECS,
    already_asked,
    forms_for_scope,
    intake_questions_for_scope,
    merge_form_questions,
    primary_form_for_scope,
)
from torii_api.services.official_form_filler import (
    classify_pages,
    fill_flat_form,
    missing_answer_keys,
    resolve_answer,
)
from torii_api.services.official_form_store import cache_dir, discover_pdf_url
from torii_api.services.pack_exports import pack_questions
from torii_api.services.pdf_geometry import fit_layout, page_rows

ANSWERS: dict[str, object] = {
    "nationality": "BANGLADESH",
    "date_of_birth": "1994-07-19",
    "full_name": "Md Hojayfa Rahman",
    "sex": "male",
    "place_of_birth": "Dhaka, Bangladesh",
    "marital_status": "single",
    "occupation": "Software Engineer",
    "home_town_city": "Mirpur, Dhaka",
    "current_japan_address": "2-14-5 Nishi-Shinjuku, Shinjuku-ku, Tokyo",
    "telephone_japan": "03-6812-4471",
    "mobile_phone": "080-4471-2299",
    "passport_number": "A05421997",
    "passport_expiry_date": "2031-02-28",
    "current_status_of_residence": "Engineer / Specialist in Humanities",
    "current_period_of_stay": "1 year",
    "current_status_expiry_date": "2026-11-30",
    "residence_card_number": "AB12345678CD",
    "desired_period_of_stay": "3 years",
    "desired_status_of_residence": "Highly Skilled Professional",
    "reason_for_extension": "Continued employment with the same employer",
    "change_reason": "Promotion into a qualifying role",
    "pr_reason": "Ten years of continuous residence",
    "criminal_record": False,
    "has_family_in_japan": False,
    "previous_japan_visits": True,
    "prior_coe_applications": False,
    "prior_deportation": False,
    "has_accompanying_persons": False,
    "intended_entry_date": "2026-10-01",
    "port_of_entry": "Tokyo Narita (NRT)",
    "intended_length_of_stay": "3 years",
    "intended_visa_application_place": "Embassy of Japan in Dhaka",
    # Applicant part 2 (申請人等作成用 ２), the sheet behind page 1.
    "employer_name": "AUREV Japan K.K.",
    "employer_branch_name": "Shinjuku Office",
    "employer_address": "2-14-5 Nishi-Shinjuku, Shinjuku-ku, Tokyo 160-0023",
    "employer_tel": "03-6812-4400",
    "final_school_name": "Bangladesh University of Engineering and Technology",
    "graduation_date": "2017-03-15",
    "has_it_qualification": True,
    "it_qualification_name": "Applied Information Technology Engineer (AP)",
    "has_legal_representative": False,
    # Applicant parts 2 and 3, form P (Student).
    "school_name": "Tokyo Japanese Language School",
    "school_address": "1-2-3 Shinjuku, Tokyo",
    "school_tel": "03-1111-2222",
    "total_years_of_education": 16,
    "japanese_test_name": "JLPT",
    "japanese_test_score": "N2",
    "japanese_school_name": "ABC Japanese Academy",
    "japanese_study_from": "2023-04-01",
    "japanese_study_to": "2025-03-31",
    "support_self_monthly_jpy": 40000,
    "support_overseas_supporter_monthly_jpy": 80000,
    "support_japan_supporter_monthly_jpy": 30000,
    "scholarship_monthly_jpy": 20000,
    "funds_carried_jpy": 300000,
    "funds_remitted_jpy": 500000,
    "supporter_name": "Abdul Rahman",
    "supporter_address": "Mirpur, Dhaka, Bangladesh",
    "supporter_tel": "+880-2-1111",
    "supporter_occupation": "Business owner",
    "supporter_employer_tel": "+880-2-2222",
    "supporter_annual_income_jpy": 3500000,
    "works_outside_status": True,
    "part_time_work_type": "Convenience store clerk",
    "part_time_employer_name": "Seven-Eleven Shinjuku",
    "part_time_employer_tel": "03-5555-6666",
    "part_time_weekly_hours": 28,
    "part_time_salary_jpy": 112000,
    "guardian_name": "Yuki Tanaka",
    "guardian_relationship": "Host parent",
    "guardian_address": "4-5-6 Nakano, Tokyo",
    "guardian_tel": "03-7777-8888",
    "guardian_mobile": "090-1111-2222",
    "funds_carrier_name": "Abdul Rahman",
    "funds_carry_date": "2026-09-15",
    "funds_other_jpy": 0,
    "support_other_monthly_jpy": 0,
    # Applicant parts 2 and 3, form T (Spouse / Long-term resident).
    "annual_income_jpy": 6200000,
    "support_guarantor_monthly_jpy": 0,
    "supporter_date_of_birth": "1985-04-20",
    "supporter_nationality": "JAPAN",
    "supporter_residence_card_number": "AB98765432CD",
    "supporter_status_of_residence": "Permanent Resident",
    "supporter_period_of_stay": "Indefinite",
    "supporter_status_expiry_date": "2030-04-20",
    "supporter_employer_name": "Tokyo Board of Education",
    "supporter_employer_branch": "Shinjuku Office",
    "supporter_employer_address": "1-1-1 Nishi-Shinjuku, Tokyo",
    "resident_guarantor_name": "Kenji Sato",
    "guarantor_occupation": "Company employee",
    "guarantor_address": "3-2-1 Roppongi, Minato-ku, Tokyo",
    "guarantor_telephone": "03-3333-4444",
    "guarantor_mobile": "090-5555-6666",
    "legal_representative_mobile": "090-0000-0000",
    # Applicant part 2, form R (Dependent).
    "family_notification_place_japan": "Shinjuku Ward Office, Tokyo",
    "family_notification_date_japan": "2023-06-12",
    "family_notification_place_home": "Dhaka City Corporation",
    "family_notification_date_home": "2023-05-02",
    "part_time_employer_branch": "Nakano Branch",
}


def _cached(form_code: str) -> bytes | None:
    path = cache_dir() / f"{form_code}.pdf"
    if not path.is_file():
        return None
    return path.read_bytes()


# ── Catalogue ──────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("category", "action", "expected_code", "expected_procedure"),
    [
        ("work", "renewal", "jp_work_extension", "extension"),
        ("work", "change_of_status", "jp_work_change_of_status", "change_of_status"),
        ("work", "new_application", "jp_work_coe", "coe"),
        ("student", "renewal", "jp_student_extension", "extension"),
        ("student", "new_application", "jp_student_coe", "coe"),
        ("dependent", "new_application", "jp_dependent_coe", "coe"),
        ("spouse", "new_application", "jp_spouse_coe", "coe"),
        ("hsp", "change_of_status", "jp_hsp_change_of_status", "change_of_status"),
        ("permanent_resident", "new_application", "jp_permanent_residence", "permanent_residence"),
        ("tourist", "new_application", "jp_consular_visa", "consular_visa"),
    ],
)
def test_each_application_type_resolves_its_own_form(
    category: str, action: str, expected_code: str, expected_procedure: str
) -> None:
    form = primary_form_for_scope(category, action)
    assert form is not None
    assert form.code == expected_code
    assert form.procedure == expected_procedure


def test_categories_do_not_share_a_form_pdf() -> None:
    """The whole point: Student and Engineer file different sheets for the same procedure."""
    urls = {
        category: primary_form_for_scope(category, "renewal").pdf_url  # type: ignore[union-attr]
        for category in ("work", "student", "dependent", "spouse", "hsp")
    }
    assert len(set(urls.values())) == len(urls), urls


def test_filing_from_abroad_includes_both_the_certificate_and_the_consular_visa() -> None:
    forms = forms_for_scope("work", "new_application")
    assert [form.code for form in forms] == ["jp_work_coe", "jp_consular_visa"]


def test_new_action_alias_resolves_like_new_application() -> None:
    assert primary_form_for_scope("work", "new") == primary_form_for_scope(
        "work", "new_application"
    )


def test_certificate_of_eligibility_ticks_the_category_purpose_box() -> None:
    boxes = {
        category: primary_form_for_scope(category, "new_application").purpose_checkbox  # type: ignore[union-attr]
        for category in ("work", "student", "dependent", "spouse", "hsp")
    }
    assert all(box is not None for box in boxes.values())
    assert len({(box.x0, box.y) for box in boxes.values() if box}) == len(boxes)


def test_every_form_carries_an_http_citation() -> None:
    """NF-2: nothing is published without an official source."""
    for category in ("work", "student", "dependent", "spouse", "hsp", "permanent_resident"):
        for action in ("new_application", "change_of_status", "renewal"):
            for form in forms_for_scope(category, action):
                assert form.citation["url"].startswith("http")
                assert form.citation["authority"]


def test_unsupported_scopes_resolve_to_no_form_rather_than_a_wrong_one() -> None:
    assert forms_for_scope("tourist", "renewal") == ()
    assert forms_for_scope("nonexistent_category", "renewal") == ()


# ── Intake derived from the forms ──────────────────────────────────────────────────


def test_every_form_field_has_an_intake_question() -> None:
    for layout in LAYOUTS.values():
        for key in layout.keys:
            assert key in QUESTION_SPECS, f"{layout.code} field '{key}' has no intake question"
    for _item_label, key in CONSULAR_VISA_FORM.acroform_items:
        assert key in QUESTION_SPECS, f"consular form field '{key}' has no intake question"


def test_derived_questions_parse_as_intake_questions() -> None:
    questions = intake_questions_for_scope("work", "new_application")
    assert questions
    parsed = parse_questions(questions, jurisdiction_code="JP", visa_category="work")
    assert {question.key for question in parsed} == {q["key"] for q in questions}


def test_derived_questions_cite_the_form_item_they_come_from() -> None:
    questions = {q["key"]: q for q in intake_questions_for_scope("work", "renewal")}
    citation = questions["residence_card_number"]["citation"]
    assert "在留期間更新許可申請書" in citation["title"]
    assert "item 12" in citation["title"]
    assert citation["url"].startswith("https://www.moj.go.jp/")


def test_merge_keeps_pack_questions_and_adds_only_what_the_form_still_needs() -> None:
    pack = [
        {
            "key": "full_name",
            "prompt": "Pack wording wins",
            "type": "string",
            "required": True,
            "citation": {"authority": "a", "title": "t", "url": "https://example.gov"},
        }
    ]
    merged = merge_form_questions(pack, "work", "renewal")
    assert merged[0] is pack[0]
    keys = [question["key"] for question in merged]
    assert keys.count("full_name") == 1
    assert "residence_card_number" in keys


def test_derived_questions_never_block_intake_completion() -> None:
    """A case already in flight must not be gated by newly derived questions."""
    for question in intake_questions_for_scope("work", "renewal"):
        assert question["required"] is False


def test_merge_leaves_non_japanese_scopes_alone() -> None:
    pack = [{"key": "full_name", "prompt": "p", "type": "string"}]
    assert merge_form_questions(pack, "b1b2", "new_application") == pack


# ── Merging into a scope's own intake ──────────────────────────────────────────────
# Each check below is a defect the first version of the merge shipped: it asked for the
# same fact twice under two names, headed the additions "Official form — …", and split
# one topic across three separate blocks.


@pytest.mark.parametrize(
    ("pack_key", "form_key"),
    [
        ("passport_expiry", "passport_expiry_date"),
        ("registered_address_japan", "current_japan_address"),
        ("criminal_disclosures", "criminal_record"),
        ("residence_card_expiry", "current_status_expiry_date"),
        ("intended_length_of_stay_days", "intended_length_of_stay"),
    ],
)
def test_a_fact_the_pack_already_asks_is_not_asked_again(pack_key: str, form_key: str) -> None:
    assert already_asked(form_key, {pack_key}) is True
    assert already_asked(form_key, set()) is False


def test_aliases_do_not_collapse_two_genuinely_different_questions() -> None:
    """Both phone fields can fall back to `phone_number`; they are still two boxes."""
    assert already_asked("mobile_phone", {"telephone_japan"}) is False
    assert already_asked("telephone_japan", {"mobile_phone"}) is False


def test_the_real_work_renewal_intake_has_no_duplicated_facts() -> None:
    merged = merge_form_questions(pack_questions("jp/work.renewal"), "work", "renewal")
    keys = [question["key"] for question in merged]
    assert len(keys) == len(set(keys))
    for pack_key, form_key in (
        ("passport_expiry", "passport_expiry_date"),
        ("registered_address_japan", "current_japan_address"),
        ("criminal_disclosures", "criminal_record"),
        ("residence_card_expiry", "current_status_expiry_date"),
    ):
        assert pack_key in keys
        assert form_key not in keys, f"{form_key} duplicates {pack_key}"


def test_no_section_advertises_itself_as_the_official_form() -> None:
    """The heading is what the applicant reads; every question is for the form."""
    for category, action in (("work", "renewal"), ("tourist", "new_application")):
        scope = f"jp/{category}.{'renewal' if action == 'renewal' else 'new_application'}"
        merged = merge_form_questions(pack_questions(scope), category, action)
        for question in merged:
            assert "Official form" not in str(question.get("section") or "")


def test_derived_questions_fold_into_the_packs_own_sections() -> None:
    merged = merge_form_questions(pack_questions("jp/work.renewal"), "work", "renewal")
    sections = {question["key"]: question["section"] for question in merged}
    assert sections["sex"] == "Personal & Identity"
    assert sections["current_status_of_residence"] == "Residence Card & Status"
    assert sections["has_family_in_japan"] == "Travel & Disclosures"


def test_a_group_with_no_matching_pack_section_keeps_a_plain_title() -> None:
    merged = merge_form_questions(pack_questions("jp/work.renewal"), "work", "renewal")
    sections = {question["key"]: question["section"] for question in merged}
    assert sections["telephone_japan"] == "Address & contact"
    assert sections["reason_for_extension"] == "What you are applying for"


def test_pack_questions_keep_their_exact_order() -> None:
    """Reordering one ahead of a question its show_when depends on would prune the answer."""
    pack = pack_questions("jp/work.renewal")
    merged = merge_form_questions(pack, "work", "renewal")
    pack_keys = [question["key"] for question in pack]
    merged_pack_keys = [q["key"] for q in merged if q["key"] in set(pack_keys)]
    assert merged_pack_keys == pack_keys


def test_each_section_appears_once_so_a_topic_is_not_split() -> None:
    """ "Official form — Identity" used to appear three times in this one flow."""
    merged = merge_form_questions(
        pack_questions("jp/tourist.new_application"), "tourist", "new_application"
    )
    runs = []
    for question in merged:
        section = question["section"]
        if not runs or runs[-1] != section:
            runs.append(section)
    assert len(runs) == len(set(runs)), f"a section is split across the flow: {runs}"


def test_derived_questions_say_which_box_they_fill() -> None:
    merged = merge_form_questions(pack_questions("jp/work.renewal"), "work", "renewal")
    hints = {q["key"]: q.get("hint") for q in merged}
    assert hints["sex"]
    assert "在留期間更新許可申請書" in hints["current_period_of_stay"]
    assert "prints empty" in hints["current_period_of_stay"]
    # A pack-authored question is untouched and carries no hint.
    assert hints["full_name"] is None


def test_a_follow_up_only_appears_after_an_affirmative_disclosure() -> None:
    """ "If you answered yes above" used to be asked even after a "no"."""
    from torii_api.services.intake import visible_questions

    merged = merge_form_questions(pack_questions("jp/work.renewal"), "work", "renewal")
    detail = next(q for q in merged if q["key"] == "criminal_record_detail")
    # It points at the key this pack actually uses, not the form's name for it.
    assert detail["show_when"] == {"key": "criminal_disclosures", "equals": True}
    assert "_depends_on" not in detail

    parsed = parse_questions(merged, jurisdiction_code="JP", visa_category="work")
    hidden = {q.key for q in visible_questions(parsed, {"criminal_disclosures": False})}
    shown = {q.key for q in visible_questions(parsed, {"criminal_disclosures": True})}
    assert "criminal_record_detail" not in hidden
    assert "criminal_record_detail" in shown


def test_hint_survives_question_parsing() -> None:
    merged = merge_form_questions(pack_questions("jp/work.renewal"), "work", "renewal")
    parsed = {
        q.key: q for q in parse_questions(merged, jurisdiction_code="JP", visa_category="work")
    }
    assert parsed["sex"].hint
    assert parsed["full_name"].hint is None


# ── Answer resolution ──────────────────────────────────────────────────────────────


def test_answers_fall_back_to_the_aliases_the_packs_already_use() -> None:
    assert resolve_answer("nationality", {"visitor_nationality": "BD"}) == "BD"
    assert resolve_answer("passport_expiry_date", {"passport_expiry": "2031-01-01"}) == "2031-01-01"
    assert resolve_answer("intended_entry_date", {"planned_arrival_date": "2026-10-01"}) == (
        "2026-10-01"
    )
    assert resolve_answer("nationality", {}) is None


def test_conditional_detail_lines_are_not_reported_missing_when_not_applicable() -> None:
    layout = LAYOUTS["moj_extension_applicant_p1"]
    assert "criminal_record_detail" not in missing_answer_keys(layout, {"criminal_record": False})
    assert "criminal_record_detail" in missing_answer_keys(layout, {"criminal_record": True})


# ── Geometry and filling ───────────────────────────────────────────────────────────


def test_discover_pdf_url_picks_the_link_under_the_procedure_heading() -> None:
    html = (
        '<h2>在留資格変更許可申請</h2><a href="/isa/content/930004064.pdf">PDF</a>'
        '<h2>在留期間更新許可申請</h2><a href="/isa/content/930004094.pdf">PDF</a>'
    )
    assert discover_pdf_url(html, "change_of_status") == (
        "https://www.moj.go.jp/isa/content/930004064.pdf"
    )
    assert discover_pdf_url(html, "extension") == (
        "https://www.moj.go.jp/isa/content/930004094.pdf"
    )


def test_layout_is_rejected_when_the_page_does_not_have_the_authored_shape() -> None:
    """A revised form must fail the fit rather than be written into blind coordinates."""
    layout = LAYOUTS["moj_extension_applicant_p1"]
    assert fit_layout([], layout.rows) is None
    assert fit_layout(list(_blank_page_rows()), layout.rows) is None


def _blank_page_rows() -> list:
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=595, height=842)
    buffer = io.BytesIO()
    writer.write(buffer)
    reader = pypdf.PdfReader(io.BytesIO(buffer.getvalue()))
    return page_rows(reader.pages[0], reader)


def test_filling_an_unfamiliar_pdf_returns_the_blank_form_untouched() -> None:
    form = primary_form_for_scope("work", "renewal")
    assert form is not None
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=595, height=842)
    buffer = io.BytesIO()
    writer.write(buffer)
    blank = buffer.getvalue()

    result = fill_flat_form(form, blank, ANSWERS)
    assert result.layout_verified is False
    assert result.content == blank
    assert result.filled == {}
    assert result.notes


@pytest.mark.parametrize(
    "form_code",
    [
        "jp_work_extension",
        "jp_work_change_of_status",
        "jp_work_coe",
        "jp_student_extension",
        "jp_student_coe",
        "jp_dependent_coe",
        "jp_spouse_coe",
        "jp_hsp_change_of_status",
        "jp_permanent_residence",
    ],
)
def test_published_forms_fill_completely(form_code: str) -> None:
    template = _cached(form_code)
    if template is None:
        pytest.skip(f"{form_code} not cached — run torii-fetch-forms")
    form = next(
        item
        for category in ("work", "student", "dependent", "spouse", "hsp", "permanent_resident")
        for action in ("new_application", "change_of_status", "renewal")
        for item in forms_for_scope(category, action)
        if item.code == form_code
    )
    result = fill_flat_form(form, template, ANSWERS)
    assert result.layout_verified is True
    assert result.missing == []
    assert len(result.filled) >= 19
    assert result.content != template
    # The applicant's answers are now page content, readable by any viewer.
    text = pypdf.PdfReader(io.BytesIO(result.content)).pages[0].extract_text()
    assert "A05421997" in text
    assert "RAHMAN" in text


# ── What the packet actually contains ──────────────────────────────────────────────
# A ministry form is several forms stapled together. Only the first applicant sheet is
# filled, and the note printed alongside it used to claim the rest belonged to the
# employer — when the applicant's own parts 2 and 3 are in there too.


@pytest.mark.parametrize(
    ("form_code", "expected_applicant_pages"),
    [
        ("jp_work_extension", [1, 3]),
        ("jp_student_extension", [1, 3, 4]),
        ("jp_spouse_coe", [1, 3, 4]),
        ("jp_dependent_coe", [1, 3]),
        # Headed 様式その１ / その２ — it never says 申請人等作成用 at all.
        ("jp_permanent_residence", [1, 2]),
    ],
)
def test_the_applicants_own_pages_are_identified(
    form_code: str, expected_applicant_pages: list[int]
) -> None:
    template = _cached(form_code)
    if template is None:
        pytest.skip(f"{form_code} not cached — run torii-fetch-forms")
    reader = pypdf.PdfReader(io.BytesIO(template))
    labels = classify_pages(reader)
    applicant = [number for number, label in enumerate(labels, 1) if label == "applicant"]
    assert applicant == expected_applicant_pages


def test_the_selector_sheet_is_not_mistaken_for_a_page_to_fill() -> None:
    """It lists the applicant parts by name, so a naive check counts it as one."""
    template = _cached("jp_work_extension")
    if template is None:
        pytest.skip("jp_work_extension not cached — run torii-fetch-forms")
    labels = classify_pages(pypdf.PdfReader(io.BytesIO(template)))
    assert labels[1] == "guide"


def test_the_note_never_claims_the_applicants_pages_belong_to_the_employer() -> None:
    template = _cached("jp_student_extension")
    if template is None:
        pytest.skip("jp_student_extension not cached — run torii-fetch-forms")
    form = primary_form_for_scope("student", "renewal")
    assert form is not None
    result = fill_flat_form(form, template, ANSWERS)

    assert result.applicant_pages == [1, 3, 4]
    combined = " ".join(result.notes)
    assert "Pages 5 and 6 are the organisation part" in combined
    # An applicant's own sheet must never be described as the organisation's.
    for page in result.applicant_pages:
        assert f"Page {page} is the organisation part" not in combined


def test_the_work_packet_fills_both_of_its_applicant_sheets() -> None:
    """Page 1 is shared across statuses; page 3 (申請人等作成用 ２ / N) is work-specific."""
    template = _cached("jp_work_extension")
    if template is None:
        pytest.skip("jp_work_extension not cached — run torii-fetch-forms")
    form = primary_form_for_scope("work", "renewal")
    assert form is not None
    assert [sheet.page for sheet in form.extra_layouts] == [2]

    result = fill_flat_form(form, template, ANSWERS)
    assert result.applicant_pages == [1, 3]
    assert result.filled_pages == [1, 3]
    assert result.summary["unfilled_applicant_pages"] == []

    text = pypdf.PdfReader(io.BytesIO(result.content)).pages[2].extract_text()
    assert "AUREV Japan K.K." in text
    assert "Shinjuku Office" in text
    assert "Applied Information Technology Engineer" in text

    # The tick-box matrices and the work-history grid are not authored, and the applicant
    # is told so rather than left to find the gap at the counter.
    combined = " ".join(result.notes)
    assert "19 Major field of study" in combined
    assert "21 Work experience" in combined


def test_extension_and_change_share_the_work_part_two_sheet() -> None:
    extension = primary_form_for_scope("work", "renewal")
    change = primary_form_for_scope("work", "change_of_status")
    assert extension is not None and change is not None
    assert extension.extra_layouts == change.extra_layouts


def test_a_status_without_an_authored_part_two_still_fills_page_one() -> None:
    """Adding later-sheet support for one status must not regress the others."""
    candidate = next(
        (
            (category, action)
            for category in ("dependent", "spouse", "hsp", "designated_activities")
            for action in ("renewal", "change_of_status", "new_application")
            if (form := primary_form_for_scope(category, action)) is not None
            and form.layout is not None
            and not form.extra_layouts
        ),
        None,
    )
    if candidate is None:
        pytest.skip("every status now has its later sheets authored")
    form = primary_form_for_scope(*candidate)
    assert form is not None
    template = _cached(form.code)
    if template is None:
        pytest.skip(f"{form.code} not cached — run torii-fetch-forms")
    result = fill_flat_form(form, template, ANSWERS)
    assert result.filled_pages == [1]
    assert result.summary["unfilled_applicant_pages"]


def test_a_part_two_item_only_prints_when_it_applies() -> None:
    """Item 22 is for a legal representative's filing; most applicants leave it blank."""
    template = _cached("jp_work_extension")
    if template is None:
        pytest.skip("jp_work_extension not cached — run torii-fetch-forms")
    form = primary_form_for_scope("work", "renewal")
    assert form is not None
    result = fill_flat_form(form, template, {**ANSWERS, "has_legal_representative": False})
    assert not [item for item in result.missing if item.startswith("22")]


def test_page_counts_read_the_document_rather_than_the_catalogue() -> None:
    """A revised packet that gains or loses a sheet must not desync the note."""
    template = _cached("jp_work_extension")
    if template is None:
        pytest.skip("jp_work_extension not cached — run torii-fetch-forms")
    labels = classify_pages(pypdf.PdfReader(io.BytesIO(template)))
    assert len(labels) == len(pypdf.PdfReader(io.BytesIO(template)).pages)


def test_a_student_variant_fills_despite_being_published_at_a_different_scale() -> None:
    """The ministry ships per-status variants at slightly different scales."""
    template = _cached("jp_student_extension")
    if template is None:
        pytest.skip("jp_student_extension not cached — run torii-fetch-forms")
    form = primary_form_for_scope("student", "renewal")
    assert form is not None
    reader = pypdf.PdfReader(io.BytesIO(template))
    fit = fit_layout(page_rows(reader.pages[0], reader), form.layout.rows)  # type: ignore[union-attr]
    assert fit is not None
    assert fit.x_scale != pytest.approx(1.0, abs=1e-4)
    assert fill_flat_form(form, template, ANSWERS).layout_verified is True


def test_cached_templates_still_match_the_revision_the_layout_was_verified_against() -> None:
    """Fails when the ministry revises a form — the signal to re-verify its layout."""
    import hashlib

    stale: list[str] = []
    checked = 0
    for category in ("work", "student", "dependent", "spouse", "hsp", "permanent_resident"):
        for action in ("new_application", "change_of_status", "renewal"):
            for form in forms_for_scope(category, action):
                if form.sha256 is None:
                    continue
                template = _cached(form.code)
                if template is None:
                    continue
                checked += 1
                if hashlib.sha256(template).hexdigest() != form.sha256:
                    stale.append(form.code)
    if not checked:
        pytest.skip("no cached templates — run torii-fetch-forms")
    assert stale == []


def test_cache_directory_is_configurable(monkeypatch: pytest.MonkeyPatch) -> None:
    from torii_api.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setenv("TORII_OFFICIAL_FORM_DIR", str(Path("/tmp/torii-forms")))
    try:
        assert cache_dir() == Path("/tmp/torii-forms")
    finally:
        monkeypatch.delenv("TORII_OFFICIAL_FORM_DIR", raising=False)
        get_settings.cache_clear()


# ── Question volume ────────────────────────────────────────────────────────────────
# Intake asked every question of every applicant regardless of whether it applied: a
# spouse applicant saw 74 questions before answering anything, of which 7 were required.


def _shown(scope: str, category: str, action: str, answers: dict | None = None):
    merged = merge_form_questions(pack_questions(scope), category, action)
    parsed = parse_questions(merged, jurisdiction_code="JP", visa_category=category)
    from torii_api.services.intake import visible_questions

    return visible_questions(parsed, answers or {})


@pytest.mark.parametrize(
    ("scope", "category", "action", "ceiling"),
    [
        ("jp/work.renewal", "work", "renewal", 36),
        ("jp/student.renewal", "student", "renewal", 48),
        ("jp/spouse.new_application", "spouse", "new_application", 42),
        ("jp/tourist.new_application", "tourist", "new_application", 38),
    ],
)
def test_a_new_applicant_is_not_shown_an_exhausting_questionnaire(
    scope: str, category: str, action: str, ceiling: int
) -> None:
    assert len(_shown(scope, category, action)) <= ceiling


def test_filing_from_abroad_does_not_ask_for_the_visa_stage_upfront() -> None:
    """The consular form is filed months later, once the certificate has been issued."""
    shown = {
        question.key
        for question in _shown("jp/spouse.new_application", "spouse", "new_application")
    }
    # Items that exist only on the consular form are not asked at the certificate stage.
    # (port_of_entry is item 13 of the certificate itself, so it legitimately is.)
    assert "airline_flight_no" not in shown
    assert "passport_issuing_authority" not in shown
    assert "inviter_name" not in shown
    # But the whole set is still available where a caller genuinely wants it.
    every = {
        q["key"] for q in intake_questions_for_scope("spouse", "new_application", all_stages=True)
    }
    assert "airline_flight_no" in every


@pytest.mark.parametrize(
    ("gate", "gated_key"),
    [
        ("is_employed", "employer_name"),
        ("has_financial_support", "supporter_name"),
        ("has_guarantor_in_japan", "resident_guarantor_name"),
        ("carries_cash_into_japan", "funds_carried_jpy"),
    ],
)
def test_a_conditional_block_is_asked_only_once_it_applies(gate: str, gated_key: str) -> None:
    scope, category, action = "jp/spouse.new_application", "spouse", "new_application"
    if gated_key == "resident_guarantor_name":
        # This block sits on the part-3 sheet, which the extension packet carries.
        scope, action = "jp/spouse.new_application", "renewal"
    before = {q.key for q in _shown(scope, category, action)}
    after = {q.key for q in _shown(scope, category, action, {gate: True})}
    assert gate in before, f"the gate {gate!r} itself must be asked"
    assert gated_key not in before
    assert gated_key in after


def test_every_gate_a_question_depends_on_is_itself_asked() -> None:
    """A gate nobody is asked leaves its block permanently hidden and its box blank."""
    for scope, category, action in (
        ("jp/work.renewal", "work", "renewal"),
        ("jp/student.renewal", "student", "renewal"),
        ("jp/spouse.new_application", "spouse", "new_application"),
        ("jp/tourist.new_application", "tourist", "new_application"),
    ):
        merged = merge_form_questions(pack_questions(scope), category, action)
        keys = {question["key"] for question in merged}
        for question in merged:
            gate = (question.get("show_when") or {}).get("key")
            if gate:
                assert gate in keys, f"{scope}: {question['key']} is gated on unasked {gate!r}"


# ── Questions are ops-editable content, not code ───────────────────────────────────


def test_questions_come_from_versioned_yaml_not_python() -> None:
    """Wording, sections and gating change often; nobody should edit Python to do it."""
    from torii_api.services.content_packs import resolve_packs_dir

    path = resolve_packs_dir() / "jp" / "_form_questions.yml"
    assert path.is_file(), "the intake questions must live in an ops-editable pack file"

    import yaml

    entries = (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("questions") or {}
    assert len(entries) == len(QUESTION_SPECS)
    assert entries["sex"]["prompt"] == QUESTION_SPECS["sex"].prompt


def test_every_authored_question_is_well_formed() -> None:
    for key, spec in QUESTION_SPECS.items():
        assert spec.prompt.strip(), f"{key} has no prompt"
        assert spec.type in ("boolean", "string", "integer", "enum", "date"), key
        assert spec.section.strip(), f"{key} has no section"
        if spec.type == "enum":
            assert spec.options, f"enum question {key} has no options"
        if spec.show_when:
            assert spec.show_when[0] in QUESTION_SPECS, (
                f"{key} gated on unknown {spec.show_when[0]}"
            )
