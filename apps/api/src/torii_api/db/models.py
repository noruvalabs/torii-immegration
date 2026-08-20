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
from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from torii_api.db.base import Base, TimestampMixin, UTCDateTime


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
    password_reset_expires: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)

    # ── Profile fields (auto-fill for intake) ──────────────────────────────
    full_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    nationality: Mapped[str | None] = mapped_column(String(100), nullable=True)
    passport_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    passport_expiry: Mapped[str | None] = mapped_column(String(16), nullable=True)
    date_of_birth: Mapped[str | None] = mapped_column(String(16), nullable=True)
    current_country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    profile_complete: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    credit_balance: Mapped[int] = mapped_column(Integer, default=10, server_default="10")

    cases: Mapped[list[Case]] = relationship(back_populates="owner")
    credit_transactions: Mapped[list[CreditTransaction]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Jurisdiction(TimestampMixin, Base):
    """A configured country/market and whether it is live for applicants."""

    __tablename__ = "jurisdictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # ISO-3166 alpha-2 (e.g. "JP"), unique. The stable handle a case scopes to.
    code: Mapped[str] = mapped_column(String(8), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    is_live: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    efile_enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")

    cases: Mapped[list[Case]] = relationship(back_populates="jurisdiction")
    visa_categories: Mapped[list[VisaCategory]] = relationship(back_populates="jurisdiction")
    case_actions: Mapped[list[CaseAction]] = relationship(back_populates="jurisdiction")
    intake_definitions: Mapped[list[IntakeDefinition]] = relationship(back_populates="jurisdiction")
    eligibility_rule_sets: Mapped[list[EligibilityRuleSet]] = relationship(
        back_populates="jurisdiction"
    )
    document_requirement_sets: Mapped[list[DocumentRequirementSet]] = relationship(
        back_populates="jurisdiction"
    )
    form_templates: Mapped[list[FormTemplate]] = relationship(back_populates="jurisdiction")


class VisaCategory(TimestampMixin, Base):
    """A visa category scoped to a jurisdiction (e.g. "work", "student" in JP)."""

    __tablename__ = "visa_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    jurisdiction_id: Mapped[int] = mapped_column(ForeignKey("jurisdictions.id"), index=True)
    code: Mapped[str] = mapped_column(String(32), index=True)
    name: Mapped[str] = mapped_column(String(128))
    is_live: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    # True when a scope with no seeded content pack can still be offered, with
    # requirements produced on demand by the live-research pipeline (NF-2 gated).
    research_enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")

    jurisdiction: Mapped[Jurisdiction] = relationship(back_populates="visa_categories")
    cases: Mapped[list[Case]] = relationship(back_populates="visa_category")
    intake_definitions: Mapped[list[IntakeDefinition]] = relationship(
        back_populates="visa_category"
    )
    eligibility_rule_sets: Mapped[list[EligibilityRuleSet]] = relationship(
        back_populates="visa_category"
    )
    document_requirement_sets: Mapped[list[DocumentRequirementSet]] = relationship(
        back_populates="visa_category"
    )
    form_templates: Mapped[list[FormTemplate]] = relationship(back_populates="visa_category")


class CaseAction(TimestampMixin, Base):
    """An action type scoped to a jurisdiction (e.g. "renewal", "new_application" in JP)."""

    __tablename__ = "case_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    jurisdiction_id: Mapped[int] = mapped_column(ForeignKey("jurisdictions.id"), index=True)
    code: Mapped[str] = mapped_column(String(32), index=True)
    name: Mapped[str] = mapped_column(String(128))
    is_live: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    research_enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")

    jurisdiction: Mapped[Jurisdiction] = relationship(back_populates="case_actions")
    cases: Mapped[list[Case]] = relationship(back_populates="case_action")
    intake_definitions: Mapped[list[IntakeDefinition]] = relationship(back_populates="case_action")
    eligibility_rule_sets: Mapped[list[EligibilityRuleSet]] = relationship(
        back_populates="case_action"
    )
    document_requirement_sets: Mapped[list[DocumentRequirementSet]] = relationship(
        back_populates="case_action"
    )
    form_templates: Mapped[list[FormTemplate]] = relationship(back_populates="case_action")


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


class EligibilityRuleSet(TimestampMixin, Base):
    """Deterministic eligibility screening rules for one case scope."""

    __tablename__ = "eligibility_rule_sets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    jurisdiction_id: Mapped[int] = mapped_column(ForeignKey("jurisdictions.id"), index=True)
    visa_category_id: Mapped[int] = mapped_column(ForeignKey("visa_categories.id"), index=True)
    case_action_id: Mapped[int] = mapped_column(ForeignKey("case_actions.id"), index=True)
    rules: Mapped[list[dict[str, Any]]] = mapped_column(SAJSON, default=list)
    is_live: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")

    jurisdiction: Mapped[Jurisdiction] = relationship(back_populates="eligibility_rule_sets")
    visa_category: Mapped[VisaCategory] = relationship(back_populates="eligibility_rule_sets")
    case_action: Mapped[CaseAction] = relationship(back_populates="eligibility_rule_sets")


class DocumentRequirementSet(TimestampMixin, Base):
    """Checklist definition for one case scope."""

    __tablename__ = "document_requirement_sets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    jurisdiction_id: Mapped[int] = mapped_column(ForeignKey("jurisdictions.id"), index=True)
    visa_category_id: Mapped[int] = mapped_column(ForeignKey("visa_categories.id"), index=True)
    case_action_id: Mapped[int] = mapped_column(ForeignKey("case_actions.id"), index=True)
    items: Mapped[list[dict[str, Any]]] = mapped_column(SAJSON, default=list)
    is_live: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")

    jurisdiction: Mapped[Jurisdiction] = relationship(back_populates="document_requirement_sets")
    visa_category: Mapped[VisaCategory] = relationship(back_populates="document_requirement_sets")
    case_action: Mapped[CaseAction] = relationship(back_populates="document_requirement_sets")


class FormTemplate(TimestampMixin, Base):
    """Versioned official form definition and explicit intake field mappings."""

    __tablename__ = "form_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    jurisdiction_id: Mapped[int] = mapped_column(ForeignKey("jurisdictions.id"), index=True)
    visa_category_id: Mapped[int] = mapped_column(ForeignKey("visa_categories.id"), index=True)
    case_action_id: Mapped[int] = mapped_column(ForeignKey("case_actions.id"), index=True)
    code: Mapped[str] = mapped_column(String(64), index=True)
    version: Mapped[str] = mapped_column(String(32))
    is_live: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    official_title: Mapped[str] = mapped_column(String(256))
    citation: Mapped[dict[str, Any]] = mapped_column(SAJSON, default=dict)
    field_mappings: Mapped[list[dict[str, Any]]] = mapped_column(SAJSON, default=list)

    jurisdiction: Mapped[Jurisdiction] = relationship(back_populates="form_templates")
    visa_category: Mapped[VisaCategory] = relationship(back_populates="form_templates")
    case_action: Mapped[CaseAction] = relationship(back_populates="form_templates")
    generated_forms: Mapped[list[CaseGeneratedForm]] = relationship(back_populates="form_template")


class ScopeResearchStatus(StrEnum):
    """Lifecycle of an on-demand research run for a case scope."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ScopeResearch(TimestampMixin, Base):
    """Cached citation-gated workflow content discovered live for one case scope.

    Produced on demand by the live-research pipeline (``case.research.queued`` outbox event →
    ``POST /ai/ops/scrape`` → ``ops_ingest.validated_for_promote``) when a scope has no live
    content pack. One row per (scope + origin_country + residence_country) so the next same-scope
    case is instant until ``expires_at``. ``payload`` mirrors the seeded definition tables
    (``intake_definitions`` / ``eligibility_rule_sets`` / ``document_requirement_sets`` /
    ``form_templates``) so the deterministic engine consumes it identically; global live rules are
    never mutated here (NF-9).
    """

    __tablename__ = "scope_research"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    jurisdiction_id: Mapped[int] = mapped_column(ForeignKey("jurisdictions.id"), index=True)
    visa_category_id: Mapped[int] = mapped_column(ForeignKey("visa_categories.id"), index=True)
    case_action_id: Mapped[int] = mapped_column(ForeignKey("case_actions.id"), index=True)
    origin_country: Mapped[str | None] = mapped_column(String(8), nullable=True)
    residence_country: Mapped[str | None] = mapped_column(String(8), nullable=True)
    status: Mapped[str] = mapped_column(
        String(16), default=ScopeResearchStatus.QUEUED, server_default=ScopeResearchStatus.QUEUED
    )
    # One object keyed like the seeded definitions: {intake_questions, eligibility_rules,
    # document_requirements, form_templates}. Only meaningful when status == "completed".
    payload: Mapped[dict[str, Any]] = mapped_column(SAJSON, default=dict)
    source_pages: Mapped[list[dict[str, Any]]] = mapped_column(SAJSON, default=list)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    researched_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)

    jurisdiction: Mapped[Jurisdiction] = relationship()
    visa_category: Mapped[VisaCategory] = relationship()
    case_action: Mapped[CaseAction] = relationship()


class CaseStageResearch(TimestampMixin, Base):
    """Cached, citation-gated agentic research for one pipeline stage (docs/plan/03).

    Replaces pack/DB-first content resolution: ``admissibility``, ``intake``, ``eligibility``,
    ``documents``, and ``forms`` are each researched live (search + LLM extraction) rather than
    read from seeded definition tables, for every scope. ``admissibility`` may run **before** a
    case exists — keyed by ``scope_key`` (destination+purpose+action+nationality+residence) and
    shared across applicants on the same corridor. The other four stages are per-case only
    (keyed by ``case_id`` + ``stage``), because their queries are seeded with this applicant's
    own answers and prior stage results, not just the scope.
    """

    __tablename__ = "case_stage_research"
    __table_args__ = (
        UniqueConstraint("case_id", "stage", name="uq_case_stage_research_case"),
        UniqueConstraint("scope_key", "stage", name="uq_case_stage_research_scope"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int | None] = mapped_column(ForeignKey("cases.id"), nullable=True, index=True)
    stage: Mapped[str] = mapped_column(String(16), index=True)
    # NULL for per-case stages (case_id is the dedup key there); set only for the pre-case
    # "admissibility" stage, e.g. "JP|tourist|new_application|BD|BD".
    scope_key: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    status: Mapped[str] = mapped_column(
        String(16), default=ScopeResearchStatus.QUEUED, server_default=ScopeResearchStatus.QUEUED
    )
    payload: Mapped[dict[str, Any]] = mapped_column(SAJSON, default=dict)
    source_pages: Mapped[list[dict[str, Any]]] = mapped_column(SAJSON, default=list)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    researched_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)

    case: Mapped[Case | None] = relationship(back_populates="stage_research")


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
    locale: Mapped[str] = mapped_column(String(16), default="en", server_default="en")
    host_locale: Mapped[str] = mapped_column(String(16), default="ja", server_default="ja")
    review_flags_acknowledged: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="0"
    )
    submission_reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    packet_snapshot: Mapped[dict[str, Any] | None] = mapped_column(SAJSON, nullable=True)
    eligibility_snapshot: Mapped[dict[str, Any] | None] = mapped_column(SAJSON, nullable=True)
    # Intake progress so an applicant can stop and resume (US-03.1, US-03.2).
    intake_answers: Mapped[dict] = mapped_column(SAJSON, default=dict)
    # Stable key for the applicant's current position in the intake flow; NULL before intake.
    intake_step: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # Recorded expiry/renewal date for a completed case (US-19.1); NULL until known.
    renewal_due_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # First-class origin/residence for cross-border cases (e.g. a Bangladeshi citizen resident
    # in Japan). ISO-3166 alpha-2; NULL for domestic scopes where residence == jurisdiction.
    origin_country: Mapped[str | None] = mapped_column(String(8), nullable=True, index=True)
    residence_country: Mapped[str | None] = mapped_column(String(8), nullable=True, index=True)
    # The ScopeResearch row this case consumes when its scope has no live content pack.
    research_id: Mapped[int | None] = mapped_column(
        ForeignKey("scope_research.id"), nullable=True, index=True
    )
    # Continuity facts from the applicant's previous application, used to evaluate
    # predicates like "same employer since the last application" (JP 技人国 language
    # waiver) and "same institution since the last application" (JP student 確認書
    # waiver). Captured at intake, never inferred (NF-1).
    prior_application: Mapped[dict[str, Any] | None] = mapped_column(SAJSON, nullable=True)
    # True when the case has been unlocked via credits or payment for official packet export.
    is_entitled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")

    jurisdiction: Mapped[Jurisdiction] = relationship(back_populates="cases")
    visa_category: Mapped[VisaCategory | None] = relationship(back_populates="cases")
    case_action: Mapped[CaseAction | None] = relationship(back_populates="cases")
    owner: Mapped[User | None] = relationship(back_populates="cases")
    research: Mapped[ScopeResearch | None] = relationship()
    checklist_items: Mapped[list[CaseChecklistItem]] = relationship(
        back_populates="case", cascade="all, delete-orphan"
    )
    documents: Mapped[list[CaseDocument]] = relationship(
        back_populates="case", cascade="all, delete-orphan"
    )
    generated_forms: Mapped[list[CaseGeneratedForm]] = relationship(
        back_populates="case", cascade="all, delete-orphan"
    )
    escalations: Mapped[list[CaseEscalation]] = relationship(
        back_populates="case", cascade="all, delete-orphan"
    )
    stage_research: Mapped[list[CaseStageResearch]] = relationship(
        back_populates="case", cascade="all, delete-orphan"
    )
    payments: Mapped[list[Payment]] = relationship(back_populates="case")


class CaseDocument(TimestampMixin, Base):
    """Applicant-provided document metadata and OCR output."""

    __tablename__ = "case_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), index=True)
    doc_type: Mapped[str] = mapped_column(String(64), index=True)
    filename: Mapped[str] = mapped_column(String(256))
    storage_key: Mapped[str] = mapped_column(String(512))
    extracted_fields: Mapped[dict[str, Any]] = mapped_column(SAJSON, default=dict)
    extraction_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    content_type: Mapped[str] = mapped_column(String(128))

    case: Mapped[Case] = relationship(back_populates="documents")
    checklist_items: Mapped[list[CaseChecklistItem]] = relationship(back_populates="document")


class CaseChecklistItem(TimestampMixin, Base):
    """Materialized document checklist item for a case."""

    __tablename__ = "case_checklist_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), index=True)
    code: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(256))
    how_to_obtain: Mapped[str] = mapped_column(Text)
    why_required: Mapped[str] = mapped_column(Text)
    is_required: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    status: Mapped[str] = mapped_column(String(16), default="needed", server_default="needed")
    citation: Mapped[dict[str, Any]] = mapped_column(SAJSON, default=dict)
    document_id: Mapped[int | None] = mapped_column(
        ForeignKey("case_documents.id"), nullable=True, index=True
    )

    case: Mapped[Case] = relationship(back_populates="checklist_items")
    document: Mapped[CaseDocument | None] = relationship(back_populates="checklist_items")


class CaseGeneratedForm(TimestampMixin, Base):
    """A filled, version-pinned form generated from a live template."""

    __tablename__ = "case_generated_forms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), index=True)
    # NULL for research-driven forms (template lives in the ScopeResearch payload).
    form_template_id: Mapped[int | None] = mapped_column(
        ForeignKey("form_templates.id"), nullable=True, index=True
    )
    # Set (instead of form_template_id) when the form came from a research snapshot.
    research_id: Mapped[int | None] = mapped_column(
        ForeignKey("scope_research.id"), nullable=True, index=True
    )
    form_code: Mapped[str] = mapped_column(String(64), index=True)
    form_version: Mapped[str] = mapped_column(String(32))
    filled_fields: Mapped[dict[str, Any]] = mapped_column(SAJSON, default=dict)
    missing_required_fields: Mapped[list[str]] = mapped_column(SAJSON, default=list)
    citation: Mapped[dict[str, Any]] = mapped_column(SAJSON, default=dict)

    case: Mapped[Case] = relationship(back_populates="generated_forms")
    form_template: Mapped[FormTemplate | None] = relationship(back_populates="generated_forms")


class CaseEscalation(TimestampMixin, Base):
    """Applicant-requested or safety-triggered human handoff."""

    __tablename__ = "case_escalations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), index=True)
    reason: Mapped[str] = mapped_column(String(32))
    message: Mapped[str] = mapped_column(Text)
    consent_to_share: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    status: Mapped[str] = mapped_column(String(16), default="open", server_default="open")
    outcome: Mapped[str | None] = mapped_column(Text, nullable=True)

    case: Mapped[Case] = relationship(back_populates="escalations")


class OutboxEvent(TimestampMixin, Base):
    """Transactional outbox — written with the business change, drained by the worker."""

    __tablename__ = "outbox_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # e.g. "renewal.due", "source.changed", "case.escalated".
    topic: Mapped[str] = mapped_column(String(64), index=True)
    # JSON on Postgres, JSON-as-text on SQLite — portable across both engines.
    payload: Mapped[dict] = mapped_column(SAJSON, default=dict)
    # NULL while pending; stamped when the worker has handled it (at-least-once).
    processed_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True, index=True)


class PaymentStatus(StrEnum):
    """Payment lifecycle states."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


class Payment(TimestampMixin, Base):
    """Mock payment record for visa application fees."""

    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    # Unique transaction identifier
    transaction_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    # Payment breakdown
    visa_fee: Mapped[float] = mapped_column(Float, default=0.0)
    service_fee: Mapped[float] = mapped_column(Float, default=0.0)
    total_amount: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    # Status tracking
    status: Mapped[str] = mapped_column(
        String(16), default=PaymentStatus.PENDING, server_default=PaymentStatus.PENDING
    )
    # Mock payment details
    payment_method: Mapped[str | None] = mapped_column(String(32), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    # Additional metadata
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(SAJSON, nullable=True)

    case: Mapped[Case] = relationship(back_populates="payments")
    user: Mapped[User] = relationship()


class DocumentWalletItem(TimestampMixin, Base):
    """Reusable document in user's encrypted wallet with versioning."""

    __tablename__ = "document_wallet_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    # Document classification
    doc_type: Mapped[str] = mapped_column(String(64), index=True)
    # e.g., "passport", "bank_statement", "employment_letter"
    name: Mapped[str] = mapped_column(String(256))
    # Version tracking
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    is_latest: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    # Storage
    storage_key: Mapped[str] = mapped_column(String(512))
    filename: Mapped[str] = mapped_column(String(256))
    content_type: Mapped[str] = mapped_column(String(128))
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # OCR extracted data
    extracted_fields: Mapped[dict[str, Any]] = mapped_column(SAJSON, default=dict)
    extraction_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Validity tracking
    issued_date: Mapped[str | None] = mapped_column(String(16), nullable=True)
    expiry_date: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # Status
    status: Mapped[str] = mapped_column(String(16), default="active", server_default="active")
    # active, expired, revoked
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped[User] = relationship()
    versions: Mapped[list[DocumentWalletItemVersion]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class DocumentWalletItemVersion(TimestampMixin, Base):
    """Historical version of a wallet document."""

    __tablename__ = "document_wallet_item_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("document_wallet_items.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    storage_key: Mapped[str] = mapped_column(String(512))
    filename: Mapped[str] = mapped_column(String(256))
    content_type: Mapped[str] = mapped_column(String(128))
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    extracted_fields: Mapped[dict[str, Any]] = mapped_column(SAJSON, default=dict)
    extraction_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    document: Mapped[DocumentWalletItem] = relationship(back_populates="versions")


class CreditTransaction(TimestampMixin, Base):
    """Credit ledger transaction recording purchases, bonuses, and consumption."""

    __tablename__ = "credit_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    amount: Mapped[int] = mapped_column(Integer)  # +50, +200 on top-up; -2 on OCR; -30 on case unlock
    balance_after: Mapped[int] = mapped_column(Integer)
    feature: Mapped[str] = mapped_column(String(64))  # "welcome_bonus", "top_up", "ocr_extraction", "ai_query", "case_unlock"
    case_id: Mapped[int | None] = mapped_column(ForeignKey("cases.id"), nullable=True, index=True)
    description: Mapped[str] = mapped_column(String(256))
    reference_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)

    user: Mapped[User] = relationship(back_populates="credit_transactions")
    case: Mapped[Case | None] = relationship()

