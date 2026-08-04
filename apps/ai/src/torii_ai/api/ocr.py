"""OCR extraction endpoint (US-06) with PDF + image support."""

from __future__ import annotations

import base64
from typing import Literal

from fastapi import APIRouter, File, Form, UploadFile
from pydantic import BaseModel, Field

from torii_ai.services import ocr as ocr_service
from torii_ai.services.ocr import DocumentType, OCRResult

router = APIRouter(prefix="/ocr", tags=["ocr"])

PDF_MIMES = {"application/pdf"}
IMAGE_MIMES = {"image/jpeg", "image/png", "image/webp", "image/gif", "image/tiff", "image/bmp"}


class OCRExtractIn(BaseModel):
    doc_type: DocumentType
    filename: str = Field(min_length=1, max_length=256)
    hint_text: str | None = Field(default=None, max_length=10000)


@router.post("/extract", response_model=OCRResult)
async def extract(payload: OCRExtractIn) -> OCRResult:
    return ocr_service.extract_document_fields(
        payload.doc_type, payload.filename, payload.hint_text
    )


def _is_pdf(file: UploadFile, content: bytes) -> bool:
    """Detect PDF by content-type or magic bytes."""
    if file.content_type in PDF_MIMES:
        return True
    return content[:4] == b"%PDF"


def _is_image(file: UploadFile) -> bool:
    return (file.content_type or "").startswith("image/")


async def _extract_from_pdf(
    content: bytes,
    doc_type: DocumentType,
) -> OCRResult:
    """Extract text from PDF via PyMuPDF, then send to Groq qwen for field extraction."""
    import json
    import re

    from openai import OpenAI

    from torii_ai.config import get_settings
    from torii_ai.services.ocr import DOC_TYPE_PROMPTS, extract_text_from_pdf

    settings = get_settings()
    if not settings.groq_api_key:
        return ocr_service._fallback_extract(doc_type, "document.pdf", None)

    raw_text = extract_text_from_pdf(content)
    if not raw_text.strip():
        return ocr_service._fallback_extract(doc_type, "document.pdf", "Empty PDF")

    prompt = DOC_TYPE_PROMPTS.get(doc_type, DOC_TYPE_PROMPTS["passport"])
    user_content = f"Extracted PDF text:\n\n{raw_text[:8000]}\n\n{prompt}"

    try:
        client = OpenAI(api_key=settings.groq_api_key, base_url=settings.groq_base_url)
        response = client.chat.completions.create(
            model=settings.groq_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a document extraction assistant. "
                        "Given extracted text from a PDF document, extract the requested fields. "
                        "Return valid JSON only, no markdown fences."
                    ),
                },
                {"role": "user", "content": user_content},
            ],
            temperature=0.1,
            max_tokens=1024,
        )
        result_text = response.choices[0].message.content or ""
        return _parse_json_fields(result_text)

    except Exception:
        pass

    return ocr_service._fallback_extract(doc_type, "document.pdf", raw_text[:2000])


async def _extract_from_image(
    content: bytes,
    file: UploadFile,
    doc_type: DocumentType,
) -> OCRResult:
    """Send image to Groq qwen vision model for field extraction."""
    import json
    import re

    from openai import OpenAI

    from torii_ai.config import get_settings
    from torii_ai.services.ocr import DOC_TYPE_PROMPTS

    settings = get_settings()
    if not settings.groq_api_key:
        return ocr_service._fallback_extract(
            doc_type, file.filename or "image", f"[Uploaded: {file.filename}]"
        )

    b64_image = base64.b64encode(content).decode("utf-8")
    mime = file.content_type or "image/jpeg"
    prompt = DOC_TYPE_PROMPTS.get(doc_type, DOC_TYPE_PROMPTS["passport"])

    try:
        client = OpenAI(api_key=settings.groq_api_key, base_url=settings.groq_base_url)
        response = client.chat.completions.create(
            model=settings.groq_model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime};base64,{b64_image}"},
                        },
                    ],
                },
            ],
            temperature=0.1,
            max_tokens=1024,
        )
        result_text = response.choices[0].message.content or ""
        return _parse_json_fields(result_text)

    except Exception:
        pass

    return ocr_service._fallback_extract(
        doc_type, file.filename or "image", f"[Uploaded: {file.filename}]"
    )


def _parse_json_fields(text: str) -> OCRResult:
    """Parse LLM JSON response into OCRResult."""
    import json
    import re

    from torii_ai.services.ocr import ExtractedValue

    json_match = re.search(r"\{[\s\S]*\}", text)
    if not json_match:
        return OCRResult(fields={}, needs_recapture=True)

    try:
        raw_fields = json.loads(json_match.group())
    except json.JSONDecodeError:
        return OCRResult(fields={}, needs_recapture=True)

    fields: dict[str, ExtractedValue] = {}
    for key, val in raw_fields.items():
        if isinstance(val, dict) and "value" in val:
            fields[key] = ExtractedValue(
                value=str(val["value"]),
                confidence=float(val.get("confidence", 0.8)),
            )
        elif isinstance(val, str):
            fields[key] = ExtractedValue(value=val, confidence=0.8)

    return OCRResult(fields=fields, needs_recapture=False)


@router.post("/extract-file", response_model=OCRResult)
async def extract_file(
    file: UploadFile = File(...),
    doc_type: DocumentType = Form("passport"),
) -> OCRResult:
    """Extract fields from an uploaded PDF or image file.

    PDFs: PyMuPDF text extraction → Groq qwen for structured field extraction.
    Images: Groq qwen vision model for OCR + field extraction.
    """
    content = await file.read()
    if not content:
        return OCRResult(fields={}, needs_recapture=True)

    if _is_pdf(file, content):
        return await _extract_from_pdf(content, doc_type)

    if _is_image(file):
        return await _extract_from_image(content, file, doc_type)

    return OCRResult(fields={}, needs_recapture=True)
