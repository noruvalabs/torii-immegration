"""Render AcroForm values into the page and flatten the form.

The Ministry of Foreign Affairs visa form is an **XFA** PDF. Writing values into its
AcroForm layer stores them, but nothing draws them: Acrobat renders the XFA layer (which
does not carry them) and Chrome's viewer renders the AcroForm layer without regenerating
appearances. Either way the applicant downloads what looks like a blank form.

So the values are painted into the page content at each widget's own rectangle and the
interactive layer is removed. The result is an ordinary flat PDF that renders the same
in every viewer and prints correctly for signature at the consulate.
"""

from __future__ import annotations

import io
from typing import Any

import pypdf
import structlog
from pypdf.generic import ArrayObject, NameObject
from reportlab.lib.colors import Color
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas

log = structlog.get_logger(__name__)

INK = Color(0.05, 0.11, 0.42)
FONT = "Helvetica"
MAX_FONT_SIZE = 9.5
MIN_FONT_SIZE = 5.5
PADDING = 2.5


def _field_name(annotation: Any) -> str:
    """Fully qualified field name, walking up the widget's parent chain."""
    parts: list[str] = []
    node: Any = annotation
    for _ in range(12):
        if node is None:
            break
        name = node.get("/T")
        if name:
            parts.append(str(name))
        parent = node.get("/Parent")
        node = parent.get_object() if parent is not None else None
    return ".".join(reversed(parts))


def _export_values(annotation: Any) -> list[str]:
    """The ``/AP /N`` state names of a button widget — its export values."""
    appearance = annotation.get("/AP")
    if appearance is None:
        return []
    normal = appearance.get_object().get("/N")
    if normal is None:
        return []
    return [str(key) for key in normal.get_object().keys()]


def _draw_value(pdf: canvas.Canvas, rect: list[float], text: str) -> None:
    x0, y0, x1, y1 = rect
    width = max(8.0, (x1 - x0) - PADDING * 2)
    height = y1 - y0
    size = min(MAX_FONT_SIZE, max(MIN_FONT_SIZE, height - 3.5))
    while size > MIN_FONT_SIZE and pdfmetrics.stringWidth(text, FONT, size) > width:
        size -= 0.25
    pdf.setFont(FONT, size)
    # Sit on the baseline of a vertically centred line box.
    pdf.drawString(x0 + PADDING, y0 + (height - size) / 2.0 + 1.2, text)


def _draw_button(pdf: canvas.Canvas, rect: list[float]) -> None:
    x0, y0, x1, y1 = rect
    radius = min(x1 - x0, y1 - y0) / 2.0 - 1.6
    center_x = (x0 + x1) / 2.0
    center_y = (y0 + y1) / 2.0
    pdf.circle(center_x, center_y, max(1.8, radius), stroke=0, fill=1)


def flatten_form_values(
    template: bytes,
    values: dict[str, str],
    buttons: dict[str, str],
) -> tuple[bytes, list[str]]:
    """Paint ``values`` and ticked ``buttons`` into the page, then drop the form layer.

    ``values`` maps a fully qualified text-field name to its text; ``buttons`` maps a
    button group's name to the export value to select (for example ``"/1"``). Returns
    the flattened PDF and the names that had no widget to draw into, so a template
    revision surfaces instead of silently dropping answers.
    """
    reader = pypdf.PdfReader(io.BytesIO(template))
    writer = pypdf.PdfWriter()
    writer.append(reader)

    drawn: set[str] = set()

    for index, page in enumerate(writer.pages):
        annotations = page.get("/Annots")
        annotations = annotations.get_object() if annotations is not None else []
        if not annotations:
            continue

        media = page.mediabox
        overlay_buffer = io.BytesIO()
        pdf = canvas.Canvas(overlay_buffer, pagesize=(float(media.width), float(media.height)))
        pdf.setFillColor(INK)
        pdf.setStrokeColor(INK)
        wrote_anything = False

        for reference in annotations:
            annotation = reference.get_object()
            name = _field_name(annotation)
            if not name:
                continue
            try:
                rect = [float(value) for value in annotation.get("/Rect", [])]
            except (TypeError, ValueError):
                continue
            if len(rect) != 4:
                continue
            rect = [
                min(rect[0], rect[2]),
                min(rect[1], rect[3]),
                max(rect[0], rect[2]),
                max(rect[1], rect[3]),
            ]

            if name in values:
                text = values[name]
                if text:
                    _draw_value(pdf, rect, text)
                    drawn.add(name)
                    wrote_anything = True
            elif name in buttons and buttons[name] in _export_values(annotation):
                _draw_button(pdf, rect)
                drawn.add(name)
                wrote_anything = True

        pdf.save()
        overlay_buffer.seek(0)
        if wrote_anything:
            try:
                page.merge_page(pypdf.PdfReader(overlay_buffer).pages[0])
            except Exception as exc:  # pragma: no cover
                log.warning("acroform_flatten.merge_failed", page=index, error=str(exc))

        # Drop the interactive widgets now their values are part of the page.
        page[NameObject("/Annots")] = ArrayObject(
            [
                reference
                for reference in annotations
                if reference.get_object().get("/Subtype") != "/Widget"
            ]
        )

    root = writer.root_object
    if "/AcroForm" in root:
        del root[NameObject("/AcroForm")]

    buffer = io.BytesIO()
    writer.write(buffer)
    unplaced = sorted((set(values) | set(buttons)) - drawn)
    return buffer.getvalue(), unplaced
