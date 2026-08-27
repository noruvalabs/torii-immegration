"""Write an applicant's answers onto the real official Japanese form.

Two mechanisms, picked per form:

* The Ministry of Foreign Affairs consular form carries AcroForm fields, so values go
  into the named fields.
* The Immigration Services Agency residence forms are flat. Their ruled lines are
  recovered from the page geometry (:mod:`torii_api.services.pdf_geometry`), aligned
  against the authored layout (:mod:`torii_api.services.jp_form_layouts`), and the values
  are drawn on top.

The alignment is a hard gate. If the fetched PDF does not have the authored shape — a
revised sheet, a different document — nothing is drawn and the caller is told the layout
was not verified, because a value in the wrong box on a signed government form is worse
than a blank line.
"""

from __future__ import annotations

import io
import os
import re
import tempfile
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

import pypdf
import structlog
from reportlab.lib.colors import Color
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfgen import canvas

from torii_api.services.jp_form_layouts import (
    Box,
    ChoiceField,
    Flag,
    FormLayout,
    Gate,
    LineField,
    Mark,
)
from torii_api.services.jp_official_forms import ANSWER_ALIASES, OfficialForm
from torii_api.services.pdf_geometry import LayoutFit, fit_layout, page_rows

log = structlog.get_logger(__name__)

INK = Color(0.05, 0.11, 0.42)  # dark blue, the way these forms are filled by hand
LATIN_FONT = "Helvetica"
CJK_FONT = "HeiseiKakuGo-W5"
BASE_FONT_SIZE = 9.0
MIN_FONT_SIZE = 5.5
# Values sit just above the rule they are written on.
BASELINE_LIFT = 2.6
# Extra breathing room between a right-aligned date part and the 年 / 月 / 日 glyph
# that terminates its slot.
DATE_CLEARANCE = 3.0

_cjk_registered = False


def _cjk_font() -> str | None:
    """Register the CJK face lazily; returns ``None`` if this build lacks it."""
    global _cjk_registered
    if _cjk_registered:
        return CJK_FONT
    try:
        pdfmetrics.registerFont(UnicodeCIDFont(CJK_FONT))
    except Exception as exc:  # pragma: no cover - depends on the reportlab build
        log.warning("official_form.cjk_font_unavailable", error=str(exc))
        return None
    _cjk_registered = True
    return CJK_FONT


def _font_for(value: str) -> str:
    try:
        value.encode("latin-1")
    except UnicodeEncodeError:
        return _cjk_font() or LATIN_FONT
    return LATIN_FONT


@dataclass
class FillResult:
    """What was written, and what could not be."""

    content: bytes
    filled: dict[str, str] = field(default_factory=dict)
    missing: list[str] = field(default_factory=list)
    layout_verified: bool = True
    notes: list[str] = field(default_factory=list)
    # Which sheets in the packet belong to the applicant, and which of those were filled.
    # A ministry form is several forms stapled together and only some are theirs.
    applicant_pages: list[int] = field(default_factory=list)
    filled_pages: list[int] = field(default_factory=list)

    @property
    def summary(self) -> dict[str, Any]:
        return {
            "filled_items": len(self.filled),
            "missing_items": len(self.missing),
            "missing": self.missing,
            "layout_verified": self.layout_verified,
            "notes": self.notes,
            "applicant_pages": self.applicant_pages,
            "filled_pages": self.filled_pages,
            "unfilled_applicant_pages": [
                page for page in self.applicant_pages if page not in self.filled_pages
            ],
        }


# What each sheet in a ministry packet is, read off the page itself rather than assumed.
PAGE_APPLICANT = "applicant"
PAGE_ORGANISATION = "organisation"
PAGE_GUIDE = "guide"
PAGE_REFERENCE = "reference"

# Order matters. The selector sheet names both the applicant and the organisation parts
# in its instructions, so it has to be recognised first or it counts as fillable. The
# organisation check then runs before the applicant one, which lets the applicant markers
# stay broad enough to catch the permanent-residence form — that one is headed
# 様式その１ / その２ and never says 申請人等作成用 at all.
_GUIDE_MARKERS = ("在留目的に従って", "Select type of form which corresponds")
_ORGANISATION_MARKERS = (
    "所属機関等作成用",
    "扶養者等作成用",
    "For organization",
    "For supporter",
)
_APPLICANT_MARKERS = (
    "申請人等作成用",
    "For applicant",
    "永住許可申請書",
    "APPLICATION FOR PERMANENT RESIDENCE",
    "Permanent Residence",
)


def classify_pages(reader: Any) -> list[str]:
    """Label every page of a ministry packet by who is responsible for filling it."""
    labels: list[str] = []
    for page in reader.pages:
        try:
            text = (page.extract_text() or "").replace("　", " ")
        except Exception:  # pragma: no cover - malformed page
            text = ""
        if any(marker in text for marker in _GUIDE_MARKERS):
            labels.append(PAGE_GUIDE)
        elif any(marker in text for marker in _ORGANISATION_MARKERS):
            labels.append(PAGE_ORGANISATION)
        elif any(marker in text for marker in _APPLICANT_MARKERS):
            labels.append(PAGE_APPLICANT)
        else:
            labels.append(PAGE_REFERENCE)
    return labels


def _page_phrase(pages: list[int]) -> tuple[str, str]:
    """``([1, 3, 4])`` → ``("Pages 1, 3 and 4", "are")``."""
    if not pages:
        return ("", "are")
    if len(pages) == 1:
        return (f"Page {pages[0]}", "is")
    listed = ", ".join(str(page) for page in pages[:-1]) + f" and {pages[-1]}"
    return (f"Pages {listed}", "are")


# ── Value coercion ─────────────────────────────────────────────────────────────────

_TRUTHY = {"true", "yes", "y", "1", "有", "on"}
_FALSY = {"false", "no", "n", "0", "無", "off", "none"}


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, (date, datetime)):
        return value.strftime("%Y-%m-%d")
    return str(value).strip()


def _as_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        token = value.strip().lower()
        if token in _TRUTHY:
            return True
        if token in _FALSY:
            return False
    return None


def _split_date(value: Any) -> tuple[str, str, str] | None:
    """Split an answer into (year, month, day) for a 年月日 line.

    A year-and-month answer is accepted with an empty day, because several lines on these
    forms print only 年 and 月 -- a graduation month, a course period -- and are answered
    that way. Rejecting it left those lines blank on a sheet the applicant had answered.
    """
    raw = _text(value)
    if not raw:
        return None
    for pattern in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%d-%m-%Y", "%Y.%m.%d"):
        try:
            parsed = datetime.strptime(raw[:10], pattern)
        except ValueError:
            continue
        return (str(parsed.year), str(parsed.month), str(parsed.day))
    for pattern in ("%Y-%m", "%Y/%m", "%Y.%m"):
        try:
            parsed = datetime.strptime(raw[:7], pattern)
        except ValueError:
            continue
        return (str(parsed.year), str(parsed.month), "")
    return None


def _split_name(value: Any) -> tuple[str, str] | None:
    raw = _text(value)
    if not raw:
        return None
    parts = [part for part in raw.replace(",", " ").split() if part]
    if not parts:
        return None
    if len(parts) == 1:
        return (parts[0].upper(), "")
    return (parts[-1].upper(), " ".join(parts[:-1]).upper())


def resolve_answer(key: str, answers: dict[str, Any]) -> Any:
    """The answer for ``key``, falling back to the pack aliases for the same fact."""
    value = answers.get(key)
    if value not in (None, ""):
        return value
    for alias in ANSWER_ALIASES.get(key, ()):
        candidate = answers.get(alias)
        if candidate not in (None, ""):
            return candidate
    return None


def _is_dormant(field: LineField | ChoiceField | Flag, answers: dict[str, Any]) -> bool:
    """True when this field is conditional on another answer that does not satisfy it."""
    dependency = field.depends_on
    if dependency is None:
        return False
    if isinstance(dependency, Gate):
        token = _normalise_token(resolve_answer(dependency.key, answers))
        return token not in dependency.values
    return _as_bool(resolve_answer(dependency, answers)) is not True


def _normalise_token(value: Any) -> str:
    """An answer reduced to the shape an option token is written in."""
    return re.sub(r"[\s\-/]+", "_", _text(value).strip().lower())


def _choice_token(choice: ChoiceField, value: Any) -> str | None:
    """Map an answer onto one of this choice's printed positions.

    Matching is against the tokens the layout itself declares, so adding a thirty-box
    group is layout work rather than code work. `_CHOICE_ALIASES` only covers wordings a
    question may already have been answered in; anything it does not recognise is left
    unmarked and reported as still needing the applicant's hand.
    """
    options = {option for option, _ in choice.options}
    token = _normalise_token(value)
    if token:
        if token in options:
            return token
        alias = _CHOICE_ALIASES.get(token)
        if alias in options:
            return alias
    flag = _as_bool(value)
    if flag is not None:
        candidate = "yes" if flag else "no"
        if candidate in options:
            return candidate
    return None


# Wordings an answer may arrive in that are not the token printed on the form. Ops-facing
# option labels belong in `_form_questions.yml`; this is only the tolerance around them.
_CHOICE_ALIASES: dict[str, str] = {
    "m": "male",
    "男": "male",
    "男性": "male",
    "f": "female",
    "女": "female",
    "女性": "female",
    "既婚": "married",
    "有": "married",
    "unmarried": "single",
    "divorced": "single",
    "widowed": "single",
    "未婚": "single",
    "無": "single",
    "true": "yes",
    "false": "no",
    "あり": "yes",
    "なし": "no",
}


# ── Drawing ────────────────────────────────────────────────────────────────────────


def _draw_fitted(
    pdf: canvas.Canvas, text: str, x: float, y: float, max_width: float, *, right: bool = False
) -> None:
    """Draw ``text`` shrinking the face until it fits ``max_width``."""
    if not text:
        return
    font = _font_for(text)
    size = BASE_FONT_SIZE
    while size > MIN_FONT_SIZE and pdfmetrics.stringWidth(text, font, size) > max_width:
        size -= 0.25
    pdf.setFont(font, size)
    if right:
        pdf.drawRightString(x, y, text)
    else:
        pdf.drawString(x, y, text)


def _draw_line_field(pdf: canvas.Canvas, fit: LayoutFit, line: LineField, value: Any) -> str | None:
    rule = fit.column(line.row, line.column)
    if rule is None:
        return None
    baseline = rule.y + BASELINE_LIFT

    if line.dates is not None:
        parts = _split_date(value)
        if parts is None:
            return None
        # A 年月 line has no day box; writing one would land outside the ruling.
        date_slots = [line.dates.year, line.dates.month]
        if line.dates.day is not None:
            date_slots.append(line.dates.day)
        for part, nominal_x in zip(parts[: len(date_slots)], date_slots, strict=True):
            _draw_fitted(
                pdf, part, fit.map_x(nominal_x) - DATE_CLEARANCE, baseline, 34.0, right=True
            )
        return "-".join(parts[: len(date_slots)])

    if line.names is not None:
        split = _split_name(value)
        if split is None:
            return None
        family, given = split
        family_x = fit.map_x(line.names.family)
        given_x = fit.map_x(line.names.given)
        _draw_fitted(pdf, family, family_x, baseline, max(20.0, given_x - family_x - 8.0))
        if given:
            _draw_fitted(pdf, given, given_x, baseline, max(20.0, rule.x1 - given_x - 4.0))
        return f"{family} {given}".strip()

    text = _text(value)
    if not text:
        return None
    _draw_fitted(pdf, text, rule.x0 + 3.0, baseline, max(20.0, rule.width - 6.0))
    return text


def _draw_circle(pdf: canvas.Canvas, fit: LayoutFit, mark: Mark) -> None:
    """Ring a printed glyph, the way these forms are marked by hand (○で囲む)."""
    x0 = fit.map_x(mark.x0)
    x1 = fit.map_x(mark.x1)
    y = fit.map_y(mark.y)
    center_x = (x0 + x1) / 2.0
    center_y = y + 3.4
    radius_x = max(6.0, (x1 - x0) / 2.0 + 2.6)
    radius_y = 6.6
    pdf.setLineWidth(1.1)
    pdf.ellipse(
        center_x - radius_x,
        center_y - radius_y,
        center_x + radius_x,
        center_y + radius_y,
        stroke=1,
        fill=0,
    )


def _draw_tick(pdf: canvas.Canvas, fit: LayoutFit, mark: Mark) -> None:
    """Tick a □ checkbox."""
    x0 = fit.map_x(mark.x0)
    x1 = fit.map_x(mark.x1)
    y = fit.map_y(mark.y)
    pdf.setLineWidth(1.2)
    path = pdf.beginPath()
    path.moveTo(x0 + 0.6, y + 2.4)
    path.lineTo((x0 + x1) / 2.0, y + 0.4)
    path.lineTo(x1 + 1.4, y + 6.2)
    pdf.drawPath(path, stroke=1, fill=0)


def _is_stated(value: Any) -> bool:
    """True when the applicant actually gave this value.

    Zero is not a statement of support: an applicant who writes 0 yen of self-funding has
    said that box does not apply, so it stays clear.
    """
    text = _text(value).strip()
    if not text:
        return False
    try:
        return float(text.replace(",", "")) != 0.0
    except ValueError:
        return True


def _draw_choice(pdf: canvas.Canvas, fit: LayoutFit, choice: ChoiceField, value: Any) -> str | None:
    token = _choice_token(choice, value)
    if token is None:
        return None
    for option, mark in choice.options:
        if option == token:
            if choice.style == "tick":
                _draw_tick(pdf, fit, mark)
            else:
                _draw_circle(pdf, fit, mark)
            return option
    return None


def _draw_photo(pdf: canvas.Canvas, fit: LayoutFit, box: Box, image: bytes) -> bool:
    x0 = fit.map_x(box.x0)
    x1 = fit.map_x(box.x1)
    y0 = fit.map_y(box.y0)
    y1 = fit.map_y(box.y1)
    handle = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    try:
        handle.write(image)
        handle.close()
        # Inset so the photo sits inside the printed frame rather than over it.
        pdf.drawImage(
            handle.name,
            x0 + 2.0,
            y0 + 2.0,
            width=(x1 - x0) - 4.0,
            height=(y1 - y0) - 4.0,
            preserveAspectRatio=True,
            anchor="c",
        )
        return True
    except Exception as exc:  # pragma: no cover - malformed uploads
        log.warning("official_form.photo_failed", error=str(exc))
        return False
    finally:
        if os.path.exists(handle.name):
            os.remove(handle.name)


# ── Public entry point ─────────────────────────────────────────────────────────────


def fill_flat_form(
    form: OfficialForm,
    template: bytes,
    answers: dict[str, Any],
    *,
    photo: bytes | None = None,
) -> FillResult:
    """Overlay ``answers`` onto the applicant part of a flat ministry form."""
    layout = form.layout
    if layout is None:
        return FillResult(content=template, layout_verified=False, notes=["no layout authored"])

    reader = pypdf.PdfReader(io.BytesIO(template))
    if not reader.pages:
        return FillResult(content=template, layout_verified=False, notes=["template has no pages"])

    # Page 1 is the gate. If its layout does not fit, the packet is not the sheet these
    # coordinates were authored against and nothing at all is written.
    fit = fit_layout(page_rows(reader.pages[0], reader), layout.rows)
    if fit is None:
        log.warning("official_form.layout_unverified", form=form.code)
        return FillResult(
            content=template,
            layout_verified=False,
            missing=[f"{line.item} {line.label}" for line in layout.lines],
            notes=[
                "The published form no longer matches the verified layout, so no values "
                "were written onto it. The blank official form is attached unchanged."
            ],
        )

    filled: dict[str, str] = {}
    missing: list[str] = []
    notes: list[str] = []
    overlays: dict[int, io.BytesIO] = {}
    filled_pages: list[int] = []
    unsupported: list[str] = []

    for sheet in (layout, *form.extra_layouts):
        index = sheet.page
        if index >= len(reader.pages):
            continue
        page = reader.pages[index]
        sheet_fit = fit if index == 0 else fit_layout(page_rows(page, reader), sheet.rows)
        if sheet_fit is None:
            # One sheet failing does not invalidate the others; say which was skipped.
            log.warning("official_form.sheet_unverified", form=form.code, page=index + 1)
            notes.append(
                f"Page {index + 1} of the published form no longer matches its verified "
                "layout, so it was left blank — fill that page in by hand."
            )
            continue

        media = page.mediabox
        buffer = io.BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=(float(media.width), float(media.height)))
        pdf.setStrokeColor(INK)
        pdf.setFillColor(INK)

        # A dormant field is not drawn at all. Suppressing only its missing-report would
        # leave a retracted answer printed on the sheet: an applicant who answers the gate,
        # fills the block and then changes the gate to "no" would still sign a form
        # asserting the block. The blank is the correct output, and the form expects it.
        for line in sheet.lines:
            label = f"{line.item} {line.label}"
            if _is_dormant(line, answers):
                continue
            written = _draw_line_field(pdf, sheet_fit, line, resolve_answer(line.key, answers))
            if written:
                filled[label] = written
            else:
                missing.append(label)

        for choice in sheet.choices:
            label = f"{choice.item} {choice.label}"
            if _is_dormant(choice, answers):
                continue
            written = _draw_choice(pdf, sheet_fit, choice, resolve_answer(choice.key, answers))
            if written:
                filled[label] = written
            else:
                missing.append(label)

        # Multi-select boxes, each restating a value already written on this sheet.
        for flag in sheet.flags:
            if _is_dormant(flag, answers):
                continue
            if _is_stated(resolve_answer(flag.key, answers)):
                _draw_tick(pdf, sheet_fit, flag.mark)
                filled[f"{flag.item} {flag.label}"] = "ticked"

        if index == 0 and form.purpose_checkbox is not None:
            _draw_tick(pdf, sheet_fit, form.purpose_checkbox)
            filled["11 Purpose of entry"] = form.title_ja
        if sheet.photo is not None:
            if photo and _draw_photo(pdf, sheet_fit, sheet.photo, photo):
                filled["Photo"] = "attached"
            else:
                notes.append("Affix a 40mm × 30mm photograph in the printed panel before filing.")

        unsupported.extend(f"page {index + 1}: {item}" for item in sheet.unsupported_items)
        pdf.save()
        buffer.seek(0)
        overlays[index] = buffer
        filled_pages.append(index + 1)

    writer = pypdf.PdfWriter()
    writer.append(reader)
    try:
        for index, buffer in overlays.items():
            writer.pages[index].merge_page(pypdf.PdfReader(buffer).pages[0])
    except Exception as exc:  # pragma: no cover
        log.warning("official_form.merge_failed", form=form.code, error=str(exc))
        return FillResult(content=template, layout_verified=False, notes=["overlay merge failed"])

    output = io.BytesIO()
    writer.write(output)

    # Account for the whole packet, read off the pages themselves. A ministry form is
    # several forms stapled together: some sheets are the applicant's, some the
    # employer's or school's, and only the ones with an authored layout get filled.
    labels = classify_pages(reader)
    applicant_pages = [n for n, label in enumerate(labels, 1) if label == PAGE_APPLICANT]
    organisation_pages = [n for n, label in enumerate(labels, 1) if label == PAGE_ORGANISATION]
    outstanding = [page for page in applicant_pages if page not in filled_pages]
    if outstanding:
        phrase, verb = _page_phrase(outstanding)
        them = "it" if len(outstanding) == 1 else "them"
        notes.append(
            f"{phrase} {verb} also yours to complete — Torii does not fill {them} yet, so "
            f"fill {them} in by hand before filing."
        )
    if unsupported:
        notes.append(
            "These items are still yours to complete by hand: " + "; ".join(unsupported) + "."
        )
    if organisation_pages:
        phrase, verb = _page_phrase(organisation_pages)
        notes.append(
            f"{phrase} {verb} the organisation part (所属機関等作成用) and {verb} completed "
            "by your employer, school or supporter in Japan."
        )
    return FillResult(
        content=output.getvalue(),
        filled=filled,
        missing=missing,
        layout_verified=True,
        notes=notes,
        applicant_pages=applicant_pages,
        filled_pages=sorted(filled_pages),
    )


def missing_answer_keys(layout: FormLayout, answers: dict[str, Any]) -> list[str]:
    """Answer keys the layout needs that are still unanswered."""
    dormant = {line.key for line in layout.lines if _is_dormant(line, answers)}
    return [
        key
        for key in layout.keys
        if key not in dormant and resolve_answer(key, answers) in (None, "")
    ]
