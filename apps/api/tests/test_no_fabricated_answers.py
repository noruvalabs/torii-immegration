"""Guards against inventing applicant facts.

These documents accompany a sworn immigration application. A blank line asks the
applicant a question; a plausible-looking guess makes a false statement to a government
on their behalf. Every check here failed at least once before it was written — see the
values in ``_KNOWN_FABRICATIONS``, all of which shipped.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from torii_api.services.citations import resolve_official_citation
from torii_api.services.forms import fill_form
from torii_api.services.official_form_filler import ANSWER_ALIASES, resolve_answer
from torii_api.services.pdf_generator import (
    NOT_PROVIDED,
    generate_generic_visa_application_pdf,
    generate_japan_work_renewal_pdf,
    generate_uk_visa_application_pdf,
    generate_us_visa_application_pdf,
)

SERVICES = Path(__file__).resolve().parent.parent / "src" / "torii_api" / "services"


def _pdf_text(content: bytes) -> str:
    """Text as a reader sees it. ReportLab compresses its streams, so scanning the raw
    bytes silently matches nothing and every assertion over it passes vacuously."""
    import io

    import pypdf

    reader = pypdf.PdfReader(io.BytesIO(content))
    return " ".join(page.extract_text() or "" for page in reader.pages)


# Real examples that shipped. Each asserted a fact about the applicant that they had
# never stated — an English test result, an employer category driving fee tiers, a
# course year, an occupation code.
_KNOWN_FABRICATIONS = (
    "Passed approved SELT test at CEFR B1",
    "Category 3 (Listed / Standard)",
    "Academic Year 2026/2027",
    "Standard SOC Eligible Code",
    "Verified via Bank Solvency Certificate",
    "Full-time (Seishain) / Permanent",
    "Degree Programme / RQF Level 6+",
    "Self-Funded via Personal Savings",
    "Verified via CAS Higher Education Assessment",
    "Filed / Attached in Dossier",
)

# Placeholders that are honest about being empty, plus the handful of literals that are
# control flow (a membership test) rather than a value written onto a document.
_ALLOWED_FALLBACKS = {NOT_PROVIDED, "", "change_of_status", "tourism"}


def _answer_fallbacks(source: str) -> list[tuple[int, str]]:
    """Every string literal used as the fallback of an ``answers.get(...)`` chain."""
    found: list[tuple[int, str]] = []
    for number, line in enumerate(source.splitlines(), 1):
        if "answers.get(" not in line:
            continue
        for match in re.finditer(r'or\s+"([^"]*)"', line):
            found.append((number, match.group(1)))
    return found


def test_no_fabricated_defaults_in_the_pdf_generators() -> None:
    source = (SERVICES / "pdf_generator.py").read_text(encoding="utf-8")
    offenders = [
        (number, value)
        for number, value in _answer_fallbacks(source)
        if value not in _ALLOWED_FALLBACKS
    ]
    assert offenders == [], (
        "An unanswered field must print NOT_PROVIDED, never an invented value. "
        f"Offending fallbacks: {offenders}"
    )


def _code_only(path: Path) -> str:
    """Source with comments stripped — the comments explaining these mistakes may cite them."""
    import io
    import tokenize

    kept: list[str] = []
    with path.open("rb") as handle:
        for token in tokenize.tokenize(io.BytesIO(handle.read()).readline):
            if token.type != tokenize.COMMENT:
                kept.append(token.string)
    return "\n".join(kept)


@pytest.mark.parametrize("phrase", _KNOWN_FABRICATIONS)
def test_previously_shipped_fabrications_are_gone(phrase: str) -> None:
    for path in SERVICES.glob("*.py"):
        assert phrase not in _code_only(path), f"{path.name} still fabricates {phrase!r}"


@pytest.mark.parametrize(
    "generator",
    [
        generate_japan_work_renewal_pdf,
        generate_uk_visa_application_pdf,
        generate_us_visa_application_pdf,
        generate_generic_visa_application_pdf,
    ],
)
def test_an_empty_case_produces_no_invented_content(generator) -> None:
    """With no answers at all, nothing about the applicant may be asserted."""
    content = generator("CASE-1", {})
    assert content.startswith(b"%PDF-")
    rendered = _pdf_text(content)
    # Sanity: the extraction actually sees the document, so the checks below mean something.
    assert "CASE-1" in rendered or "APPLICATION" in rendered.upper()
    for phrase in _KNOWN_FABRICATIONS:
        assert phrase not in rendered, f"{generator.__name__} still prints {phrase!r}"


def test_sex_and_marital_status_are_never_assumed() -> None:
    """Both used to default to 'Male' and 'Single' when unanswered."""
    source = (SERVICES / "pdf_generator.py").read_text(encoding="utf-8")
    for number, value in _answer_fallbacks(source):
        assert value not in ("Male", "Female", "Single", "Married"), (
            f"pdf_generator.py:{number} assumes {value!r}"
        )


def test_form_filling_never_derives_one_fact_from_another() -> None:
    """A savings figure is not a declaration of sufficient funds."""
    mappings = [
        {"form_field": "funds", "answer_key": "visitor_has_sufficient_funds", "required": True},
        {"form_field": "guarantor_name", "answer_key": "relationship_to_visitor", "required": True},
    ]
    filled = fill_form(
        mappings, {"estimated_savings_available": "12000", "trip_payer": "self_funded"}
    )
    assert "funds" not in filled.filled_fields
    assert "guarantor_name" not in filled.filled_fields
    assert set(filled.missing_required_fields) == {"funds", "guarantor_name"}


def test_official_form_aliases_are_all_the_same_fact() -> None:
    """Substitutions that shipped and were wrong: a hotel as a residence, a guarantor's phone."""
    assert "accommodation_address" not in ANSWER_ALIASES["current_japan_address"]
    assert "guarantor_telephone" not in ANSWER_ALIASES["telephone_japan"]
    assert "place_of_birth" not in ANSWER_ALIASES
    assert "change_reason" not in ANSWER_ALIASES
    assert "employment_status" not in ANSWER_ALIASES["occupation"]


def test_place_of_birth_is_not_filled_from_nationality() -> None:
    assert resolve_answer("place_of_birth", {"nationality": "BANGLADESH"}) is None
    assert resolve_answer("place_of_birth", {"place_of_birth": "Dhaka"}) == "Dhaka"


def test_an_unresolvable_citation_is_empty_not_invented() -> None:
    """It used to synthesise 'https://www.gov.xx/visa', which reads as an official source."""
    citation = resolve_official_citation(jurisdiction_code="ZZ", visa_category="mystery")
    assert citation["url"] in ("", None) or citation["url"].startswith("http")
    assert "www.gov.zz" not in str(citation["url"])


def test_every_citation_url_in_the_resolver_is_a_real_official_url() -> None:
    """No placeholder or example URLs in the citation table."""
    source = (SERVICES / "citations.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    urls = [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and node.value.startswith("http")
    ]
    assert urls
    for url in urls:
        assert "example." not in url
        assert "gov.xx" not in url
        assert not re.match(r"https://www\.gov\.\{", url)


# ── The web packet step generates documents client-side too ────────────────────────
# Those are drafts the applicant signs and hands to a consulate, so the same rule
# applies there as in the PDF generators: never state what the applicant has not.

_PACKET_STEP = (
    Path(__file__).resolve().parents[2]
    / "web"
    / "src"
    / "components"
    / "applicant"
    / "steps"
    / "PacketStep.tsx"
)

# Every one of these shipped. The itinerary generator invented a hotel, its address and
# phone number, and a day-by-day plan chosen by `day % 3`; the expense declaration had
# the applicant certify funds and enclosures that may not exist.
_CLIENT_FABRICATIONS = (
    "Tokyo Central Hotel",
    "+81-3-0000-0000",
    "Chiyoda-ku, Tokyo, Japan",
    "fully provided for and guaranteed",
    "will not become a public burden",
    "Cultural sightseeing, visiting historical heritage sites",
    "Employed Professional",
    "Company / Business Organization",
    "Self-Employed / Business / Company",
    "Verified regular income",
    "(Verified & Attached)",
)


def _packet_step_code() -> str:
    """The file with comments stripped — a comment may name what was removed, code may not."""
    source = _PACKET_STEP.read_text(encoding="utf-8")
    return " ".join(line for line in source.splitlines() if not line.lstrip().startswith("//"))


@pytest.mark.skipif(not _PACKET_STEP.is_file(), reason="web app not present")
@pytest.mark.parametrize("phrase", _CLIENT_FABRICATIONS)
def test_the_packet_step_does_not_fabricate_client_side(phrase: str) -> None:
    assert phrase not in _packet_step_code(), f"PacketStep.tsx still fabricates {phrase!r}"


@pytest.mark.skipif(not _PACKET_STEP.is_file(), reason="web app not present")
def test_the_packet_step_does_not_claim_to_verify_documents() -> None:
    """Torii records what the applicant says they hold; it verifies nothing."""
    source = _PACKET_STEP.read_text(encoding="utf-8")
    assert "verified your document checklist" not in source


@pytest.mark.skipif(not _PACKET_STEP.is_file(), reason="web app not present")
def test_the_itinerary_is_left_for_the_applicant_to_write() -> None:
    """A generated day-by-day plan is a fiction the applicant signs and files."""
    code = _packet_step_code()
    assert "day % 3" not in code
    assert "Plan for the day" in code


# ── An item's own citation is the accurate one ─────────────────────────────────────
# The resolver used to override an authored citation whenever its URL looked "generic"
# to a heuristic, and to derive one from words in an answer key otherwise.


def test_an_items_own_citation_wins_over_the_fallback() -> None:
    authored = {
        "authority": "Immigration Services Agency of Japan",
        "title": "Application for Extension of Period of Stay",
        "url": "https://www.moj.go.jp/isa/applications/procedures/16-3.html",
        "source_version": "2026-04",
    }
    resolved = resolve_official_citation(
        jurisdiction_code="JP", visa_category="work", existing_citation=authored
    )
    assert resolved["url"] == authored["url"]
    assert resolved["title"] == authored["title"]
    assert resolved["authority"] == authored["authority"]


def test_a_generic_looking_url_is_still_the_items_own_citation() -> None:
    """16-3.html is the real page for an extension; the heuristic used to replace it."""
    authored = {
        "authority": "Immigration Services Agency of Japan",
        "title": "Resident tax certificate",
        "url": "https://www.moj.go.jp/isa/applications/procedures/16-3.html",
    }
    resolved = resolve_official_citation(
        jurisdiction_code="JP", visa_category="student", existing_citation=authored
    )
    assert resolved["url"] == authored["url"]


def test_an_incomplete_citation_falls_back_to_the_scope_not_to_a_keyword() -> None:
    """A work case gets the work page, whatever words the item's key happens to contain."""
    for partial in ({}, {"url": "https://x.example"}, {"authority": "Somebody"}, None):
        resolved = resolve_official_citation(
            jurisdiction_code="JP",
            visa_category="work",
            existing_citation=partial,  # type: ignore[arg-type]
        )
        assert resolved["url"].endswith("/status/gijinkoku.html")


def test_an_unknown_jurisdiction_resolves_to_nothing_rather_than_a_guess() -> None:
    resolved = resolve_official_citation(jurisdiction_code="ZZ", visa_category="work")
    assert resolved["url"] == ""
    assert resolved["authority"] == ""


def test_the_resolver_cannot_be_handed_an_item_key() -> None:
    """Deriving a source from words in a key is what the rewrite exists to stop."""
    import inspect

    parameters = inspect.signature(resolve_official_citation).parameters
    assert "item_key_or_code" not in parameters
    # No substring sniffing anywhere in the module either. Checked on the parse tree, so
    # the docstring quoting the removed branches does not count as one.
    tree = ast.parse((SERVICES / "citations.py").read_text(encoding="utf-8"))
    membership = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Compare) and any(isinstance(op, ast.In) for op in node.ops)
    ]
    assert membership == []


# ── Japanese answers must survive every form path ──────────────────────────────────
# The consular form is printed in English, but several of its boxes ask for facts that
# are Japanese: where the applicant will stay, who invites them, the guarantor. Helvetica
# has no glyph for a kanji and reportlab raises nothing -- it draws a black box per
# character -- so this failed silently and the applicant downloaded ■■■ where a name
# should be.


@pytest.mark.parametrize(
    "value",
    [
        "田中 由紀",
        "東京都新宿区西新宿1-1-7",
        "Aurora Systems 株式会社",
        "ダッカ日本語センター",
    ],
)
def test_a_japanese_answer_is_not_drawn_as_black_boxes(value: str) -> None:
    import io

    import pypdf
    from reportlab.pdfgen import canvas

    from torii_api.services.acroform_flatten import _draw_value

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer)
    _draw_value(pdf, [50.0, 700.0, 400.0, 716.0], value)
    pdf.save()
    buffer.seek(0)

    text = pypdf.PdfReader(buffer).pages[0].extract_text() or ""
    assert "■" not in text, f"{value!r} rendered as tofu"
    # The characters themselves reached the page, not just "something non-empty".
    assert value.split()[0] in text


def test_both_form_paths_agree_on_which_face_can_draw_a_value() -> None:
    """The consular form and the residence forms must not disagree about a kanji."""
    from torii_api.services.acroform_flatten import _font_for as consular_font
    from torii_api.services.official_form_filler import _font_for as residence_font

    for value in ("Md Hojayfa Rahman", "田中 由紀", "Aurora Systems 株式会社"):
        assert consular_font(value) == residence_font(value)


def test_fill_form_deduplicates_synonym_aliases() -> None:
    """Auto-fill must not duplicate synonym alias fields (e.g. nationality vs citizenship)."""
    answers = {
        "nationality": "Bangladesh",
        "citizenship": "Bangladesh",
        "country_of_citizenship": "Bangladesh",
        "country_of_nationality": "Bangladesh",
        "current_country": "Bangladesh",
        "current_residence_country": "Bangladesh",
        "residence_country": "Bangladesh",
        "home_town_city": "Dhaka",
        "home_city": "Dhaka",
        "hometown": "Dhaka",
    }
    filled = fill_form([], answers)
    # Ensure nationality is present under one clean label and synonyms are not duplicated
    assert "Nationality / Citizenship" in filled.filled_fields
    assert "Citizenship" not in filled.filled_fields
    assert "Country Of Nationality" not in filled.filled_fields
    assert "Country Of Citizenship" not in filled.filled_fields

    # Current country alias deduplication
    assert "Current Country" in filled.filled_fields
    assert "Country of Current Residence" not in filled.filled_fields
    assert "Country of Residence" not in filled.filled_fields

    # Hometown alias deduplication
    assert "Home Town City" in filled.filled_fields
    assert "Home City" not in filled.filled_fields
    assert "Hometown" not in filled.filled_fields


def test_apply_extracted_fields_normalizes_statutory_and_japanese_keys() -> None:
    """Document extraction keys like '6.国籍' or '生年月日' must normalize to canonical keys."""
    from unittest.mock import MagicMock

    from torii_api.api.case_workflow import _apply_extracted_fields_to_case_and_user

    mock_case = MagicMock()
    mock_case.intake_answers = {}
    mock_user = MagicMock()

    extracted = {
        "6.国籍": "Bangladesh",
        "生年月日": "2003-10-23",
        "氏名": "Hasib Rahman",
    }
    _apply_extracted_fields_to_case_and_user(mock_case, mock_user, extracted)

    assert "6.国籍" not in mock_case.intake_answers
    assert mock_case.intake_answers["nationality"] == "Bangladesh"
    assert mock_case.intake_answers["date_of_birth"] == "2003-10-23"
    assert mock_case.intake_answers["full_name"] == "Hasib Rahman"
    assert mock_user.nationality == "Bangladesh"
    assert mock_user.full_name == "Hasib Rahman"
