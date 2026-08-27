"""Filing instructions and the cover letter are per application type, not per country.

An extension, a certificate of eligibility and a consular visa go to different offices,
are filed by different people, and cost different amounts. The previous implementation
string-sniffed a display label and gave every Japanese case one of two answers.
"""

from __future__ import annotations

import io
from datetime import date

import pypdf
import pytest

from torii_api.services.content_packs import load_pack_by_scope
from torii_api.services.pdf_generator import generate_cover_letter_pdf, generate_dossier_packet_pdf
from torii_api.services.submission_kit import build_submission_kit

ANSWERS = {
    "full_name": "Md Hojayfa Rahman",
    "nationality": "BANGLADESH",
    "passport_number": "A05421997",
    "residence_card_number": "AB12345678CD",
}
CHECKLIST = [
    {"name": "Original valid passport", "citation": {"authority": "Immigration Services Agency"}},
    {
        "name": "Residence card (在留カード)",
        "citation": {"authority": "Immigration Services Agency"},
    },
]
FORMS = [
    {
        "form_code": "jp_work_extension",
        "official_title": "在留期間更新許可申請書（技術・人文知識・国際業務）",
    }
]


def _pdf_text(content: bytes) -> str:
    """Text as a reader sees it — ReportLab compresses streams, so raw bytes match nothing."""
    reader = pypdf.PdfReader(io.BytesIO(content))
    return " ".join(page.extract_text() or "" for page in reader.pages)


def _kit(category: str, action: str, scope: str | None = None):
    fees = list(load_pack_by_scope(scope).fees) if scope else []
    return build_submission_kit(
        jurisdiction_code="JP",
        visa_category=category,
        action=action,
        checklist=CHECKLIST,
        fees=fees,
        as_of=date(2026, 8, 26),
    )


# ── The kit differs by procedure ───────────────────────────────────────────────────


def test_each_procedure_names_its_own_office_and_filer() -> None:
    extension = _kit("work", "renewal")
    certificate = _kit("work", "new_application")
    consular = _kit("tourist", "new_application")
    assert extension and certificate and consular

    # Every ISA residence form is headed 法務大臣殿; the consular form is not.
    assert "法務大臣殿" in extension.addressee
    assert "法務大臣殿" in certificate.addressee
    assert "Embassy or Consulate-General" in consular.addressee

    # A certificate is filed in Japan by a proxy before the applicant has ever entered.
    assert "proxy" in certificate.filed_by
    assert "You, in person" in extension.filed_by


def test_steps_are_not_the_same_across_procedures() -> None:
    extension = [step.title for step in _kit("work", "renewal").steps]  # type: ignore[union-attr]
    consular = [step.title for step in _kit("tourist", "new_application").steps]  # type: ignore[union-attr]
    assert extension != consular
    assert any("Regional Immigration Services Bureau" in title for title in extension)
    assert any("mission" in title for title in consular)


def test_the_organisation_step_appears_only_where_the_packet_has_one() -> None:
    """A permanent-residence packet is two applicant sheets; nobody else fills it."""
    with_org = [step.title for step in _kit("work", "renewal").steps]  # type: ignore[union-attr]
    without = [step.title for step in _kit("permanent_resident", "new_application").steps]  # type: ignore[union-attr]
    assert any("employer, school or supporter" in title for title in with_org)
    assert not any("employer, school or supporter" in title for title in without)


def test_a_two_stage_application_says_so() -> None:
    kit = _kit("work", "new_application")
    assert kit is not None
    assert any("two stages" in note for note in kit.notes)


def test_fees_come_from_the_pack_and_only_when_published() -> None:
    """NF-2: a figure reaches the applicant only if the pack publishes it with a citation."""
    with_fee = _kit("work", "renewal", "jp/work.renewal")
    assert with_fee is not None
    assert with_fee.fee_note and "6,000 JPY" in with_fee.fee_note

    # A scope whose pack publishes no fee says nothing rather than inventing one.
    without_fee = _kit("spouse", "renewal")
    assert without_fee is not None
    assert without_fee.fee_note is None


def test_the_certificate_itself_is_free() -> None:
    kit = _kit("work", "new_application")
    assert kit is not None
    assert kit.fee_note and "No fee" in kit.fee_note


def test_the_stack_is_built_from_the_case_not_a_fixed_list() -> None:
    """It used to name a tax certificate and an employer statutory table for everyone."""
    kit = _kit("student", "renewal")
    assert kit is not None
    stack = " ".join(kit.stacking_order)
    assert "Original valid passport" in stack
    assert "在職証明書" not in stack
    assert "法定調書合計表" not in stack

    empty = build_submission_kit(
        jurisdiction_code="JP", visa_category="work", action="renewal", checklist=[]
    )
    assert empty is not None
    # Only the cover letter and the forms — nothing invented to pad it out.
    assert all("passport" not in entry.lower() for entry in empty.stacking_order)


def test_an_unmodelled_jurisdiction_gets_nothing_rather_than_another_countrys_ministry() -> None:
    """The old default branch cited mofa.go.jp as the authority for every country."""
    assert (
        build_submission_kit(jurisdiction_code="CA", visa_category="work", action="renewal") is None
    )
    assert build_submission_kit(jurisdiction_code=None, visa_category=None, action=None) is None
    assert (
        build_submission_kit(jurisdiction_code="JP", visa_category="unknown", action="renewal")
        is None
    )


def test_every_step_cites_a_real_source() -> None:
    for category, action in (
        ("work", "renewal"),
        ("work", "new_application"),
        ("tourist", "new_application"),
    ):
        kit = _kit(category, action)
        assert kit is not None
        for step in kit.steps:
            assert step.authority
            if step.citation_url:
                assert step.citation_url.startswith("https://")
                assert "example." not in step.citation_url


# ── The cover letter states only what the case establishes ─────────────────────────


def test_the_letter_is_addressed_per_procedure() -> None:
    extension = _pdf_text(
        generate_cover_letter_pdf("R-1", ANSWERS, CHECKLIST, submission_kit=_kit("work", "renewal"))
    )
    consular = _pdf_text(
        generate_cover_letter_pdf(
            "C-1", ANSWERS, CHECKLIST, submission_kit=_kit("tourist", "new_application")
        )
    )
    assert "法務大臣殿" in extension
    assert "法務大臣殿" not in consular
    assert "Embassy or Consulate-General" in consular


@pytest.mark.parametrize(
    "phrase",
    [
        "full compliance with local immigration laws",
        "substantiates ongoing professional engagement",
        "continuous compliance with tax and social contribution obligations",
        "Certified Compliant",
    ],
)
def test_the_letter_no_longer_certifies_facts_nobody_established(phrase: str) -> None:
    """Each of these was printed for every applicant, including students and dependents."""
    letter = _pdf_text(
        generate_cover_letter_pdf("R-1", ANSWERS, CHECKLIST, submission_kit=_kit("work", "renewal"))
    )
    dossier = _pdf_text(
        generate_dossier_packet_pdf(
            "R-1", ANSWERS, FORMS, CHECKLIST, submission_kit=_kit("work", "renewal")
        )
    )
    assert phrase not in letter
    assert phrase not in dossier


def test_an_empty_checklist_says_so_rather_than_listing_documents_that_do_not_exist() -> None:
    letter = _pdf_text(
        generate_cover_letter_pdf("R-1", ANSWERS, [], submission_kit=_kit("work", "renewal"))
    )
    assert "No supporting documents have been recorded" in letter
    assert "Municipal Resident Tax" not in letter
    assert "Certificate of Employment" not in letter


def test_the_letter_lists_the_cases_own_enclosures() -> None:
    letter = _pdf_text(
        generate_cover_letter_pdf(
            "R-1", ANSWERS, CHECKLIST, submission_kit=_kit("work", "renewal"), forms=FORMS
        )
    )
    assert "Original valid passport" in letter
    assert "在留期間更新許可申請書" in letter


def test_the_letter_is_readable_in_japanese_not_tofu() -> None:
    """The platypus styles are Helvetica, which has no CJK glyphs."""
    letter = generate_cover_letter_pdf(
        "R-1", ANSWERS, CHECKLIST, submission_kit=_kit("work", "renewal"), forms=FORMS
    )
    text = _pdf_text(letter)
    assert "法務大臣殿" in text
    assert "在留カード" in text


def test_the_dossier_snapshot_is_titled_from_the_form_the_case_files() -> None:
    """It was headed "Application for Extension of Period of Stay" for every case."""
    tourist_forms = [{"form_code": "jp_consular_visa", "official_title": "日本国査証申請書"}]
    dossier = _pdf_text(
        generate_dossier_packet_pdf(
            "C-1",
            ANSWERS,
            tourist_forms,
            CHECKLIST,
            submission_kit=_kit("tourist", "new_application"),
        )
    )
    assert "日本国査証申請書" in dossier
    assert "APPLICATION FOR EXTENSION OF PERIOD OF STAY" not in dossier


def test_the_dossier_shows_employment_only_when_the_applicant_stated_it() -> None:
    without = _pdf_text(
        generate_dossier_packet_pdf(
            "C-1", ANSWERS, FORMS, CHECKLIST, submission_kit=_kit("tourist", "new_application")
        )
    )
    assert "Monthly Remuneration" not in without

    with_job = _pdf_text(
        generate_dossier_packet_pdf(
            "R-1",
            {**ANSWERS, "employer_name": "AUREV Japan K.K.", "monthly_salary": "420,000 JPY"},
            FORMS,
            CHECKLIST,
            submission_kit=_kit("work", "renewal"),
        )
    )
    assert "AUREV Japan K.K." in with_job


def test_the_letter_prints_without_a_kit() -> None:
    """A scope with no modelled filing route still gets a letter, minus what it cannot support."""
    letter = generate_cover_letter_pdf("X-1", ANSWERS, CHECKLIST)
    assert letter.startswith(b"%PDF-")
    assert "Md Hojayfa Rahman" in _pdf_text(letter)


# ── The agent's research drives the filing route ───────────────────────────────────
# agentic_research.py has always produced process steps, fees and the filing channel for a
# corridor; the API consumed four of its five stages and hardcoded this one per country.
# docs/plan/03_corridor_bd_jp.md records that as G2.

_BD_CITATION = {
    "authority": "Embassy of Japan in Bangladesh",
    "title": "Visa section",
    "url": "https://www.bd.emb-japan.go.jp/itpr_en/visa.html",
}

_BD_JP_PAYLOAD: dict = {
    "admission": {
        "visa_required": True,
        "route": "consular_visa",
        "max_stay_days": 90,
        "citation": _BD_CITATION,
    },
    "filing_channel": {
        "channel": "accredited_travel_agency",
        "filer": "third_party",
        "mission_name": "Embassy of Japan in Bangladesh",
        "mission_url": "https://www.bd.emb-japan.go.jp/",
        "citation": _BD_CITATION,
    },
    "process": {
        "steps": [
            {"order": 2, "title": "File through an accredited agency", "detail": "Not direct."},
            {
                "order": 1,
                "title": "Complete the visa application form",
                "detail": "Attach a photo.",
            },
        ],
        "processing_time_days_min": 5,
        "processing_time_days_max": 10,
        "citation": _BD_CITATION,
    },
    "fees": [{"code": "single_entry", "amount": 3000, "currency": "BDT", "citation": _BD_CITATION}],
}


def test_research_supplies_the_corridor_specific_filing_route() -> None:
    """Neither the agency channel nor a taka fee follows from the destination alone."""
    from torii_api.services.submission_kit import kit_from_research

    authored = _kit("tourist", "new_application")
    kit = kit_from_research(_BD_JP_PAYLOAD, fallback=authored, checklist=CHECKLIST)
    assert kit is not None

    assert "Embassy of Japan in Bangladesh" in kit.office
    assert "accredited" in kit.office
    assert "not you directly" in kit.filed_by
    assert kit.fee_note == "3,000 BDT"
    assert any("5\u201310 working days" in note for note in kit.notes)

    # Steps come back in the order the agent numbered them, not payload order.
    assert [step.title for step in kit.steps] == [
        "Complete the visa application form",
        "File through an accredited agency",
    ]
    for step in kit.steps:
        assert step.citation_url == _BD_CITATION["url"]


def test_uncited_research_is_ignored_rather_than_shown() -> None:
    """NF-2: a filing instruction nobody can check against a government page is dropped."""
    from torii_api.services.submission_kit import kit_from_research

    payload = {"process": {"steps": [{"order": 1, "title": "Trust me", "detail": "no source"}]}}
    assert kit_from_research(payload, fallback=_kit("tourist", "new_application")) is None


def test_a_fee_without_a_citation_never_reaches_the_applicant() -> None:
    from torii_api.services.submission_kit import kit_from_research

    payload = dict(_BD_JP_PAYLOAD)
    payload["fees"] = [{"code": "guess", "amount": 9999, "currency": "BDT"}]
    kit = kit_from_research(payload, fallback=_kit("tourist", "new_application"))
    assert kit is not None
    assert kit.fee_note != "9,999 BDT"


def test_an_unresearched_corridor_keeps_the_authored_route() -> None:
    """Falling back is the point: no research must not mean an empty roadmap."""
    from torii_api.services.submission_kit import kit_from_research

    authored = _kit("work", "renewal", "jp/work.renewal")
    assert authored is not None
    assert kit_from_research({}, fallback=authored) is None
    # The caller keeps `authored`, which still names the bureau and the 6,000 JPY fee.
    assert "Regional Immigration Services Bureau" in authored.office
    assert authored.fee_note and "6,000 JPY" in authored.fee_note


def test_visa_free_corridors_say_so() -> None:
    from torii_api.services.submission_kit import kit_from_research

    payload = dict(_BD_JP_PAYLOAD)
    payload["admission"] = {**_BD_JP_PAYLOAD["admission"], "visa_required": False}
    kit = kit_from_research(payload, fallback=_kit("tourist", "new_application"))
    assert kit is not None
    assert any("visa-free" in note for note in kit.notes)


def test_research_accessors_gate_on_citations() -> None:
    from torii_api.services.research import (
        research_admission,
        research_fees,
        research_filing_channel,
        research_process_steps,
        research_processing_days,
    )

    assert research_process_steps(_BD_JP_PAYLOAD)
    assert research_fees(_BD_JP_PAYLOAD)
    assert research_filing_channel(_BD_JP_PAYLOAD)
    assert research_admission(_BD_JP_PAYLOAD)
    assert research_processing_days(_BD_JP_PAYLOAD) == (5, 10)

    # Malformed or empty payloads return empty rather than raising.
    for bad in ({}, {"process": None}, {"process": {"steps": "nope"}}, {"fees": "nope"}):
        assert research_process_steps(bad) == []
        assert research_fees(bad) == []
        assert research_filing_channel(bad) is None
        assert research_processing_days(bad) == (None, None)
