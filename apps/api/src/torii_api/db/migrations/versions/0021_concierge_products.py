"""Add concierge_products and concierge_orders tables for Document Concierge (Thing 2).

Revision ID: 0021
Revises: 0020
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0021"
down_revision: str | None = "0020"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing_tables = insp.get_table_names()

    if "concierge_products" not in existing_tables:
        op.create_table(
            "concierge_products",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("code", sa.String(64), nullable=False),
            sa.Column("name", sa.String(256), nullable=False),
            sa.Column("description", sa.Text(), server_default="", nullable=False),
            sa.Column("product_type", sa.String(32), nullable=False),
            sa.Column("price_cents", sa.Integer(), server_default="0", nullable=False),
            sa.Column("currency", sa.String(8), server_default="USD", nullable=False),
            sa.Column("checklist_code_pattern", sa.String(512), server_default="", nullable=False),
            sa.Column("is_active", sa.Boolean(), server_default="1", nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint("code", name="uq_concierge_products_code"),
        )
        op.create_index("ix_concierge_products_code", "concierge_products", ["code"])
        op.create_index(
            "ix_concierge_products_product_type", "concierge_products", ["product_type"]
        )

    if "concierge_orders" not in existing_tables:
        op.create_table(
            "concierge_orders",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("case_id", sa.Integer(), sa.ForeignKey("cases.id"), nullable=False),
            sa.Column(
                "checklist_item_id",
                sa.Integer(),
                sa.ForeignKey("case_checklist_items.id"),
                nullable=False,
            ),
            sa.Column(
                "product_id",
                sa.Integer(),
                sa.ForeignKey("concierge_products.id"),
                nullable=False,
            ),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("price_cents", sa.Integer(), server_default="0", nullable=False),
            sa.Column("currency", sa.String(8), server_default="USD", nullable=False),
            sa.Column("status", sa.String(16), server_default="pending", nullable=False),
            sa.Column(
                "fulfilled_document_id",
                sa.Integer(),
                sa.ForeignKey("case_documents.id"),
                nullable=True,
            ),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_concierge_orders_case_id", "concierge_orders", ["case_id"])
        op.create_index(
            "ix_concierge_orders_checklist_item_id", "concierge_orders", ["checklist_item_id"]
        )
        op.create_index("ix_concierge_orders_product_id", "concierge_orders", ["product_id"])
        op.create_index("ix_concierge_orders_user_id", "concierge_orders", ["user_id"])

    # Seed the five initial concierge products
    products_table = sa.table(
        "concierge_products",
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("description", sa.Text),
        sa.column("product_type", sa.String),
        sa.column("price_cents", sa.Integer),
        sa.column("currency", sa.String),
        sa.column("checklist_code_pattern", sa.String),
        sa.column("is_active", sa.Boolean),
    )
    op.bulk_insert(
        products_table,
        [
            {
                "code": "dummy_flight",
                "name": "Dummy Flight Reservation",
                "description": "A verifiable flight reservation PDF valid for 14 days — accepted by all major consulates. No actual ticket purchase needed.",
                "product_type": "dummy_flight",
                "price_cents": 1200,
                "currency": "USD",
                "checklist_code_pattern": "flight,itinerary,booking,travel_itinerary,flight_reservation,flight_booking",
                "is_active": True,
            },
            {
                "code": "travel_insurance",
                "name": "Travel Insurance Certificate",
                "description": "Travel medical insurance certificate covering your trip dates with minimum required coverage. Instant PDF delivery.",
                "product_type": "travel_insurance",
                "price_cents": 1500,
                "currency": "USD",
                "checklist_code_pattern": "insurance,travel_insurance,medical_insurance,health_insurance",
                "is_active": True,
            },
            {
                "code": "doctor_referral",
                "name": "Doctor Referral Letter",
                "description": "AI-generated medical referral letter template customised to your visa requirements. Review and get signed by your physician.",
                "product_type": "doctor_referral",
                "price_cents": 1900,
                "currency": "USD",
                "checklist_code_pattern": "referral,doctor,medical_referral,doctor_letter,medical_letter",
                "is_active": True,
            },
            {
                "code": "hotel_reservation",
                "name": "Hotel Confirmation Letter",
                "description": "Free hotel confirmation letter via our Booking.com partner. Shows proof of accommodation for your visa application.",
                "product_type": "hotel_reservation",
                "price_cents": 0,
                "currency": "USD",
                "checklist_code_pattern": "hotel,accommodation,hotel_booking,hotel_reservation,lodging",
                "is_active": True,
            },
            {
                "code": "invitation_letter",
                "name": "Invitation Letter",
                "description": "AI-generated invitation letter from your host, formatted to meet consulate requirements. Editable before download.",
                "product_type": "invitation_letter",
                "price_cents": 1400,
                "currency": "USD",
                "checklist_code_pattern": "invitation,host_letter,invitation_letter,sponsor_letter",
                "is_active": True,
            },
        ],
    )


def downgrade() -> None:
    op.drop_table("concierge_orders")
    op.drop_table("concierge_products")
