"""OCR-shaped extraction endpoint (US-06)."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from torii_ai.services import ocr as ocr_service
from torii_ai.services.ocr import DocumentType, OCRResult

router = APIRouter(prefix="/ai/ocr", tags=["ocr"])


class OCRExtractIn(BaseModel):
    doc_type: DocumentType
    filename: str = Field(min_length=1, max_length=256)
    hint_text: str | None = Field(default=None, max_length=10000)


@router.post("/extract", response_model=OCRResult)
async def extract(payload: OCRExtractIn) -> OCRResult:
    return ocr_service.extract_document_fields(
        payload.doc_type, payload.filename, payload.hint_text
    )
