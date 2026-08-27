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
