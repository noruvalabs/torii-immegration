"""Offline OCR-shaped heuristic extraction for the applicant document flow."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

DocumentType = Literal["passport", "residence_card", "employment_contract"]


class ExtractedValue(BaseModel):
    value: str
    confidence: float


class OCRResult(BaseModel):
    fields: dict[str, ExtractedValue]
    needs_recapture: bool


def extract_document_fields(
    doc_type: DocumentType, filename: str, hint_text: str | None
) -> OCRResult:
    """Parse explicit text hints and filename tokens; this does not perform image recognition."""
    text = hint_text or Path(filename).stem.replace("_", " ").replace("-", " ")
    fields: dict[str, ExtractedValue] = {}

    if name_match := re.search(r"(?:name|holder)\s*[:=]\s*([^\n,;]+)", text, re.IGNORECASE):
        fields["full_name"] = ExtractedValue(value=name_match.group(1).strip(), confidence=0.9)

    if doc_type == "passport":
        match = re.search(
            r"(?:passport(?:\s*(?:number|no))?\s*[:=#]?\s*)([A-Z0-9]{5,12})",
            text,
            re.IGNORECASE,
        )
        if match:
            fields["passport_number"] = ExtractedValue(
                value=match.group(1).upper(), confidence=0.92
            )
    elif doc_type == "residence_card":
        match = re.search(
            r"(?:residence(?:\s*card)?(?:\s*(?:number|no))?\s*[:=#]?\s*)([A-Z0-9]{6,16})",
            text,
            re.IGNORECASE,
        )
        if match:
            fields["residence_card_number"] = ExtractedValue(
                value=match.group(1).upper(), confidence=0.9
            )
    else:
        match = re.search(r"(?:employer|company)\s*[:=]\s*([^\n,;]+)", text, re.IGNORECASE)
        if match:
            fields["employer_name"] = ExtractedValue(
                value=match.group(1).strip(), confidence=0.88
            )

    return OCRResult(fields=fields, needs_recapture=not fields)
