"""OCR extraction endpoint (US-06) with vision model support."""

from __future__ import annotations

import base64
from typing import Literal

from fastapi import APIRouter, File, Form, UploadFile
from pydantic import BaseModel, Field

from torii_ai.services import ocr as ocr_service
from torii_ai.services.ocr import DocumentType, OCRResult

router = APIRouter(prefix="/ocr", tags=["ocr"])


class OCRExtractIn(BaseModel):
    doc_type: DocumentType
    filename: str = Field(min_length=1, max_length=256)
    hint_text: str | None = Field(default=None, max_length=10000)


@router.post("/extract", response_model=OCRResult)
async def extract(payload: OCRExtractIn) -> OCRResult:
    return ocr_service.extract_document_fields(
        payload.doc_type, payload.filename, payload.hint_text
    )


@router.post("/extract-file", response_model=OCRResult)
async def extract_file(
    file: UploadFile = File(...),
    doc_type: DocumentType = Form("passport"),
) -> OCRResult:
    """Extract fields from an uploaded image file using vision model."""
    content = await file.read()
    if not content:
        return OCRResult(fields={}, needs_recapture=True)

    hint_text = f"[Uploaded file: {file.filename}]"

    import json
    import re

    from openai import OpenAI

    from torii_ai.config import get_settings

    settings = get_settings()

    if not settings.groq_api_key:
        return ocr_service.extract_document_fields(doc_type, file.filename or "document", hint_text)

    try:
        client = OpenAI(
            api_key=settings.groq_api_key,
            base_url=settings.groq_base_url,
        )

        b64_image = base64.b64encode(content).decode("utf-8")
        mime = file.content_type or "image/jpeg"

        from torii_ai.services.ocr import DOC_TYPE_PROMPTS

        prompt = DOC_TYPE_PROMPTS.get(doc_type, DOC_TYPE_PROMPTS["passport"])

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

        content_text = response.choices[0].message.content or ""

        json_match = re.search(r"\{[\s\S]*\}", content_text)
        if json_match:
            raw_fields = json.loads(json_match.group())
            fields = {}
            for key, val in raw_fields.items():
                if isinstance(val, dict) and "value" in val:
                    from torii_ai.services.ocr import ExtractedValue

                    fields[key] = ExtractedValue(
                        value=str(val["value"]),
                        confidence=float(val.get("confidence", 0.8)),
                    )
                elif isinstance(val, str):
                    from torii_ai.services.ocr import ExtractedValue

                    fields[key] = ExtractedValue(value=val, confidence=0.8)
            return OCRResult(fields=fields, needs_recapture=False)

    except Exception:
        pass

    return ocr_service.extract_document_fields(doc_type, file.filename or "document", hint_text)
