"""Resolve, fetch and fill the official form for a case — the one call the API needs.

Ties the three pieces together: :mod:`jp_official_forms` says *which* form the
application type requires, :mod:`official_form_store` gets that exact PDF from the
issuing ministry, and :mod:`official_form_filler` writes the applicant's answers onto it.
When any of that is unavailable, generation falls back to the rendered application
summary rather than failing the download.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import structlog

from torii_api.services.jp_official_forms import (
    OfficialForm,
    forms_for_scope,
    primary_form_for_scope,
)
from torii_api.services.official_form_filler import (
    FillResult,
    fill_flat_form,
    missing_answer_keys,
)
from torii_api.services.official_form_store import ensure_template

log = structlog.get_logger(__name__)

SOURCE_OFFICIAL_TEMPLATE = "official_template"
SOURCE_BUNDLED_ACROFORM = "bundled_acroform"
SOURCE_UNAVAILABLE = "unavailable"


@dataclass
class RenderedForm:
    """A filled official form plus everything needed to explain and cite it."""

    form: OfficialForm
    content: bytes
    filename: str
    source: str
    provenance: dict[str, Any]
    fill: FillResult | None = None

    @property
    def metadata(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "code": self.form.code,
            "title_en": self.form.title_en,
            "title_ja": self.form.title_ja,
            "series": self.form.series,
            "procedure": self.form.procedure,
            "authority": self.form.authority,
            "source_page_url": self.form.source_page_url,
            "pdf_url": self.form.pdf_url,
            "pages": self.form.pages,
            "citation": self.form.citation,
            "note": self.form.note,
            "source": self.source,
            "provenance": self.provenance,
            "size_bytes": len(self.content),
        }
        if self.fill is not None:
            data.update(self.fill.summary)
            data["filled_fields"] = self.fill.filled
        return data


def _safe_stem(reference: str | None, case_id: int | None) -> str:
    raw = reference or (f"Case-{case_id}" if case_id is not None else "Case")
    return "".join(char for char in raw if char.isalnum() or char in ("-", "_", ".")) or "Case"


def form_filename(form: OfficialForm, reference: str | None, case_id: int | None = None) -> str:
    return f"{_safe_stem(reference, case_id)}_{form.code}.pdf"


async def render_form(
    form: OfficialForm,
    answers: dict[str, Any],
    *,
    reference: str | None = None,
    case_id: int | None = None,
    photo: bytes | None = None,
    applicant_email: str | None = None,
    scope_label: str | None = None,
) -> RenderedForm | None:
    """Fetch ``form`` from the ministry and write ``answers`` onto it.

    Returns ``None`` only when no local copy of the form can be obtained at all, which
    is the caller's signal to fall back to the generated application summary.
    """
    template = await ensure_template(form)
    if template is None:
        log.warning("official_form.template_unavailable", form=form.code)
        return None

    filename = form_filename(form, reference, case_id)
    provenance = template.provenance(form)

    if form.bundled_template is not None:
        # The consular form carries AcroForm fields; the dedicated filler handles it.
        from torii_api.services.pdf_generator import generate_official_japan_visa_form_pdf

        content = generate_official_japan_visa_form_pdf(
            reference or f"Case-{case_id}",
            answers,
            destination_label=scope_label or "Japan",
            applicant_email=applicant_email,
            photo_data=photo,
        )
        return RenderedForm(
            form=form,
            content=content,
            filename=filename,
            source=SOURCE_BUNDLED_ACROFORM,
            provenance=provenance,
        )

    result = fill_flat_form(form, template.content, answers, photo=photo)
    return RenderedForm(
        form=form,
        content=result.content,
        filename=filename,
        source=SOURCE_OFFICIAL_TEMPLATE,
        provenance=provenance,
        fill=result,
    )


async def render_primary_form(
    visa_category: str,
    action: str,
    answers: dict[str, Any],
    **kwargs: Any,
) -> RenderedForm | None:
    """The statutory form the application type turns on, filled."""
    form = primary_form_for_scope(visa_category, action)
    if form is None:
        return None
    return await render_form(form, answers, **kwargs)


def describe_scope_forms(
    visa_category: str, action: str, answers: dict[str, Any]
) -> list[dict[str, Any]]:
    """Every official form the scope requires, and what is still missing for each.

    Cheap: it reads the catalogue only, so the applicant can see which sheets their
    application needs — and which answers each still wants — without a download.
    """
    described: list[dict[str, Any]] = []
    for form in forms_for_scope(visa_category, action):
        entry: dict[str, Any] = {
            "code": form.code,
            "title_en": form.title_en,
            "title_ja": form.title_ja,
            "series": form.series,
            "procedure": form.procedure,
            "authority": form.authority,
            "source_page_url": form.source_page_url,
            "pdf_url": form.pdf_url,
            "pages": form.pages,
            "citation": form.citation,
            "note": form.note,
        }
        if form.layout is not None:
            all_layouts = (form.layout, *form.extra_layouts)
            missing = []
            total = 0
            for lyt in all_layouts:
                missing.extend(missing_answer_keys(lyt, answers))
                total += len(lyt.keys)
            entry["missing_answer_keys"] = list(dict.fromkeys(missing))
            entry["total_items"] = total
        described.append(entry)
    return described
