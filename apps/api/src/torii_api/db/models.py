"""Core system-of-record tables.

A deliberately small seed of the domain (docs/specs/01_domain.md) — enough to prove the
persistence, migration, and background-work seams end to end, and the anchor the rest of the
case pipeline grows from:

* :class:`User` — an account (applicant, staff, admin) with secure credentials (US-20, US-30).
* :class:`Jurisdiction` — a configured country/market; only ``is_live`` ones are offered in
  onboarding (US-01.3, US-29.3).
* :class:`Case` — one row in the single canonical case pipeline, whatever channel it arrived
  through; carries the status lifecycle, intake progress for save/resume (US-03), and the
  renewal date that drives reminders (US-19).
* :class:`IntakeDefinition` — branching questionnaire for a jurisdiction/category/action scope
  (US-02); the AI service asks the API which questions apply and posts validated answers here.
* :class:`OutboxEvent` — the transactional outbox (architecture seam 2): the API writes an
  event in the same transaction as the business change; the arq worker drains it at-least-once.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import JSON as SAJSON
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from torii_api.db.base import Base, TimestampMixin


class UserRole(StrEnum):
    """Least-privilege roles for applicants and back-office staff (US-30)."""

    APPLICANT = "applicant"
    OPS = "ops"
    EMPLOYER = "employer"
    ADMIN = "admin"


class User(TimestampMixin, Base):
    """A platform account — applicant by default on self-registration (US-20.1)."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64), unique=True, index=True, nullable=True)
    password_hash: Mapped[str] = mapped_column(String(128))
    role: Mapped[str] = mapped_column(
        String(32), default=UserRole.APPLICANT, server_default=UserRole.APPLICANT
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    email_verification_token: Mapped[str | None] = mapped_column(
        String(128), unique=True, index=True, nullable=True
    )
    password_reset_token: Mapped[str | None] = mapped_column(
        String(128), unique=True, index=True, nullable=True
    )
    password_reset_expires: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    cases: Mapped[list[Case]] = relationship(back_populates="owner")


class Jurisdiction(TimestampMixin, Base):
    """A configured country/market and whether it is live for applicants."""

    __tablename__ = "jurisdictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # ISO-3166 alpha-2 (e.g. "JP"), unique. The stable handle a case scopes to.
    code: Mapped[str] = mapped_column(String(8), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    is_live: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")

    cases: Mapped[list[Case]] = relationship(back_populates="jurisdiction")
    visa_categories: Mapped[list[VisaCategory]] = relationship(back_populates="jurisdiction")
    case_actions: Mapped[list[CaseAction]] = relationship(back_populates="jurisdiction")
    intake_definitions: Mapped[list[IntakeDefinition]] = relationship(back_populates="jurisdiction")


class VisaCategory(TimestampMixin, Base):
    """A visa category scoped to a jurisdiction (e.g. "work", "student" in JP)."""

    __tablename__ = "visa_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    jurisdiction_id: Mapped[int] = mapped_column(ForeignKey("jurisdictions.id"), index=True)
    code: Mapped[str] = mapped_column(String(32), index=True)
    name: Mapped[str] = mapped_column(String(128))
    is_live: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")

    jurisdiction: Mapped[Jurisdiction] = relationship(back_populates="visa_categories")
    cases: Mapped[list[Case]] = relationship(back_populates="visa_category")
    intake_definitions: Mapped[list[IntakeDefinition]] = relationship(
        back_populates="visa_category"
    )


class CaseAction(TimestampMixin, Base):
    """An action type scoped to a jurisdiction (e.g. "renewal", "new_application" in JP)."""

    __tablename__ = "case_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    jurisdiction_id: Mapped[int] = mapped_column(ForeignKey("jurisdictions.id"), index=True)
    code: Mapped[str] = mapped_column(String(32), index=True)
    name: Mapped[str] = mapped_column(String(128))
    is_live: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")

    jurisdiction: Mapped[Jurisdiction] = relationship(back_populates="case_actions")
    cases: Mapped[list[Case]] = relationship(back_populates="case_action")
    intake_definitions: Mapped[list[IntakeDefinition]] = relationship(back_populates="case_action")


class IntakeDefinition(TimestampMixin, Base):
    """Branching intake questionnaire for one live scope (US-02)."""

    __tablename__ = "intake_definitions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    jurisdiction_id: Mapped[int] = mapped_column(ForeignKey("jurisdictions.id"), index=True)
    visa_category_id: Mapped[int] = mapped_column(ForeignKey("visa_categories.id"), index=True)
    case_action_id: Mapped[int] = mapped_column(ForeignKey("case_actions.id"), index=True)
    # Ordered list of question objects — see torii_api.services.intake.IntakeQuestion.
    questions: Mapped[list[dict[str, Any]]] = mapped_column(SAJSON, default=list)
    is_live: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")

    jurisdiction: Mapped[Jurisdiction] = relationship(back_populates="intake_definitions")
    visa_category: Mapped[VisaCategory] = relationship(back_populates="intake_definitions")
    case_action: Mapped[CaseAction] = relationship(back_populates="intake_definitions")


class Case(TimestampMixin, Base):
    """One case in the canonical pipeline — one status lifecycle, one history."""

    __tablename__ = "cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Human-facing reference (e.g. "JP-2026-000123"), unique across the platform.
    reference: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    jurisdiction_id: Mapped[int] = mapped_column(ForeignKey("jurisdictions.id"), index=True)
    visa_category_id: Mapped[int | None] = mapped_column(
        ForeignKey("visa_categories.id"), nullable=True, index=True
    )
    case_action_id: Mapped[int | None] = mapped_column(
        ForeignKey("case_actions.id"), nullable=True, index=True
    )
    # Signed-in owner; NULL for anonymous / employer-initiated cases not yet claimed (US-03).
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    # Status lifecycle string kept open here; the enum/state-machine lands with the pipeline.
    status: Mapped[str] = mapped_column(String(32), default="draft", server_default="draft")
    applicant_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    # Intake progress so an applicant can stop and resume (US-03.1, US-03.2).
    intake_answers: Mapped[dict] = mapped_column(SAJSON, default=dict)
    # Stable key for the applicant's current position in the intake flow; NULL before intake.
    intake_step: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # Recorded expiry/renewal date for a completed case (US-19.1); NULL until known.
    renewal_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    jurisdiction: Mapped[Jurisdiction] = relationship(back_populates="cases")
    visa_category: Mapped[VisaCategory | None] = relationship(back_populates="cases")
    case_action: Mapped[CaseAction | None] = relationship(back_populates="cases")
    owner: Mapped[User | None] = relationship(back_populates="cases")


class OutboxEvent(TimestampMixin, Base):
    """Transactional outbox — written with the business change, drained by the worker."""

    __tablename__ = "outbox_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # e.g. "renewal.due", "source.changed", "case.escalated".
    topic: Mapped[str] = mapped_column(String(64), index=True)
    # JSON on Postgres, JSON-as-text on SQLite — portable across both engines.
    payload: Mapped[dict] = mapped_column(SAJSON, default=dict)
    # NULL while pending; stamped when the worker has handled it (at-least-once).
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
