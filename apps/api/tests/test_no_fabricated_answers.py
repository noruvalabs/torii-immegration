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
    citation = resolve_official_citation(jurisdiction_code="ZZ", item_key_or_code="mystery_key")
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
