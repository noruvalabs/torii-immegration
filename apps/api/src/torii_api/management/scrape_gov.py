"""Management command: scrape government immigration sources and update the database.

Usage::

    uv run python -m torii_api.management.scrape_gov

Scrapes Japan ISA and USA USCIS websites, extracts structured immigration data,
and stores it as draft records in the database for human review.
"""

from __future__ import annotations

import asyncio

from sqlalchemy import select

from torii_api.config import get_settings
from torii_api.db.base import Base
from torii_api.db.engine import create_engine, create_session_factory, to_async_url
from torii_api.db.models import (
    CaseAction,
    DocumentRequirementSet,
    EligibilityRuleSet,
    IntakeDefinition,
    Jurisdiction,
    VisaCategory,
)
from torii_api.services.gov_scraper import scrape_all


async def run() -> None:
    settings = get_settings()
    engine = create_engine(to_async_url(settings.database_url))
    session_factory = create_session_factory(engine)

    # Ensure tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Run scraper
    jurisdictions = [j.strip() for j in settings.scrape_jurisdictions.split(",") if j.strip()]
    print(f"Scraping jurisdictions: {', '.join(jurisdictions)}")
    results = await scrape_all(jurisdictions)

    async with session_factory() as session:
        stored_counts = {"eligibility": 0, "documents": 0, "intake": 0}

        for code, result in results.items():
            print(f"\n{'=' * 60}")
            print(f"  {code}: {len(result.source_pages)} pages scraped")
            print(f"  Visa categories found: {len(result.visa_categories)}")
            print(f"  Document sets: {len(result.document_requirements)}")
            print(f"  Eligibility rule sets: {len(result.eligibility_rules)}")
            print(f"  Errors: {len(result.errors)}")
            print(f"{'=' * 60}")

            # Resolve jurisdiction
            jurisdiction = await session.scalar(
                select(Jurisdiction).where(Jurisdiction.code == code)
            )
            if jurisdiction is None:
                print(f"  WARNING: Jurisdiction '{code}' not found in DB. Skipping.")
                continue

            # ── Store visa categories (as metadata on existing categories) ──────
            for vc_data in result.visa_categories:
                code_vc = vc_data.get("code", "")
                name = vc_data.get("name_en", vc_data.get("name", ""))
                if not code_vc or not name:
                    continue

                # Check if visa category already exists
                existing = await session.scalar(
                    select(VisaCategory).where(
                        VisaCategory.jurisdiction_id == jurisdiction.id,
                        VisaCategory.code == code_vc,
                    )
                )
                if existing is None:
                    session.add(
                        VisaCategory(
                            jurisdiction_id=jurisdiction.id,
                            code=code_vc,
                            name=name,
                            is_live=False,  # Draft — requires review
                        )
                    )
                    print(f"  + Visa category: {code_vc} ({name})")

            # ── Store eligibility rules ────────────────────────────────────────
            for action_code, rules in result.eligibility_rules.items():
                if not rules:
                    continue

                # Find or create visa category for "work" (default)
                vc = await session.scalar(
                    select(VisaCategory).where(
                        VisaCategory.jurisdiction_id == jurisdiction.id,
                        VisaCategory.code == "work",
                    )
                )
                if vc is None:
                    # Use the first available category
                    vc = await session.scalar(
                        select(VisaCategory).where(VisaCategory.jurisdiction_id == jurisdiction.id)
                    )
                if vc is None:
                    print(f"  WARNING: No visa categories for {code}. Skipping eligibility rules.")
                    continue

                # Find or create case action
                ca = await session.scalar(
                    select(CaseAction).where(
                        CaseAction.jurisdiction_id == jurisdiction.id,
                        CaseAction.code == action_code,
                    )
                )
                if ca is None:
                    ca = await session.scalar(
                        select(CaseAction).where(CaseAction.jurisdiction_id == jurisdiction.id)
                    )
                if ca is None:
                    print(f"  WARNING: No case actions for {code}. Skipping eligibility rules.")
                    continue

                existing = await session.scalar(
                    select(EligibilityRuleSet).where(
                        EligibilityRuleSet.jurisdiction_id == jurisdiction.id,
                        EligibilityRuleSet.visa_category_id == vc.id,
                        EligibilityRuleSet.case_action_id == ca.id,
                    )
                )
                if existing:
                    existing.rules = rules
                    existing.is_live = False
                    print(
                        f"  ~ Updated eligibility rules for {vc.code}/{ca.code}: {len(rules)} rules"
                    )
                else:
                    session.add(
                        EligibilityRuleSet(
                            jurisdiction_id=jurisdiction.id,
                            visa_category_id=vc.id,
                            case_action_id=ca.id,
                            rules=rules,
                            is_live=False,
                        )
                    )
                    print(f"  + Eligibility rules for {vc.code}/{ca.code}: {len(rules)} rules")
                stored_counts["eligibility"] += 1

            # ── Store document requirements ────────────────────────────────────
            for action_code, documents in result.document_requirements.items():
                if not documents:
                    continue

                vc = await session.scalar(
                    select(VisaCategory).where(
                        VisaCategory.jurisdiction_id == jurisdiction.id,
                        VisaCategory.code == "work",
                    )
                )
                if vc is None:
                    vc = await session.scalar(
                        select(VisaCategory).where(VisaCategory.jurisdiction_id == jurisdiction.id)
                    )
                if vc is None:
                    continue

                ca = await session.scalar(
                    select(CaseAction).where(
                        CaseAction.jurisdiction_id == jurisdiction.id,
                        CaseAction.code == action_code,
                    )
                )
                if ca is None:
                    ca = await session.scalar(
                        select(CaseAction).where(CaseAction.jurisdiction_id == jurisdiction.id)
                    )
                if ca is None:
                    continue

                existing = await session.scalar(
                    select(DocumentRequirementSet).where(
                        DocumentRequirementSet.jurisdiction_id == jurisdiction.id,
                        DocumentRequirementSet.visa_category_id == vc.id,
                        DocumentRequirementSet.case_action_id == ca.id,
                    )
                )
                if existing:
                    existing.items = documents
                    existing.is_live = False
                    print(
                        f"  ~ Updated document requirements for {vc.code}/{ca.code}: {len(documents)} items"
                    )
                else:
                    session.add(
                        DocumentRequirementSet(
                            jurisdiction_id=jurisdiction.id,
                            visa_category_id=vc.id,
                            case_action_id=ca.id,
                            items=documents,
                            is_live=False,
                        )
                    )
                    print(
                        f"  + Document requirements for {vc.code}/{ca.code}: {len(documents)} items"
                    )
                stored_counts["documents"] += 1

            # ── Store intake questions (basic from scraped data) ────────────────
            # Build intake questions from eligibility rules + document requirements
            intake_questions = _build_intake_questions(result)
            if intake_questions:
                vc = await session.scalar(
                    select(VisaCategory).where(
                        VisaCategory.jurisdiction_id == jurisdiction.id,
                        VisaCategory.code == "work",
                    )
                )
                if vc is None:
                    vc = await session.scalar(
                        select(VisaCategory).where(VisaCategory.jurisdiction_id == jurisdiction.id)
                    )
                if vc is None:
                    continue

                # Use first action
                ca = await session.scalar(
                    select(CaseAction).where(CaseAction.jurisdiction_id == jurisdiction.id)
                )
                if ca is None:
                    continue

                existing = await session.scalar(
                    select(IntakeDefinition).where(
                        IntakeDefinition.jurisdiction_id == jurisdiction.id,
                        IntakeDefinition.visa_category_id == vc.id,
                        IntakeDefinition.case_action_id == ca.id,
                    )
                )
                if existing:
                    existing.questions = intake_questions
                    existing.is_live = False
                    print(
                        f"  ~ Updated intake questions for {vc.code}/{ca.code}: {len(intake_questions)} questions"
                    )
                else:
                    session.add(
                        IntakeDefinition(
                            jurisdiction_id=jurisdiction.id,
                            visa_category_id=vc.id,
                            case_action_id=ca.id,
                            questions=intake_questions,
                            is_live=False,
                        )
                    )
                    print(
                        f"  + Intake questions for {vc.code}/{ca.code}: {len(intake_questions)} questions"
                    )
                stored_counts["intake"] += 1

        await session.commit()

    await engine.dispose()
    print(f"\n{'=' * 60}")
    print(f"  DONE — stored {stored_counts['eligibility']} eligibility rule sets,")
    print(f"          {stored_counts['documents']} document requirement sets,")
    print(f"          {stored_counts['intake']} intake definitions")
    print("  All records are DRAFT (is_live=False). Review and approve via admin.")
    print(f"{'=' * 60}")


def _build_intake_questions(result) -> list[dict]:
    """Build intake questionnaire from scraped data."""
    questions = []

    # Basic questions every applicant needs to answer
    questions.append(
        {
            "key": "nationality",
            "kind": "text",
            "label": "What is your nationality?",
            "hint": "Country of citizenship",
            "required": True,
        }
    )

    questions.append(
        {
            "key": "current_status",
            "kind": "select",
            "label": "What is your current immigration status?",
            "options": [
                {"value": vc["code"], "label": vc.get("name_en", vc["code"])}
                for vc in result.visa_categories
                if vc.get("code") and not vc["code"].startswith("gc_")
            ][:10],  # Limit options
            "required": True,
        }
    )

    questions.append(
        {
            "key": "purpose",
            "kind": "select",
            "label": "What do you need to do?",
            "options": [
                {"value": "renewal", "label": "Renew/extend current status"},
                {"value": "change_status", "label": "Change to a different status"},
                {"value": "new_application", "label": "New visa application"},
            ],
            "required": True,
        }
    )

    questions.append(
        {
            "key": "has_passport",
            "kind": "bool",
            "label": "Do you have a valid passport?",
            "required": True,
        }
    )

    questions.append(
        {
            "key": "has_residence_card",
            "kind": "bool",
            "label": "Do you currently hold a residence card or visa?",
            "required": True,
        }
    )

    questions.append(
        {
            "key": "employment_status",
            "kind": "select",
            "label": "What is your current employment situation?",
            "options": [
                {"value": "employed", "label": "Employed"},
                {"value": "self_employed", "label": "Self-employed"},
                {"value": "student", "label": "Student"},
                {"value": "unemployed", "label": "Not currently employed"},
                {"value": "retired", "label": "Retired"},
            ],
            "required": True,
        }
    )

    if result.jurisdiction_code == "JP":
        questions.append(
            {
                "key": "years_in_japan",
                "kind": "number",
                "label": "How many years have you lived in Japan?",
                "hint": "Whole years",
                "required": True,
            }
        )
    elif result.jurisdiction_code == "US":
        questions.append(
            {
                "key": "entry_date",
                "kind": "date",
                "label": "When did you last enter the United States?",
                "required": True,
            }
        )

    questions.append(
        {
            "key": "has_criminal_record",
            "kind": "bool",
            "label": "Do you have any criminal convictions?",
            "required": True,
        }
    )

    questions.append(
        {
            "key": "additional_info",
            "kind": "text",
            "label": "Is there anything else we should know about your situation?",
            "hint": "Optional — any special circumstances or concerns",
            "required": False,
        }
    )

    return questions


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
