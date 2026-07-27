"""Citation and instruction shapes (docs/specs/citation-contract.md)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

InstructionKind = Literal[
    "form_requirement",
    "field_help",
    "document_requirement",
    "eligibility",
    "process_step",
    "timeline",
]


class Citation(BaseModel):
    source_id: str = Field(default_factory=lambda: str(uuid4()))
    authority: str
    title: str = ""
    ref: str | None = None
    url: str | None = None
    retrieved_at: datetime
    source_version: str | None = None


class Instruction(BaseModel):
    instruction_id: str = Field(default_factory=lambda: str(uuid4()))
    text: str
    official_term: str | None = None
    kind: InstructionKind = "process_step"
    sources: list[Citation]
