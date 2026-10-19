-- Torii schema for Supabase  (GENERATED -- do not hand-edit)
--
-- Source of truth is Alembic: apps/api/src/torii_api/db/migrations/versions/*.py at
-- revision 0019. This file was produced by running all 19 migrations against a clean
-- PostgreSQL 17 + pgvector database and dumping the result with:
--
--   pg_dump --schema-only --no-owner --no-privileges --no-comments
--
-- then adjusting exactly three things for Supabase (see infra/supabase/README.md):
--   * removed the \restrict / \unrestrict psql meta-commands (they are not SQL)
--   * removed `SET transaction_timeout` (PostgreSQL 17+ only; Supabase may be older)
--   * moved pgvector into the `extensions` schema, where Supabase keeps extensions
--
-- Regenerate rather than edit -- see the README for the one command that rebuilds it.
--
-- The alembic_version INSERT at the end is load-bearing: pg_dump --schema-only emits the
-- table but not its row, and an unstamped database makes the API replay all 19 migrations
-- over the schema above and fail on the first CREATE TABLE.
--
-- 22 tables, 64 indexes, 39 foreign keys.

--
-- PostgreSQL database dump
--


-- Dumped from database version 17.11 (Debian 17.11-1.pgdg12+2)
-- Dumped by pg_dump version 17.11 (Debian 17.11-1.pgdg12+2)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: vector; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA extensions;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


--
-- Name: case_actions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.case_actions (
    id integer NOT NULL,
    jurisdiction_id integer NOT NULL,
    code character varying(32) NOT NULL,
    name character varying(128) NOT NULL,
    is_live boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    research_enabled boolean DEFAULT false NOT NULL,
    is_enabled boolean DEFAULT true NOT NULL,
    description character varying(512) DEFAULT ''::character varying NOT NULL,
    source character varying(16) DEFAULT 'manual'::character varying NOT NULL,
    citation json DEFAULT '{}'::json NOT NULL
);


--
-- Name: case_actions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.case_actions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: case_actions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.case_actions_id_seq OWNED BY public.case_actions.id;


--
-- Name: case_checklist_items; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.case_checklist_items (
    id integer NOT NULL,
    case_id integer NOT NULL,
    code character varying(64) NOT NULL,
    name character varying(256) NOT NULL,
    how_to_obtain text NOT NULL,
    why_required text NOT NULL,
    is_required boolean DEFAULT true NOT NULL,
    status character varying(16) DEFAULT 'needed'::character varying NOT NULL,
    citation json NOT NULL,
    document_id integer,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: case_checklist_items_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.case_checklist_items_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: case_checklist_items_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.case_checklist_items_id_seq OWNED BY public.case_checklist_items.id;


--
-- Name: case_documents; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.case_documents (
    id integer NOT NULL,
    case_id integer NOT NULL,
    doc_type character varying(64) NOT NULL,
    filename character varying(256) NOT NULL,
    storage_key character varying(512) NOT NULL,
    extracted_fields json NOT NULL,
    extraction_confidence double precision,
    confirmed boolean DEFAULT false NOT NULL,
    content_type character varying(128) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: case_documents_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.case_documents_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: case_documents_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.case_documents_id_seq OWNED BY public.case_documents.id;


--
-- Name: case_escalations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.case_escalations (
    id integer NOT NULL,
    case_id integer NOT NULL,
    reason character varying(32) NOT NULL,
    message text NOT NULL,
    consent_to_share boolean DEFAULT false NOT NULL,
    status character varying(16) DEFAULT 'open'::character varying NOT NULL,
    outcome text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: case_escalations_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.case_escalations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: case_escalations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.case_escalations_id_seq OWNED BY public.case_escalations.id;


--
-- Name: case_generated_forms; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.case_generated_forms (
    id integer NOT NULL,
    case_id integer NOT NULL,
    form_template_id integer,
    form_code character varying(64) NOT NULL,
    form_version character varying(32) NOT NULL,
    filled_fields json NOT NULL,
    missing_required_fields json NOT NULL,
    citation json NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    research_id integer
);


--
-- Name: case_generated_forms_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.case_generated_forms_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: case_generated_forms_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.case_generated_forms_id_seq OWNED BY public.case_generated_forms.id;


--
-- Name: case_stage_research; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.case_stage_research (
    id integer NOT NULL,
    case_id integer,
    stage character varying(16) NOT NULL,
    scope_key character varying(160),
    status character varying(16) DEFAULT 'queued'::character varying NOT NULL,
    payload json NOT NULL,
    source_pages json NOT NULL,
    error text,
    researched_at timestamp with time zone,
    expires_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: case_stage_research_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.case_stage_research_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: case_stage_research_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.case_stage_research_id_seq OWNED BY public.case_stage_research.id;


--
-- Name: cases; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.cases (
    id integer NOT NULL,
    reference character varying(64) NOT NULL,
    jurisdiction_id integer NOT NULL,
    status character varying(32) DEFAULT 'draft'::character varying NOT NULL,
    applicant_email character varying(320),
    renewal_due_at timestamp with time zone,
    notes text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    user_id integer,
    visa_category_id integer,
    case_action_id integer,
    intake_answers json DEFAULT '{}'::json NOT NULL,
    intake_step character varying(128),
    locale character varying(16) DEFAULT 'en'::character varying NOT NULL,
    host_locale character varying(16) DEFAULT 'ja'::character varying NOT NULL,
    review_flags_acknowledged boolean DEFAULT false NOT NULL,
    submission_reference character varying(128),
    packet_snapshot json,
    eligibility_snapshot json,
    origin_country character varying(8),
    residence_country character varying(8),
    research_id integer,
    prior_application json,
    is_entitled boolean DEFAULT false NOT NULL,
    is_archived boolean DEFAULT false NOT NULL
);


--
-- Name: cases_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.cases_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: cases_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.cases_id_seq OWNED BY public.cases.id;


--
-- Name: credit_transactions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.credit_transactions (
    id integer NOT NULL,
    user_id integer NOT NULL,
    amount integer NOT NULL,
    balance_after integer NOT NULL,
    feature character varying(64) NOT NULL,
    case_id integer,
    description character varying(256) NOT NULL,
    reference_id character varying(128),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: credit_transactions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.credit_transactions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: credit_transactions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.credit_transactions_id_seq OWNED BY public.credit_transactions.id;


--
-- Name: document_requirement_sets; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.document_requirement_sets (
    id integer NOT NULL,
    jurisdiction_id integer NOT NULL,
    visa_category_id integer NOT NULL,
    case_action_id integer NOT NULL,
    items json NOT NULL,
    is_live boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: document_requirement_sets_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.document_requirement_sets_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: document_requirement_sets_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.document_requirement_sets_id_seq OWNED BY public.document_requirement_sets.id;


--
-- Name: document_wallet_item_versions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.document_wallet_item_versions (
    id integer NOT NULL,
    document_id integer NOT NULL,
    version integer NOT NULL,
    storage_key character varying(512) NOT NULL,
    filename character varying(256) NOT NULL,
    content_type character varying(128) NOT NULL,
    file_size integer,
    extracted_fields json DEFAULT '{}'::json NOT NULL,
    extraction_confidence double precision,
    notes text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: document_wallet_item_versions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.document_wallet_item_versions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: document_wallet_item_versions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.document_wallet_item_versions_id_seq OWNED BY public.document_wallet_item_versions.id;


--
-- Name: document_wallet_items; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.document_wallet_items (
    id integer NOT NULL,
    user_id integer NOT NULL,
    doc_type character varying(64) NOT NULL,
    name character varying(256) NOT NULL,
    version integer DEFAULT 1 NOT NULL,
    is_latest boolean DEFAULT true NOT NULL,
    storage_key character varying(512) NOT NULL,
    filename character varying(256) NOT NULL,
    content_type character varying(128) NOT NULL,
    file_size integer,
    extracted_fields json DEFAULT '{}'::json NOT NULL,
    extraction_confidence double precision,
    issued_date character varying(16),
    expiry_date character varying(16),
    status character varying(16) DEFAULT 'active'::character varying NOT NULL,
    notes text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: document_wallet_items_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.document_wallet_items_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: document_wallet_items_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.document_wallet_items_id_seq OWNED BY public.document_wallet_items.id;


--
-- Name: eligibility_rule_sets; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.eligibility_rule_sets (
    id integer NOT NULL,
    jurisdiction_id integer NOT NULL,
    visa_category_id integer NOT NULL,
    case_action_id integer NOT NULL,
    rules json NOT NULL,
    is_live boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: eligibility_rule_sets_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.eligibility_rule_sets_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: eligibility_rule_sets_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.eligibility_rule_sets_id_seq OWNED BY public.eligibility_rule_sets.id;


--
-- Name: form_templates; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.form_templates (
    id integer NOT NULL,
    jurisdiction_id integer NOT NULL,
    visa_category_id integer NOT NULL,
    case_action_id integer NOT NULL,
    code character varying(64) NOT NULL,
    version character varying(32) NOT NULL,
    is_live boolean DEFAULT false NOT NULL,
    official_title character varying(256) NOT NULL,
    citation json NOT NULL,
    field_mappings json NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: form_templates_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.form_templates_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: form_templates_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.form_templates_id_seq OWNED BY public.form_templates.id;


--
-- Name: intake_definitions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.intake_definitions (
    id integer NOT NULL,
    jurisdiction_id integer NOT NULL,
    visa_category_id integer NOT NULL,
    case_action_id integer NOT NULL,
    questions json NOT NULL,
    is_live boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: intake_definitions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.intake_definitions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: intake_definitions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.intake_definitions_id_seq OWNED BY public.intake_definitions.id;


--
-- Name: jurisdictions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.jurisdictions (
    id integer NOT NULL,
    code character varying(8) NOT NULL,
    name character varying(128) NOT NULL,
    is_live boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    efile_enabled boolean DEFAULT false NOT NULL,
    is_enabled boolean DEFAULT true NOT NULL
);


--
-- Name: jurisdictions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.jurisdictions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: jurisdictions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.jurisdictions_id_seq OWNED BY public.jurisdictions.id;


--
-- Name: outbox_events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.outbox_events (
    id integer NOT NULL,
    topic character varying(64) NOT NULL,
    payload json,
    processed_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: outbox_events_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.outbox_events_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: outbox_events_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.outbox_events_id_seq OWNED BY public.outbox_events.id;


--
-- Name: pack_overrides; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pack_overrides (
    id integer NOT NULL,
    jurisdiction_id integer NOT NULL,
    visa_category_id integer NOT NULL,
    case_action_id integer NOT NULL,
    path character varying(256) NOT NULL,
    value json,
    reason text DEFAULT ''::text NOT NULL,
    created_by character varying(256) DEFAULT ''::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: pack_overrides_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.pack_overrides_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: pack_overrides_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.pack_overrides_id_seq OWNED BY public.pack_overrides.id;


--
-- Name: payments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.payments (
    id integer NOT NULL,
    case_id integer NOT NULL,
    user_id integer NOT NULL,
    transaction_id character varying(64) NOT NULL,
    visa_fee double precision DEFAULT '0'::double precision NOT NULL,
    service_fee double precision DEFAULT '0'::double precision NOT NULL,
    total_amount double precision DEFAULT '0'::double precision NOT NULL,
    currency character varying(8) DEFAULT 'USD'::character varying NOT NULL,
    status character varying(16) DEFAULT 'pending'::character varying NOT NULL,
    payment_method character varying(32),
    paid_at timestamp with time zone,
    metadata_json json,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: payments_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.payments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: payments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.payments_id_seq OWNED BY public.payments.id;


--
-- Name: scope_research; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.scope_research (
    id integer NOT NULL,
    jurisdiction_id integer NOT NULL,
    visa_category_id integer NOT NULL,
    case_action_id integer NOT NULL,
    origin_country character varying(8),
    residence_country character varying(8),
    status character varying(16) DEFAULT 'queued'::character varying NOT NULL,
    payload json NOT NULL,
    source_pages json NOT NULL,
    error text,
    researched_at timestamp with time zone,
    expires_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: scope_research_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.scope_research_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: scope_research_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.scope_research_id_seq OWNED BY public.scope_research.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id integer NOT NULL,
    email character varying(320) NOT NULL,
    password_hash character varying(128) NOT NULL,
    role character varying(32) DEFAULT 'applicant'::character varying NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    username character varying(64),
    email_verified boolean DEFAULT false NOT NULL,
    email_verification_token character varying(128),
    password_reset_token character varying(128),
    password_reset_expires timestamp with time zone,
    full_name character varying(200),
    nationality character varying(100),
    passport_number character varying(32),
    passport_expiry character varying(16),
    date_of_birth character varying(16),
    current_country character varying(100),
    profile_complete boolean DEFAULT false NOT NULL,
    avatar_url character varying(512),
    credit_balance integer DEFAULT 10 NOT NULL,
    email_verification_expires timestamp with time zone
);


--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: visa_categories; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.visa_categories (
    id integer NOT NULL,
    jurisdiction_id integer NOT NULL,
    code character varying(32) NOT NULL,
    name character varying(128) NOT NULL,
    is_live boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    research_enabled boolean DEFAULT false NOT NULL,
    is_enabled boolean DEFAULT true NOT NULL,
    description character varying(512) DEFAULT ''::character varying NOT NULL,
    source character varying(16) DEFAULT 'manual'::character varying NOT NULL,
    citation json DEFAULT '{}'::json NOT NULL
);


--
-- Name: visa_categories_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.visa_categories_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: visa_categories_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.visa_categories_id_seq OWNED BY public.visa_categories.id;


--
-- Name: case_actions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.case_actions ALTER COLUMN id SET DEFAULT nextval('public.case_actions_id_seq'::regclass);


--
-- Name: case_checklist_items id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.case_checklist_items ALTER COLUMN id SET DEFAULT nextval('public.case_checklist_items_id_seq'::regclass);


--
-- Name: case_documents id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.case_documents ALTER COLUMN id SET DEFAULT nextval('public.case_documents_id_seq'::regclass);


--
-- Name: case_escalations id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.case_escalations ALTER COLUMN id SET DEFAULT nextval('public.case_escalations_id_seq'::regclass);


--
-- Name: case_generated_forms id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.case_generated_forms ALTER COLUMN id SET DEFAULT nextval('public.case_generated_forms_id_seq'::regclass);


--
-- Name: case_stage_research id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.case_stage_research ALTER COLUMN id SET DEFAULT nextval('public.case_stage_research_id_seq'::regclass);


--
-- Name: cases id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cases ALTER COLUMN id SET DEFAULT nextval('public.cases_id_seq'::regclass);


--
-- Name: credit_transactions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.credit_transactions ALTER COLUMN id SET DEFAULT nextval('public.credit_transactions_id_seq'::regclass);


--
-- Name: document_requirement_sets id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_requirement_sets ALTER COLUMN id SET DEFAULT nextval('public.document_requirement_sets_id_seq'::regclass);


--
-- Name: document_wallet_item_versions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_wallet_item_versions ALTER COLUMN id SET DEFAULT nextval('public.document_wallet_item_versions_id_seq'::regclass);


--
-- Name: document_wallet_items id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_wallet_items ALTER COLUMN id SET DEFAULT nextval('public.document_wallet_items_id_seq'::regclass);


--
-- Name: eligibility_rule_sets id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.eligibility_rule_sets ALTER COLUMN id SET DEFAULT nextval('public.eligibility_rule_sets_id_seq'::regclass);


--
-- Name: form_templates id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.form_templates ALTER COLUMN id SET DEFAULT nextval('public.form_templates_id_seq'::regclass);


--
-- Name: intake_definitions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intake_definitions ALTER COLUMN id SET DEFAULT nextval('public.intake_definitions_id_seq'::regclass);


--
-- Name: jurisdictions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.jurisdictions ALTER COLUMN id SET DEFAULT nextval('public.jurisdictions_id_seq'::regclass);


--
-- Name: outbox_events id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.outbox_events ALTER COLUMN id SET DEFAULT nextval('public.outbox_events_id_seq'::regclass);


--
-- Name: pack_overrides id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pack_overrides ALTER COLUMN id SET DEFAULT nextval('public.pack_overrides_id_seq'::regclass);


--
-- Name: payments id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payments ALTER COLUMN id SET DEFAULT nextval('public.payments_id_seq'::regclass);


--
-- Name: scope_research id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scope_research ALTER COLUMN id SET DEFAULT nextval('public.scope_research_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Name: visa_categories id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.visa_categories ALTER COLUMN id SET DEFAULT nextval('public.visa_categories_id_seq'::regclass);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: case_actions pk_case_actions; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.case_actions
    ADD CONSTRAINT pk_case_actions PRIMARY KEY (id);


--
-- Name: case_checklist_items pk_case_checklist_items; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.case_checklist_items
    ADD CONSTRAINT pk_case_checklist_items PRIMARY KEY (id);


--
-- Name: case_documents pk_case_documents; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.case_documents
    ADD CONSTRAINT pk_case_documents PRIMARY KEY (id);


--
-- Name: case_escalations pk_case_escalations; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.case_escalations
    ADD CONSTRAINT pk_case_escalations PRIMARY KEY (id);


--
-- Name: case_generated_forms pk_case_generated_forms; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.case_generated_forms
    ADD CONSTRAINT pk_case_generated_forms PRIMARY KEY (id);


--
-- Name: case_stage_research pk_case_stage_research; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.case_stage_research
    ADD CONSTRAINT pk_case_stage_research PRIMARY KEY (id);


--
-- Name: cases pk_cases; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cases
    ADD CONSTRAINT pk_cases PRIMARY KEY (id);


--
-- Name: credit_transactions pk_credit_transactions; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.credit_transactions
    ADD CONSTRAINT pk_credit_transactions PRIMARY KEY (id);


--
-- Name: document_requirement_sets pk_document_requirement_sets; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_requirement_sets
    ADD CONSTRAINT pk_document_requirement_sets PRIMARY KEY (id);


--
-- Name: document_wallet_item_versions pk_document_wallet_item_versions; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_wallet_item_versions
    ADD CONSTRAINT pk_document_wallet_item_versions PRIMARY KEY (id);


--
-- Name: document_wallet_items pk_document_wallet_items; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_wallet_items
    ADD CONSTRAINT pk_document_wallet_items PRIMARY KEY (id);


--
-- Name: eligibility_rule_sets pk_eligibility_rule_sets; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.eligibility_rule_sets
    ADD CONSTRAINT pk_eligibility_rule_sets PRIMARY KEY (id);


--
-- Name: form_templates pk_form_templates; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.form_templates
    ADD CONSTRAINT pk_form_templates PRIMARY KEY (id);


--
-- Name: intake_definitions pk_intake_definitions; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intake_definitions
    ADD CONSTRAINT pk_intake_definitions PRIMARY KEY (id);


--
-- Name: jurisdictions pk_jurisdictions; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.jurisdictions
    ADD CONSTRAINT pk_jurisdictions PRIMARY KEY (id);


--
-- Name: outbox_events pk_outbox_events; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.outbox_events
    ADD CONSTRAINT pk_outbox_events PRIMARY KEY (id);


--
-- Name: pack_overrides pk_pack_overrides; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pack_overrides
    ADD CONSTRAINT pk_pack_overrides PRIMARY KEY (id);


--
-- Name: payments pk_payments; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT pk_payments PRIMARY KEY (id);


--
-- Name: scope_research pk_scope_research; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scope_research
    ADD CONSTRAINT pk_scope_research PRIMARY KEY (id);


--
-- Name: users pk_users; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT pk_users PRIMARY KEY (id);


--
-- Name: visa_categories pk_visa_categories; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.visa_categories
    ADD CONSTRAINT pk_visa_categories PRIMARY KEY (id);


--
-- Name: case_stage_research uq_case_stage_research_case; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.case_stage_research
    ADD CONSTRAINT uq_case_stage_research_case UNIQUE (case_id, stage);


--
-- Name: case_stage_research uq_case_stage_research_scope; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.case_stage_research
    ADD CONSTRAINT uq_case_stage_research_scope UNIQUE (scope_key, stage);


--
-- Name: cases uq_cases_reference; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cases
    ADD CONSTRAINT uq_cases_reference UNIQUE (reference);


--
-- Name: jurisdictions uq_jurisdictions_code; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.jurisdictions
    ADD CONSTRAINT uq_jurisdictions_code UNIQUE (code);


--
-- Name: users uq_users_email; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT uq_users_email UNIQUE (email);


--
-- Name: users uq_users_username; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT uq_users_username UNIQUE (username);


--
-- Name: ix_case_actions_code; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_case_actions_code ON public.case_actions USING btree (code);


--
-- Name: ix_case_actions_jurisdiction_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_case_actions_jurisdiction_id ON public.case_actions USING btree (jurisdiction_id);


--
-- Name: ix_case_checklist_items_case_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_case_checklist_items_case_id ON public.case_checklist_items USING btree (case_id);


--
-- Name: ix_case_checklist_items_code; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_case_checklist_items_code ON public.case_checklist_items USING btree (code);


--
-- Name: ix_case_checklist_items_document_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_case_checklist_items_document_id ON public.case_checklist_items USING btree (document_id);


--
-- Name: ix_case_documents_case_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_case_documents_case_id ON public.case_documents USING btree (case_id);


--
-- Name: ix_case_documents_doc_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_case_documents_doc_type ON public.case_documents USING btree (doc_type);


--
-- Name: ix_case_escalations_case_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_case_escalations_case_id ON public.case_escalations USING btree (case_id);


--
-- Name: ix_case_generated_forms_case_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_case_generated_forms_case_id ON public.case_generated_forms USING btree (case_id);


--
-- Name: ix_case_generated_forms_form_code; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_case_generated_forms_form_code ON public.case_generated_forms USING btree (form_code);


--
-- Name: ix_case_generated_forms_form_template_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_case_generated_forms_form_template_id ON public.case_generated_forms USING btree (form_template_id);


--
-- Name: ix_case_generated_forms_research_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_case_generated_forms_research_id ON public.case_generated_forms USING btree (research_id);


--
-- Name: ix_case_stage_research_case_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_case_stage_research_case_id ON public.case_stage_research USING btree (case_id);


--
-- Name: ix_case_stage_research_scope_key; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_case_stage_research_scope_key ON public.case_stage_research USING btree (scope_key);


--
-- Name: ix_case_stage_research_stage; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_case_stage_research_stage ON public.case_stage_research USING btree (stage);


--
-- Name: ix_cases_case_action_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_cases_case_action_id ON public.cases USING btree (case_action_id);


--
-- Name: ix_cases_jurisdiction_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_cases_jurisdiction_id ON public.cases USING btree (jurisdiction_id);


--
-- Name: ix_cases_origin_country; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_cases_origin_country ON public.cases USING btree (origin_country);


--
-- Name: ix_cases_reference; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_cases_reference ON public.cases USING btree (reference);


--
-- Name: ix_cases_research_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_cases_research_id ON public.cases USING btree (research_id);


--
-- Name: ix_cases_residence_country; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_cases_residence_country ON public.cases USING btree (residence_country);


--
-- Name: ix_cases_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_cases_user_id ON public.cases USING btree (user_id);


--
-- Name: ix_cases_visa_category_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_cases_visa_category_id ON public.cases USING btree (visa_category_id);


--
-- Name: ix_credit_transactions_case_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_credit_transactions_case_id ON public.credit_transactions USING btree (case_id);


--
-- Name: ix_credit_transactions_reference_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_credit_transactions_reference_id ON public.credit_transactions USING btree (reference_id);


--
-- Name: ix_credit_transactions_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_credit_transactions_user_id ON public.credit_transactions USING btree (user_id);


--
-- Name: ix_document_requirement_sets_case_action_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_document_requirement_sets_case_action_id ON public.document_requirement_sets USING btree (case_action_id);


--
-- Name: ix_document_requirement_sets_jurisdiction_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_document_requirement_sets_jurisdiction_id ON public.document_requirement_sets USING btree (jurisdiction_id);


--
-- Name: ix_document_requirement_sets_visa_category_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_document_requirement_sets_visa_category_id ON public.document_requirement_sets USING btree (visa_category_id);


--
-- Name: ix_document_wallet_item_versions_document_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_document_wallet_item_versions_document_id ON public.document_wallet_item_versions USING btree (document_id);


--
-- Name: ix_document_wallet_items_doc_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_document_wallet_items_doc_type ON public.document_wallet_items USING btree (doc_type);


--
-- Name: ix_document_wallet_items_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_document_wallet_items_user_id ON public.document_wallet_items USING btree (user_id);


--
-- Name: ix_eligibility_rule_sets_case_action_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_eligibility_rule_sets_case_action_id ON public.eligibility_rule_sets USING btree (case_action_id);


--
-- Name: ix_eligibility_rule_sets_jurisdiction_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_eligibility_rule_sets_jurisdiction_id ON public.eligibility_rule_sets USING btree (jurisdiction_id);


--
-- Name: ix_eligibility_rule_sets_visa_category_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_eligibility_rule_sets_visa_category_id ON public.eligibility_rule_sets USING btree (visa_category_id);


--
-- Name: ix_form_templates_case_action_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_form_templates_case_action_id ON public.form_templates USING btree (case_action_id);


--
-- Name: ix_form_templates_code; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_form_templates_code ON public.form_templates USING btree (code);


--
-- Name: ix_form_templates_jurisdiction_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_form_templates_jurisdiction_id ON public.form_templates USING btree (jurisdiction_id);


--
-- Name: ix_form_templates_visa_category_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_form_templates_visa_category_id ON public.form_templates USING btree (visa_category_id);


--
-- Name: ix_intake_definitions_case_action_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_intake_definitions_case_action_id ON public.intake_definitions USING btree (case_action_id);


--
-- Name: ix_intake_definitions_jurisdiction_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_intake_definitions_jurisdiction_id ON public.intake_definitions USING btree (jurisdiction_id);


--
-- Name: ix_intake_definitions_visa_category_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_intake_definitions_visa_category_id ON public.intake_definitions USING btree (visa_category_id);


--
-- Name: ix_jurisdictions_code; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_jurisdictions_code ON public.jurisdictions USING btree (code);


--
-- Name: ix_outbox_events_processed_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_outbox_events_processed_at ON public.outbox_events USING btree (processed_at);


--
-- Name: ix_outbox_events_topic; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_outbox_events_topic ON public.outbox_events USING btree (topic);


--
-- Name: ix_pack_overrides_case_action_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pack_overrides_case_action_id ON public.pack_overrides USING btree (case_action_id);


--
-- Name: ix_pack_overrides_jurisdiction_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pack_overrides_jurisdiction_id ON public.pack_overrides USING btree (jurisdiction_id);


--
-- Name: ix_pack_overrides_path; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pack_overrides_path ON public.pack_overrides USING btree (path);


--
-- Name: ix_pack_overrides_visa_category_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pack_overrides_visa_category_id ON public.pack_overrides USING btree (visa_category_id);


--
-- Name: ix_payments_case_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_payments_case_id ON public.payments USING btree (case_id);


--
-- Name: ix_payments_transaction_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_payments_transaction_id ON public.payments USING btree (transaction_id);


--
-- Name: ix_payments_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_payments_user_id ON public.payments USING btree (user_id);


--
-- Name: ix_scope_research_case_action_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_scope_research_case_action_id ON public.scope_research USING btree (case_action_id);


--
-- Name: ix_scope_research_jurisdiction_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_scope_research_jurisdiction_id ON public.scope_research USING btree (jurisdiction_id);


--
-- Name: ix_scope_research_visa_category_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_scope_research_visa_category_id ON public.scope_research USING btree (visa_category_id);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: ix_users_email_verification_token; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_users_email_verification_token ON public.users USING btree (email_verification_token);


--
-- Name: ix_users_password_reset_token; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_users_password_reset_token ON public.users USING btree (password_reset_token);


--
-- Name: ix_users_username; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_users_username ON public.users USING btree (username);


--
-- Name: ix_visa_categories_code; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_visa_categories_code ON public.visa_categories USING btree (code);


--
-- Name: ix_visa_categories_jurisdiction_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_visa_categories_jurisdiction_id ON public.visa_categories USING btree (jurisdiction_id);


--
-- Name: uq_case_actions_jurisdiction_code; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_case_actions_jurisdiction_code ON public.case_actions USING btree (jurisdiction_id, code);


--
-- Name: uq_pack_overrides_scope_path; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_pack_overrides_scope_path ON public.pack_overrides USING btree (jurisdiction_id, visa_category_id, case_action_id, path);


--
-- Name: uq_visa_categories_jurisdiction_code; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_visa_categories_jurisdiction_code ON public.visa_categories USING btree (jurisdiction_id, code);


--
-- Name: case_actions fk_case_actions_jurisdiction_id_jurisdictions; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.case_actions
    ADD CONSTRAINT fk_case_actions_jurisdiction_id_jurisdictions FOREIGN KEY (jurisdiction_id) REFERENCES public.jurisdictions(id);


--
-- Name: case_checklist_items fk_case_checklist_items_case_id_cases; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.case_checklist_items
    ADD CONSTRAINT fk_case_checklist_items_case_id_cases FOREIGN KEY (case_id) REFERENCES public.cases(id);


--
-- Name: case_checklist_items fk_case_checklist_items_document_id_case_documents; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.case_checklist_items
    ADD CONSTRAINT fk_case_checklist_items_document_id_case_documents FOREIGN KEY (document_id) REFERENCES public.case_documents(id);


--
-- Name: case_documents fk_case_documents_case_id_cases; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.case_documents
    ADD CONSTRAINT fk_case_documents_case_id_cases FOREIGN KEY (case_id) REFERENCES public.cases(id);


--
-- Name: case_escalations fk_case_escalations_case_id_cases; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.case_escalations
    ADD CONSTRAINT fk_case_escalations_case_id_cases FOREIGN KEY (case_id) REFERENCES public.cases(id);


--
-- Name: case_generated_forms fk_case_generated_forms_case_id_cases; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.case_generated_forms
    ADD CONSTRAINT fk_case_generated_forms_case_id_cases FOREIGN KEY (case_id) REFERENCES public.cases(id);


--
-- Name: case_generated_forms fk_case_generated_forms_form_template_id_form_templates; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.case_generated_forms
    ADD CONSTRAINT fk_case_generated_forms_form_template_id_form_templates FOREIGN KEY (form_template_id) REFERENCES public.form_templates(id);


--
-- Name: case_generated_forms fk_case_generated_forms_research_id_scope_research; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.case_generated_forms
    ADD CONSTRAINT fk_case_generated_forms_research_id_scope_research FOREIGN KEY (research_id) REFERENCES public.scope_research(id);


--
-- Name: case_stage_research fk_case_stage_research_case_id_cases; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.case_stage_research
    ADD CONSTRAINT fk_case_stage_research_case_id_cases FOREIGN KEY (case_id) REFERENCES public.cases(id);


--
-- Name: cases fk_cases_case_action_id_case_actions; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cases
    ADD CONSTRAINT fk_cases_case_action_id_case_actions FOREIGN KEY (case_action_id) REFERENCES public.case_actions(id);


--
-- Name: cases fk_cases_jurisdiction_id_jurisdictions; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cases
    ADD CONSTRAINT fk_cases_jurisdiction_id_jurisdictions FOREIGN KEY (jurisdiction_id) REFERENCES public.jurisdictions(id);


--
-- Name: cases fk_cases_research_id_scope_research; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cases
    ADD CONSTRAINT fk_cases_research_id_scope_research FOREIGN KEY (research_id) REFERENCES public.scope_research(id);


--
-- Name: cases fk_cases_user_id_users; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cases
    ADD CONSTRAINT fk_cases_user_id_users FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: cases fk_cases_visa_category_id_visa_categories; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cases
    ADD CONSTRAINT fk_cases_visa_category_id_visa_categories FOREIGN KEY (visa_category_id) REFERENCES public.visa_categories(id);


--
-- Name: credit_transactions fk_credit_transactions_case_id_cases; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.credit_transactions
    ADD CONSTRAINT fk_credit_transactions_case_id_cases FOREIGN KEY (case_id) REFERENCES public.cases(id);


--
-- Name: credit_transactions fk_credit_transactions_user_id_users; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.credit_transactions
    ADD CONSTRAINT fk_credit_transactions_user_id_users FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: document_requirement_sets fk_document_requirement_sets_case_action_id_case_actions; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_requirement_sets
    ADD CONSTRAINT fk_document_requirement_sets_case_action_id_case_actions FOREIGN KEY (case_action_id) REFERENCES public.case_actions(id);


--
-- Name: document_requirement_sets fk_document_requirement_sets_jurisdiction_id_jurisdictions; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_requirement_sets
    ADD CONSTRAINT fk_document_requirement_sets_jurisdiction_id_jurisdictions FOREIGN KEY (jurisdiction_id) REFERENCES public.jurisdictions(id);


--
-- Name: document_requirement_sets fk_document_requirement_sets_visa_category_id_visa_categories; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_requirement_sets
    ADD CONSTRAINT fk_document_requirement_sets_visa_category_id_visa_categories FOREIGN KEY (visa_category_id) REFERENCES public.visa_categories(id);


--
-- Name: document_wallet_item_versions fk_document_wallet_item_versions_document_id_document_w_1b8b; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_wallet_item_versions
    ADD CONSTRAINT fk_document_wallet_item_versions_document_id_document_w_1b8b FOREIGN KEY (document_id) REFERENCES public.document_wallet_items(id);


--
-- Name: document_wallet_items fk_document_wallet_items_user_id_users; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_wallet_items
    ADD CONSTRAINT fk_document_wallet_items_user_id_users FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: eligibility_rule_sets fk_eligibility_rule_sets_case_action_id_case_actions; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.eligibility_rule_sets
    ADD CONSTRAINT fk_eligibility_rule_sets_case_action_id_case_actions FOREIGN KEY (case_action_id) REFERENCES public.case_actions(id);


--
-- Name: eligibility_rule_sets fk_eligibility_rule_sets_jurisdiction_id_jurisdictions; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.eligibility_rule_sets
    ADD CONSTRAINT fk_eligibility_rule_sets_jurisdiction_id_jurisdictions FOREIGN KEY (jurisdiction_id) REFERENCES public.jurisdictions(id);


--
-- Name: eligibility_rule_sets fk_eligibility_rule_sets_visa_category_id_visa_categories; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.eligibility_rule_sets
    ADD CONSTRAINT fk_eligibility_rule_sets_visa_category_id_visa_categories FOREIGN KEY (visa_category_id) REFERENCES public.visa_categories(id);


--
-- Name: form_templates fk_form_templates_case_action_id_case_actions; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.form_templates
    ADD CONSTRAINT fk_form_templates_case_action_id_case_actions FOREIGN KEY (case_action_id) REFERENCES public.case_actions(id);


--
-- Name: form_templates fk_form_templates_jurisdiction_id_jurisdictions; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.form_templates
    ADD CONSTRAINT fk_form_templates_jurisdiction_id_jurisdictions FOREIGN KEY (jurisdiction_id) REFERENCES public.jurisdictions(id);


--
-- Name: form_templates fk_form_templates_visa_category_id_visa_categories; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.form_templates
    ADD CONSTRAINT fk_form_templates_visa_category_id_visa_categories FOREIGN KEY (visa_category_id) REFERENCES public.visa_categories(id);


--
-- Name: intake_definitions fk_intake_definitions_case_action_id_case_actions; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intake_definitions
    ADD CONSTRAINT fk_intake_definitions_case_action_id_case_actions FOREIGN KEY (case_action_id) REFERENCES public.case_actions(id);


--
-- Name: intake_definitions fk_intake_definitions_jurisdiction_id_jurisdictions; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intake_definitions
    ADD CONSTRAINT fk_intake_definitions_jurisdiction_id_jurisdictions FOREIGN KEY (jurisdiction_id) REFERENCES public.jurisdictions(id);


--
-- Name: intake_definitions fk_intake_definitions_visa_category_id_visa_categories; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intake_definitions
    ADD CONSTRAINT fk_intake_definitions_visa_category_id_visa_categories FOREIGN KEY (visa_category_id) REFERENCES public.visa_categories(id);


--
-- Name: pack_overrides fk_pack_overrides_case_action_id_case_actions; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pack_overrides
    ADD CONSTRAINT fk_pack_overrides_case_action_id_case_actions FOREIGN KEY (case_action_id) REFERENCES public.case_actions(id);


--
-- Name: pack_overrides fk_pack_overrides_jurisdiction_id_jurisdictions; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pack_overrides
    ADD CONSTRAINT fk_pack_overrides_jurisdiction_id_jurisdictions FOREIGN KEY (jurisdiction_id) REFERENCES public.jurisdictions(id);


--
-- Name: pack_overrides fk_pack_overrides_visa_category_id_visa_categories; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pack_overrides
    ADD CONSTRAINT fk_pack_overrides_visa_category_id_visa_categories FOREIGN KEY (visa_category_id) REFERENCES public.visa_categories(id);


--
-- Name: payments fk_payments_case_id_cases; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT fk_payments_case_id_cases FOREIGN KEY (case_id) REFERENCES public.cases(id);


--
-- Name: payments fk_payments_user_id_users; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT fk_payments_user_id_users FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: scope_research fk_scope_research_case_action_id_case_actions; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scope_research
    ADD CONSTRAINT fk_scope_research_case_action_id_case_actions FOREIGN KEY (case_action_id) REFERENCES public.case_actions(id);


--
-- Name: scope_research fk_scope_research_jurisdiction_id_jurisdictions; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scope_research
    ADD CONSTRAINT fk_scope_research_jurisdiction_id_jurisdictions FOREIGN KEY (jurisdiction_id) REFERENCES public.jurisdictions(id);


--
-- Name: scope_research fk_scope_research_visa_category_id_visa_categories; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scope_research
    ADD CONSTRAINT fk_scope_research_visa_category_id_visa_categories FOREIGN KEY (visa_category_id) REFERENCES public.visa_categories(id);


--
-- Name: visa_categories fk_visa_categories_jurisdiction_id_jurisdictions; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.visa_categories
    ADD CONSTRAINT fk_visa_categories_jurisdiction_id_jurisdictions FOREIGN KEY (jurisdiction_id) REFERENCES public.jurisdictions(id);


--
-- PostgreSQL database dump complete
--




--
-- Stamp Alembic at the revision this schema was generated from. Without this row the API
-- would attempt to replay every migration over the tables created above.
--

INSERT INTO public.alembic_version (version_num) VALUES ('0019')
    ON CONFLICT (version_num) DO NOTHING;
