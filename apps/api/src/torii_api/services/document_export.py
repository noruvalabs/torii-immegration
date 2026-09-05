"""Render the applicant's drafted documents as real files: PDF or Word (.docx).

The filing kit produces six drafting documents (cover letter, schedule of stay, statement
of reason, financial guarantee, form data sheet, the combined kit). Until now they could
only leave the product as ``.txt``, which is not a document anybody hands to a consular
officer or opens in Word to finish. This module turns the exact text the applicant sees —
template or AI-drafted, including their own edits — into a paginated PDF or an editable
Word file, with no new runtime dependency: PDFs go through ReportLab, which the API
already uses for the official forms, and ``.docx`` is written as the minimal OOXML
package the format actually requires.

Nothing here invents content, and nothing is added above the text either: the applicant's
own wording starts the page. The only additions are the document's own title, typography,
and the "draft — check and sign before filing" footer.
"""

from __future__ import annotations

import io
import re
import zipfile
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
)

from torii_api.services.pdf_generator import _cjk_safe, _has_cjk

FORMATS = ("pdf", "docx")

MEDIA_TYPES = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "zip": "application/zip",
}

_FOOTER_NOTE = (
    "Draft prepared by Torii from the applicant's own answers - check every entry and "
    "sign before filing."
)

# A line of ===== or ----- used as a section divider in the generated text.
_RULE = re.compile(r"^\s*[=\-_~]{6,}\s*$")
# Two or more consecutive spaces inside a line mean the text is aligned in columns and
# must keep its spacing (itinerary tables, form data sheets) rather than being reflowed.
_TABULAR = re.compile(r"\S {2,}\S")
_HEADING = re.compile(r"^[A-Z0-9][A-Z0-9 ,.&()/:'’—–-]{4,90}$")


def safe_stem(value: str, fallback: str = "document") -> str:
    """A filename stem safe on every platform, without inventing one."""
    cleaned = "".join(c for c in (value or "") if c.isalnum() or c in ("-", "_", ".")).strip("._-")
    return cleaned[:120] or fallback


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()["Normal"]
    return {
        "title": ParagraphStyle(
            "ExportTitle",
            parent=base,
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=17,
            textColor=colors.HexColor("#0f172a"),
            spaceAfter=2,
        ),
        "heading": ParagraphStyle(
            "ExportHeading",
            parent=base,
            fontName="Helvetica-Bold",
            fontSize=10.5,
            leading=13,
            textColor=colors.HexColor("#0f172a"),
            spaceBefore=10,
            spaceAfter=3,
        ),
        "body": ParagraphStyle(
            "ExportBody",
            parent=base,
            fontName="Helvetica",
            fontSize=9.5,
            leading=13.5,
            textColor=colors.HexColor("#1e293b"),
            spaceAfter=2,
        ),
        "mono": ParagraphStyle(
            "ExportMono",
            parent=base,
            fontName="Courier",
            fontSize=8,
            leading=10.5,
            textColor=colors.HexColor("#1e293b"),
        ),
    }


def _is_heading(line: str, next_line: str | None) -> bool:
    stripped = line.strip()
    if not stripped or _has_cjk(stripped):
        return False
    if next_line is not None and _RULE.match(next_line):
        return True
    if stripped.endswith(":") and stripped[:-1].isupper():
        return True
    return bool(_HEADING.match(stripped)) and stripped == stripped.upper()


def _flowables(content: str, styles: dict[str, ParagraphStyle]) -> list:
    """Turn the document text into flowables, keeping aligned blocks aligned."""
    lines = content.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    flow: list = []
    mono_block: list[str] = []

    def flush_mono() -> None:
        if mono_block:
            flow.append(Preformatted("\n".join(mono_block), styles["mono"]))
            mono_block.clear()

    for index, raw in enumerate(lines):
        line = raw.rstrip()
        following = lines[index + 1] if index + 1 < len(lines) else None

        if _RULE.match(line):
            flush_mono()
            flow.append(Spacer(1, 2))
            flow.append(HRFlowable(width="100%", thickness=0.7, color=colors.HexColor("#cbd5e1")))
            flow.append(Spacer(1, 4))
            continue

        if not line.strip():
            flush_mono()
            flow.append(Spacer(1, 6))
            continue

        if _TABULAR.search(line) and not _has_cjk(line):
            # Column-aligned text (itineraries, data sheets) only reads correctly in a
            # fixed-width face; reflowing it as a paragraph would destroy the alignment.
            mono_block.append(line)
            continue

        flush_mono()
        indent_width = len(line) - len(line.lstrip())
        style = styles["heading"] if _is_heading(line, following) else styles["body"]
        text = _cjk_safe(escape(line.strip()))
        if indent_width >= 2 and style is styles["body"]:
            style = ParagraphStyle(
                f"ExportIndent{index}", parent=styles["body"], leftIndent=8 + indent_width * 2
            )
        flow.append(Paragraph(text, style))

    flush_mono()
    return flow


def render_pdf(documents: list[tuple[str, str]]) -> bytes:
    """One PDF holding the given ``(title, content)`` documents, one per page-run."""
    styles = _styles()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=48,
        rightMargin=48,
        topMargin=44,
        bottomMargin=48,
        title=documents[0][0] if documents else "Document",
    )

    story: list = []
    for position, (title, content) in enumerate(documents):
        if position:
            story.append(PageBreak())
        story.append(Paragraph(_cjk_safe(escape(title)), styles["title"]))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#94a3b8")))
        story.append(Spacer(1, 8))
        story.extend(_flowables(content, styles))

    def _furniture(canvas, current_doc) -> None:  # noqa: ANN001 - reportlab page callback
        canvas.saveState()
        canvas.setFont("Helvetica-Oblique", 7)
        canvas.setFillColor(colors.HexColor("#94a3b8"))
        canvas.drawString(48, 30, _FOOTER_NOTE)
        canvas.drawRightString(A4[0] - 48, 30, f"Page {canvas.getPageNumber()}")
        canvas.restoreState()

    doc.build(story, onFirstPage=_furniture, onLaterPages=_furniture)
    return buffer.getvalue()


# -- Word (.docx) -------------------------------------------------------------------
# A .docx is a zip of OOXML parts. Writing the parts Word requires directly keeps the
# export dependency-free and produces a file that opens in Word, Pages, LibreOffice and
# Google Docs - and, unlike a PDF, one the applicant can still edit before signing.

_CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" '
    'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-'
    'officedocument.wordprocessingml.document.main+xml"/>'
    '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-'
    'officedocument.wordprocessingml.styles+xml"/>'
    "</Types>"
)

_ROOT_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
    'relationships/officeDocument" Target="word/document.xml"/>'
    "</Relationships>"
)

_DOC_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
    'relationships/styles" Target="styles.xml"/>'
    "</Relationships>"
)

_STYLES_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
    "<w:docDefaults><w:rPrDefault><w:rPr>"
    '<w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:eastAsia="MS Mincho" w:cs="Calibri"/>'
    '<w:sz w:val="21"/><w:szCs w:val="21"/></w:rPr></w:rPrDefault></w:docDefaults>'
    '<w:style w:type="paragraph" w:styleId="Normal" w:default="1"><w:name w:val="Normal"/>'
    '<w:pPr><w:spacing w:after="80" w:line="264" w:lineRule="auto"/></w:pPr></w:style>'
    '<w:style w:type="paragraph" w:styleId="ToriiTitle"><w:name w:val="Torii Title"/>'
    '<w:pPr><w:spacing w:after="40"/></w:pPr>'
    '<w:rPr><w:b/><w:sz w:val="30"/><w:szCs w:val="30"/></w:rPr></w:style>'
    '<w:style w:type="paragraph" w:styleId="ToriiMeta"><w:name w:val="Torii Meta"/>'
    '<w:pPr><w:spacing w:after="200"/></w:pPr>'
    '<w:rPr><w:i/><w:color w:val="64748B"/><w:sz w:val="17"/><w:szCs w:val="17"/></w:rPr>'
    "</w:style>"
    '<w:style w:type="paragraph" w:styleId="ToriiHeading"><w:name w:val="Torii Heading"/>'
    '<w:pPr><w:spacing w:before="200" w:after="60"/></w:pPr>'
    '<w:rPr><w:b/><w:sz w:val="23"/><w:szCs w:val="23"/></w:rPr></w:style>'
    '<w:style w:type="paragraph" w:styleId="ToriiMono"><w:name w:val="Torii Mono"/>'
    '<w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/></w:pPr>'
    '<w:rPr><w:rFonts w:ascii="Consolas" w:hAnsi="Consolas" w:cs="Consolas"/>'
    '<w:sz w:val="17"/><w:szCs w:val="17"/></w:rPr></w:style>'
    "</w:styles>"
)


def _docx_paragraph(text: str, style: str = "Normal") -> str:
    opening = f'<w:p><w:pPr><w:pStyle w:val="{style}"/></w:pPr>'
    if not text.strip():
        return opening + "</w:p>"
    return opening + f'<w:r><w:t xml:space="preserve">{escape(text)}</w:t></w:r></w:p>'


def _docx_body(documents: list[tuple[str, str]]) -> str:
    parts: list[str] = []
    for position, (title, content) in enumerate(documents):
        if position:
            parts.append('<w:p><w:r><w:br w:type="page"/></w:r></w:p>')
        parts.append(_docx_paragraph(title, "ToriiTitle"))
        for raw in content.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
            line = raw.rstrip()
            if _RULE.match(line):
                parts.append(_docx_paragraph(""))
                continue
            if _TABULAR.search(line):
                parts.append(_docx_paragraph(line, "ToriiMono"))
                continue
            style = "ToriiHeading" if _is_heading(line, None) else "Normal"
            parts.append(_docx_paragraph(line, style))
    parts.append(_docx_paragraph(""))
    parts.append(_docx_paragraph(_FOOTER_NOTE, "ToriiMeta"))
    return "".join(parts)


def render_docx(documents: list[tuple[str, str]]) -> bytes:
    """One editable Word file holding the given ``(title, content)`` documents."""
    body = _docx_body(documents)
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{body}"
        '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
        '<w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134" '
        'w:header="709" w:footer="709" w:gutter="0"/></w:sectPr>'
        "</w:body></w:document>"
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _CONTENT_TYPES)
        archive.writestr("_rels/.rels", _ROOT_RELS)
        archive.writestr("word/_rels/document.xml.rels", _DOC_RELS)
        archive.writestr("word/styles.xml", _STYLES_XML)
        archive.writestr("word/document.xml", document_xml)
    return buffer.getvalue()


_RENDERERS = {"pdf": render_pdf, "docx": render_docx}


def render_document(documents: list[tuple[str, str]], *, fmt: str) -> bytes:
    """Render every document into one file of ``fmt``."""
    renderer = _RENDERERS.get(fmt)
    if renderer is None:
        raise ValueError(f"unsupported export format '{fmt}'")
    return renderer(documents)


def render_bundle(documents: list[tuple[str, str, str]], *, fmt: str) -> bytes:
    """A zip holding each ``(title, stem, content)`` document as its own ``fmt`` file."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for title, stem, content in documents:
            archive.writestr(
                f"{safe_stem(stem, 'document')}.{fmt}",
                render_document([(title, content)], fmt=fmt),
            )
    return buffer.getvalue()


__all__ = [
    "FORMATS",
    "MEDIA_TYPES",
    "render_bundle",
    "render_docx",
    "render_document",
    "render_pdf",
    "safe_stem",
]
