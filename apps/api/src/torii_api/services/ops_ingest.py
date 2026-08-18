"""Ingest scraped immigration definitions and optionally auto-promote to live.

Used by the daily worker (Tavily path) so OPS does not need manual uploads for
beachhead JP/US scopes. Promotion requires citations and schema validation.
Failed scrapes never demote existing live definitions.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from torii_api.db.models import (
    CaseAction,
    DocumentRequirementSet,
    EligibilityRuleSet,
    FormTemplate,
    IntakeDefinition,
    Jurisdiction,
    OutboxEvent,
    VisaCategory,
)
from torii_api.services.content_packs import effective_window
from torii_api.services.intake import parse_questions

log = structlog.get_logger()

BEACHHEAD_SCOPES: list[tuple[str, str, str]] = [
    ("JP", "work", "renewal"),
    ("US", "h1b", "renewal"),
    ("US", "h1b", "new_application"),
]


def has_citation(item: dict[str, Any]) -> bool:
    citation = item.get("citation")
    if not isinstance(citation, dict):
        return False
    url = citation.get("url")
    return isinstance(url, str) and url.startswith("http")


def _has_valid_effective_window(item: dict[str, Any]) -> bool:
    """Reject malformed ``effective_from`` / ``effective_until`` dates (NF-2 gate).

    A window whose from-date is after its until-date is also invalid; ``from == until``
    is an empty window and therefore never applicable, so treat it as invalid too.
    """
    try:
        effective_from, effective_until = effective_window(item)
    except ValueError:
        return False
    if effective_from is not None and effective_until is not None:
        return effective_from < effective_until
    return True


def validated_for_promote(
    *,
    rules: list[dict[str, Any]],
    documents: list[dict[str, Any]],
    questions: list[dict[str, Any]],
) -> bool:
    """True when scraped payload is complete enough to go live without manual OPS."""
    if not rules or not documents or not questions:
        return False
    if not all(has_citation(rule) for rule in rules):
        return False
    if not all(has_citation(doc) for doc in documents):
        return False
    if not all(_has_valid_effective_window(item) for item in rules + documents):
        return False
    try:
        parse_questions(questions)
    except (TypeError, ValueError):
        return False
    return True


async def resolve_scope(
    session: AsyncSession,
    jurisdiction_code: str,
    visa_category: str,
    action: str,
) -> tuple[Jurisdiction, VisaCategory, CaseAction] | None:
    jurisdiction = await session.scalar(
        select(Jurisdiction).where(Jurisdiction.code == jurisdiction_code.upper())
    )
    if jurisdiction is None:
        return None
    vc = await session.scalar(
        select(VisaCategory).where(
            VisaCategory.jurisdiction_id == jurisdiction.id,
            VisaCategory.code == visa_category.lower(),
        )
    )
    ca = await session.scalar(
        select(CaseAction).where(
            CaseAction.jurisdiction_id == jurisdiction.id,
            CaseAction.code == action.lower(),
        )
    )
    if vc is None or ca is None:
        return None
    return jurisdiction, vc, ca


async def ingest_scrape_result(
    session: AsyncSession,
    *,
    jurisdiction_code: str,
    visa_category: str,
    action: str,
    eligibility_rules: list[dict[str, Any]],
    document_requirements: list[dict[str, Any]],
    intake_questions: list[dict[str, Any]],
    form_templates: list[dict[str, Any]],
    auto_promote: bool = True,
) -> dict[str, Any]:
    """Upsert definitions; promote to live only when validation passes.

    When validation fails, existing live rows are left untouched. New scopes
    without any row may still receive draft (``is_live=False``) content.
    """
    scope = await resolve_scope(session, jurisdiction_code, visa_category, action)
    if scope is None:
        return {"status": "skipped", "reason": "scope_not_found"}

    jurisdiction, vc, ca = scope
    promote = auto_promote and validated_for_promote(
        rules=eligibility_rules,
        documents=document_requirements,
        questions=intake_questions,
    )

    summary: dict[str, Any] = {
        "status": "ok",
        "promoted": promote,
        "eligibility": 0,
        "documents": 0,
        "intake": 0,
        "forms": 0,
    }

    async def _upsert_singleton(
        model: type[EligibilityRuleSet] | type[DocumentRequirementSet] | type[IntakeDefinition],
        *,
        field: str,
        value: Any,
        count_key: str,
        count: int,
    ) -> None:
        existing = await session.scalar(
            select(model).where(
                model.jurisdiction_id == jurisdiction.id,
                model.visa_category_id == vc.id,
                model.case_action_id == ca.id,
            )
        )
        if existing is not None:
            if not promote and existing.is_live:
                return
            setattr(existing, field, value)
            existing.is_live = promote
        else:
            session.add(
                model(
                    jurisdiction_id=jurisdiction.id,
                    visa_category_id=vc.id,
                    case_action_id=ca.id,
                    is_live=promote,
                    **{field: value},
                )
            )
        summary[count_key] = count

    if eligibility_rules:
        await _upsert_singleton(
            EligibilityRuleSet,
            field="rules",
            value=eligibility_rules,
            count_key="eligibility",
            count=len(eligibility_rules),
        )
    if document_requirements:
        await _upsert_singleton(
            DocumentRequirementSet,
            field="items",
            value=document_requirements,
            count_key="documents",
            count=len(document_requirements),
        )
    if intake_questions:
        await _upsert_singleton(
            IntakeDefinition,
            field="questions",
            value=intake_questions,
            count_key="intake",
            count=len(intake_questions),
        )

    for form in form_templates:
        code = str(form.get("code") or "")
        if not code:
            continue
        existing = await session.scalar(
            select(FormTemplate).where(
                FormTemplate.jurisdiction_id == jurisdiction.id,
                FormTemplate.visa_category_id == vc.id,
                FormTemplate.case_action_id == ca.id,
                FormTemplate.code == code,
            )
        )
        form_live = promote and has_citation(form)
        values = {
            "version": str(form.get("version") or datetime.now(UTC).strftime("%Y-%m")),
            "official_title": str(form.get("official_title") or code),
            "citation": dict(form.get("citation") or {}),
            "field_mappings": list(form.get("field_mappings") or []),
            "is_live": form_live,
        }
        if existing is not None:
            if not form_live and existing.is_live:
                continue
            for key, value in values.items():
                setattr(existing, key, value)
        else:
            session.add(
                FormTemplate(
                    jurisdiction_id=jurisdiction.id,
                    visa_category_id=vc.id,
                    case_action_id=ca.id,
                    code=code,
                    **values,
                )
            )
        summary["forms"] += 1

    if promote:
        session.add(
            OutboxEvent(
                topic="ops.definitions.promoted",
                payload={
                    "jurisdiction_code": jurisdiction_code.upper(),
                    "visa_category": visa_category.lower(),
                    "action": action.lower(),
                    "promoted_at": datetime.now(UTC).isoformat(),
                    "eligibility": summary["eligibility"],
                    "documents": summary["documents"],
                    "intake": summary["intake"],
                    "forms": summary["forms"],
                },
            )
        )

    await session.flush()
    log.info(
        "ops.ingest.stored",
        jurisdiction=jurisdiction_code,
        visa_category=visa_category,
        action=action,
        promoted=promote,
    )
    return summary
