"""Branching intake questionnaire — definitions, visibility, and answer validation (US-02).

Framework-free so routers, seeds, and tests share the same deterministic rules (NF-1).
"""

from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field

from torii_api.services.pack_exports import pack_questions

QuestionType = Literal["boolean", "string", "integer", "enum", "date"]


class ShowWhen(BaseModel):
    """Reveal this question only when another answer equals ``equals``."""

    key: str
    equals: bool | str | int


class IntakeQuestion(BaseModel):
    """One plain-language intake question in a scoped definition (US-02.1)."""

    key: str = Field(min_length=1, max_length=64)
    prompt: str = Field(min_length=1, max_length=512)
    type: QuestionType
    options: list[str] | None = None
    required: bool = True
    show_when: ShowWhen | None = None
    min_length: int | None = None
    max_length: int | None = None
    min_value: int | None = None
    max_value: int | None = None
    section: str | None = None
    citation: dict[str, Any] | None = None


class IntakeProgress(BaseModel):
    answered: int
    total: int
    complete: bool


def is_visible(question: IntakeQuestion, answers: dict[str, Any]) -> bool:
    """Whether ``question`` applies given current ``answers`` (US-02.2)."""
    rule = question.show_when
    if rule is None:
        return True
    return answers.get(rule.key) == rule.equals


def visible_questions(
    questions: list[IntakeQuestion], answers: dict[str, Any]
) -> list[IntakeQuestion]:
    """Questions the applicant should see for the current branch."""
    return [q for q in questions if is_visible(q, answers)]


def validate_answer(question: IntakeQuestion, value: Any) -> str | None:
    """Return an error message if ``value`` is invalid for ``question``, else ``None`` (US-02.3)."""
    if value is None:
        return "answer is required" if question.required else None

    if question.type == "boolean":
        if not isinstance(value, bool):
            return "expected a boolean"
        return None

    if question.type == "integer":
        if isinstance(value, bool) or not isinstance(value, int):
            return "expected an integer"
        if question.min_value is not None and value < question.min_value:
            return f"must be at least {question.min_value}"
        if question.max_value is not None and value > question.max_value:
            return f"must be at most {question.max_value}"
        return None

    if question.type == "string":
        if not isinstance(value, str):
            return "expected a string"
        if question.min_length is not None and len(value) < question.min_length:
            return f"must be at least {question.min_length} characters"
        if question.max_length is not None and len(value) > question.max_length:
            return f"must be at most {question.max_length} characters"
        if question.required and value.strip() == "":
            return "answer is required"
        return None

    if question.type == "enum":
        if not isinstance(value, str):
            return "expected a string option"
        options = question.options or []
        if value not in options:
            return f"must be one of: {', '.join(options)}"
        return None

    if question.type == "date":
        if not isinstance(value, str):
            return "expected an ISO-8601 date string (YYYY-MM-DD)"
        try:
            date.fromisoformat(value)
        except ValueError:
            return "must be a valid ISO-8601 date (YYYY-MM-DD)"
        return None

    return "unsupported question type"


def prune_answers(questions: list[IntakeQuestion], answers: dict[str, Any]) -> dict[str, Any]:
    """Drop answers for questions that no longer apply after a branch change (US-02.5)."""
    kept: dict[str, Any] = {}
    for question in questions:
        if question.key not in answers:
            continue
        if is_visible(question, kept):
            kept[question.key] = answers[question.key]
    return kept


def progress_for(questions: list[IntakeQuestion], answers: dict[str, Any]) -> IntakeProgress:
    """Count answered vs visible questions for progress UI (US-02.4)."""
    visible = visible_questions(questions, answers)
    answered = sum(1 for q in visible if q.key in answers and answers[q.key] is not None)
    total = len(visible)
    return IntakeProgress(answered=answered, total=total, complete=total > 0 and answered == total)


def parse_questions(raw: list[dict[str, Any]] | list[IntakeQuestion]) -> list[IntakeQuestion]:
    """Normalize stored JSON (or models) into typed questions."""
    out: list[IntakeQuestion] = []
    for item in raw:
        q = item if isinstance(item, IntakeQuestion) else IntakeQuestion.model_validate(item)
        if q.type == "enum" and not q.options:
            raise ValueError(f"enum question '{q.key}' requires options")
        out.append(q)
    return out


TOP_COUNTRY_OPTIONS: list[str] = [
    "Japan",
    "United States",
    "United Kingdom",
    "Canada",
    "Australia",
    "Germany",
    "France",
    "Singapore",
    "South Korea",
    "United Arab Emirates",
    "New Zealand",
    "Netherlands",
    "Italy",
    "Spain",
    "Switzerland",
    "Ireland",
    "Thailand",
    "Malaysia",
    "India",
    "China",
]

# Authored in docs/jurisdictions/*.yml; re-exported for tests and legacy imports.
JP_WORK_RENEWAL_QUESTIONS: list[dict[str, Any]] = pack_questions("jp/work.renewal")
US_H1B_QUESTIONS: list[dict[str, Any]] = pack_questions("us/h1b.renewal")
JP_TOURIST_NEW_APPLICATION_QUESTIONS: list[dict[str, Any]] = pack_questions(
    "jp/tourist.new_application"
)
JP_STUDENT_NEW_APPLICATION_QUESTIONS: list[dict[str, Any]] = pack_questions(
    "jp/student.new_application"
)
