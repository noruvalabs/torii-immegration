"""add applicant-core workflow tables

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-27
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> tuple[sa.Column, sa.Column]:
    return (
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def _scope_columns() -> tuple[sa.Column, sa.Column, sa.Column]:
    return (
        sa.Column("jurisdiction_id", sa.Integer(), nullable=False),
        sa.Column("visa_category_id", sa.Integer(), nullable=False),
        sa.Column("case_action_id", sa.Integer(), nullable=False),
    )


def _scope_constraints(table: str) -> tuple[sa.ForeignKeyConstraint, ...]:
    return (
        sa.ForeignKeyConstraint(
            ["jurisdiction_id"],
            ["jurisdictions.id"],
            name=op.f(f"fk_{table}_jurisdiction_id_jurisdictions"),
        ),
        sa.ForeignKeyConstraint(
            ["visa_category_id"],
            ["visa_categories.id"],
            name=op.f(f"fk_{table}_visa_category_id_visa_categories"),
        ),
        sa.ForeignKeyConstraint(
            ["case_action_id"],
            ["case_actions.id"],
            name=op.f(f"fk_{table}_case_action_id_case_actions"),
        ),
    )


def _scope_indexes(table: str) -> None:
    for column in ("jurisdiction_id", "visa_category_id", "case_action_id"):
        op.create_index(op.f(f"ix_{table}_{column}"), table, [column], unique=False)


def upgrade() -> None:
    op.add_column(
        "jurisdictions",
        sa.Column("efile_enabled", sa.Boolean(), server_default="0", nullable=False),
    )
    op.add_column(
        "cases", sa.Column("locale", sa.String(length=16), server_default="en", nullable=False)
    )
    op.add_column(
        "cases", sa.Column("host_locale", sa.String(length=16), server_default="ja", nullable=False)
    )
    op.add_column(
        "cases",
        sa.Column("review_flags_acknowledged", sa.Boolean(), server_default="0", nullable=False),
    )
    op.add_column("cases", sa.Column("submission_reference", sa.String(length=128), nullable=True))
    op.add_column("cases", sa.Column("packet_snapshot", sa.JSON(), nullable=True))
    op.add_column("cases", sa.Column("eligibility_snapshot", sa.JSON(), nullable=True))

    op.create_table(
        "eligibility_rule_sets",
        sa.Column("id", sa.Integer(), nullable=False),
        *_scope_columns(),
        sa.Column("rules", sa.JSON(), nullable=False),
        sa.Column("is_live", sa.Boolean(), server_default="0", nullable=False),
        *_timestamps(),
        *_scope_constraints("eligibility_rule_sets"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_eligibility_rule_sets")),
    )
    _scope_indexes("eligibility_rule_sets")

    op.create_table(
        "document_requirement_sets",
        sa.Column("id", sa.Integer(), nullable=False),
        *_scope_columns(),
        sa.Column("items", sa.JSON(), nullable=False),
        sa.Column("is_live", sa.Boolean(), server_default="0", nullable=False),
        *_timestamps(),
        *_scope_constraints("document_requirement_sets"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_document_requirement_sets")),
    )
    _scope_indexes("document_requirement_sets")

    op.create_table(
        "form_templates",
        sa.Column("id", sa.Integer(), nullable=False),
        *_scope_columns(),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("is_live", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("official_title", sa.String(length=256), nullable=False),
        sa.Column("citation", sa.JSON(), nullable=False),
        sa.Column("field_mappings", sa.JSON(), nullable=False),
        *_timestamps(),
        *_scope_constraints("form_templates"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_form_templates")),
    )
    _scope_indexes("form_templates")
    op.create_index(op.f("ix_form_templates_code"), "form_templates", ["code"], unique=False)

    op.create_table(
        "case_documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.Integer(), nullable=False),
        sa.Column("doc_type", sa.String(length=64), nullable=False),
        sa.Column("filename", sa.String(length=256), nullable=False),
        sa.Column("storage_key", sa.String(length=512), nullable=False),
        sa.Column("extracted_fields", sa.JSON(), nullable=False),
        sa.Column("extraction_confidence", sa.Float(), nullable=True),
        sa.Column("confirmed", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["case_id"], ["cases.id"], name=op.f("fk_case_documents_case_id_cases")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_case_documents")),
    )
    op.create_index(op.f("ix_case_documents_case_id"), "case_documents", ["case_id"], unique=False)
    op.create_index(
        op.f("ix_case_documents_doc_type"), "case_documents", ["doc_type"], unique=False
    )

    op.create_table(
        "case_checklist_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("how_to_obtain", sa.Text(), nullable=False),
        sa.Column("why_required", sa.Text(), nullable=False),
        sa.Column("is_required", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("status", sa.String(length=16), server_default="needed", nullable=False),
        sa.Column("citation", sa.JSON(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["case_id"], ["cases.id"], name=op.f("fk_case_checklist_items_case_id_cases")
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["case_documents.id"],
            name=op.f("fk_case_checklist_items_document_id_case_documents"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_case_checklist_items")),
    )
    op.create_index(
        op.f("ix_case_checklist_items_case_id"), "case_checklist_items", ["case_id"], unique=False
    )
    op.create_index(
        op.f("ix_case_checklist_items_code"), "case_checklist_items", ["code"], unique=False
    )
    op.create_index(
        op.f("ix_case_checklist_items_document_id"),
        "case_checklist_items",
        ["document_id"],
        unique=False,
    )

    op.create_table(
        "case_generated_forms",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.Integer(), nullable=False),
        sa.Column("form_template_id", sa.Integer(), nullable=False),
        sa.Column("form_code", sa.String(length=64), nullable=False),
        sa.Column("form_version", sa.String(length=32), nullable=False),
        sa.Column("filled_fields", sa.JSON(), nullable=False),
        sa.Column("missing_required_fields", sa.JSON(), nullable=False),
        sa.Column("citation", sa.JSON(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["case_id"], ["cases.id"], name=op.f("fk_case_generated_forms_case_id_cases")
        ),
        sa.ForeignKeyConstraint(
            ["form_template_id"],
            ["form_templates.id"],
            name=op.f("fk_case_generated_forms_form_template_id_form_templates"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_case_generated_forms")),
    )
    op.create_index(
        op.f("ix_case_generated_forms_case_id"), "case_generated_forms", ["case_id"], unique=False
    )
    op.create_index(
        op.f("ix_case_generated_forms_form_template_id"),
        "case_generated_forms",
        ["form_template_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_case_generated_forms_form_code"),
        "case_generated_forms",
        ["form_code"],
        unique=False,
    )

    op.create_table(
        "case_escalations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=32), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("consent_to_share", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("status", sa.String(length=16), server_default="open", nullable=False),
        sa.Column("outcome", sa.Text(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["case_id"], ["cases.id"], name=op.f("fk_case_escalations_case_id_cases")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_case_escalations")),
    )
    op.create_index(
        op.f("ix_case_escalations_case_id"), "case_escalations", ["case_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_case_escalations_case_id"), table_name="case_escalations")
    op.drop_table("case_escalations")
    op.drop_index(op.f("ix_case_generated_forms_form_code"), table_name="case_generated_forms")
    op.drop_index(
        op.f("ix_case_generated_forms_form_template_id"), table_name="case_generated_forms"
    )
    op.drop_index(op.f("ix_case_generated_forms_case_id"), table_name="case_generated_forms")
    op.drop_table("case_generated_forms")
    op.drop_index(op.f("ix_case_checklist_items_document_id"), table_name="case_checklist_items")
    op.drop_index(op.f("ix_case_checklist_items_code"), table_name="case_checklist_items")
    op.drop_index(op.f("ix_case_checklist_items_case_id"), table_name="case_checklist_items")
    op.drop_table("case_checklist_items")
    op.drop_index(op.f("ix_case_documents_doc_type"), table_name="case_documents")
    op.drop_index(op.f("ix_case_documents_case_id"), table_name="case_documents")
    op.drop_table("case_documents")
    op.drop_index(op.f("ix_form_templates_code"), table_name="form_templates")
    for table in ("form_templates", "document_requirement_sets", "eligibility_rule_sets"):
        for column in ("case_action_id", "visa_category_id", "jurisdiction_id"):
            op.drop_index(op.f(f"ix_{table}_{column}"), table_name=table)
        op.drop_table(table)
    op.drop_column("cases", "eligibility_snapshot")
    op.drop_column("cases", "packet_snapshot")
    op.drop_column("cases", "submission_reference")
    op.drop_column("cases", "review_flags_acknowledged")
    op.drop_column("cases", "host_locale")
    op.drop_column("cases", "locale")
    op.drop_column("jurisdictions", "efile_enabled")
