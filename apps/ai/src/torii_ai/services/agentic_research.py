"""Agentic per-stage research engine (docs/plan/03_corridor_bd_jp.md, Decisions §2).

Replaces pack/DB-first content resolution with live LLM + web-search research run once per
pipeline stage — ``admissibility`` (before a case exists), then ``intake``, ``eligibility``,
``documents``, ``forms`` (each per case) — rather than once per scope. Each stage is seeded with
everything the case has learned so far (prior answers, prior stage results), so later stages are
genuinely case-specific, not just destination-specific: two applicants on the same scope with
different answers can get different eligibility/document/form research.

NF-1 boundary, unchanged in spirit, applied per-stage: the LLM+search step *discovers* cited
content (what a rule/document/form *is*). It never decides whether a specific applicant satisfies
a rule — ``torii_api``'s existing deterministic functions (``evaluate_eligibility``, ``fill_form``,
checklist visibility) still do that, over whatever this engine discovered instead of over
DB-seeded pack rows.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

import structlog

from torii_ai.config import Settings
from torii_ai.llm.groq import ChatClient
from torii_ai.services.ops_scraper import country_label, extract_json, official_domains_for
from torii_ai.services.web_fetch import scrape_pages
from torii_ai.tools.tavily import SearchClient

log = structlog.get_logger()

Stage = Literal["admissibility", "intake", "eligibility", "documents", "forms"]

STAGES: tuple[Stage, ...] = ("admissibility", "intake", "eligibility", "documents", "forms")

# Stage -> the substantive key(s) of its extraction payload, kept when persisting a result
# (insufficient/followup_queries are round-tripping control fields, not content).
_STAGE_CONTENT_KEYS: dict[Stage, tuple[str, ...]] = {
    "admissibility": ("admission", "filing_channel", "process", "fees", "faq"),
    "intake": ("questions",),
    "eligibility": ("rules",),
    "documents": ("documents",),
    "forms": ("forms",),
}

# Followup rounds are capped at this many queries so a stalled research run doesn't spiral.
_MAX_FOLLOWUP_QUERIES = 3


@dataclass
class StageResearchRequest:
    stage: Stage
    destination_code: str
    purpose_code: str
    action_code: str
    nationality: str | None = None
    residence_country: str | None = None
    # Accumulated context from prior stages — stage-defined keys:
    #   eligibility/documents/forms: {"answers": {...}}
    #   documents/forms:             {..., "eligibility_findings": [...]}
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class StageResearchResult:
    stage: Stage
    items: dict[str, Any]
    source_pages: list[dict[str, Any]]
    insufficient: bool = False
    researched_at: str = ""


_CITATION_RULE = (
    '- Every "<citation>" placeholder above is an object: {"authority": "official body name", '
    '"title": "page title", "url": "https://...", "source_version": "YYYY-MM"}.'
)
_FOLLOWUP_RULE = (
    "- \"followup_queries\" are search-engine query text (e.g. \"Japan tourist visa required "
    'documents official"), never a URL and never one you were already given as source content.'
)

ADMISSIBILITY_SYSTEM = f"""You are an immigration research assistant. Given scraped official
government/embassy page content, determine whether a specific nationality needs a visa to enter
a destination country for a stated purpose, and how and where they would file.

Return JSON only, no markdown fences:
{{
  "admission": {{
    "visa_required": true|false|null,
    "route": "consular_visa|evisa|visa_on_arrival|visa_free|eta|null",
    "max_stay_days": integer|null,
    "citation": <citation>
  }},
  "filing_channel": {{
    "channel": "<see allowed channel values below>",
    "filer": "applicant|third_party|null",
    "mission_name": "string|null",
    "mission_url": "string|null",
    "directory_url": "string|null",
    "citation": <citation>
  }},
  "process": {{
    "steps": [{{"order": 1, "title": "...", "detail": "..."}}],
    "processing_time_days_min": integer|null,
    "processing_time_days_max": integer|null,
    "citation": <citation>
  }},
  "fees": [
    {{"code": "short_code", "amount": number|null, "currency": "ISO code", "citation": <citation>}}
  ],
  "faq": [{{"question": "...", "answer": "...", "citation": <citation>}}],
  "insufficient": true|false,
  "followup_queries": ["a more specific search query", "..."]
}}

Rules:
- Only state what the provided content actually says. Never invent a visa requirement, fee,
  processing time, or filing channel not present in the source material.
- Every fact-bearing object MUST carry a citation with an http(s) url taken from the provided
  sources — never a URL you were not given.
- If a fact isn't stated anywhere in the content, use null for that field (or omit the object
  entirely) and set "insufficient": true with 1-3 "followup_queries" that would find it.
- "channel" is one of: embassy, consulate, visa_application_centre, accredited_travel_agency,
  online_portal, or null if not stated.
- "filer": "third_party" means official guidance requires filing through an accredited
  agency/visa application centre rather than directly with the embassy/consulate — state this as
  a fact for the applicant to act on, never as something the tool cannot help with.
{_CITATION_RULE}
{_FOLLOWUP_RULE}
"""

INTAKE_SYSTEM = f"""You are an immigration intake-questionnaire designer. Given scraped official
visa-application-form and requirements content, produce the plain-language questions an applicant
must answer to prepare this specific filing.

Return JSON only, no markdown fences:
{{
  "questions": [
    {{
      "key": "short_snake_case_key",
      "prompt": "Plain-language question for the applicant",
      "type": "string|boolean|integer|enum|date",
      "options": ["opt1", "opt2"], // required for enum, omit otherwise
      "required": true,
      "section": "1. Personal Information | 2. Trip & Purpose | 3. Accommodation | 4. Financial & Sponsor | 5. Employment & Study | 6. Travel History | 7. Local Connections | 8. Document Readiness",
      "show_when": {{"key": "parent_question_key", "equals": "expected_value"}}, // optional conditional branching
      "citation": <citation>
    }}
  ],
  "insufficient": true|false,
  "followup_queries": ["...", "..."]
}}

Rules:
- Derive questions from the actual official form/requirements content provided.
- DYNAMIC COUNTRY & TOUR-TYPE TAILORING:
  The questionnaire and modules must dynamically reflect the destination country (e.g. Japan, UK, US) and the specific type of tour/visit:
  1. Personal Information: full_name, date_of_birth, nationality, current_residence_country, passport_number, passport_issue_date, passport_expiry_date, marital_status.
  2. Trip & Tour Type:
     - planned_arrival_date, stay_duration_days, main_purpose
     - tour_type (enum: independent_tourism, package_tour_via_agency, visiting_relatives_or_acquaintances, short_term_business)
     - when tour_type == "package_tour_via_agency": tour_agency_name, package_booking_reference, receiving_agency_in_destination
     - when tour_type == "visiting_relatives_or_acquaintances": host_full_name, host_relationship, host_residency_status, host_address, is_host_guaranteeing_expenses
     - when tour_type == "independent_tourism": cities_to_visit, schedule_of_stay_ready
     - when tour_type == "short_term_business": inviting_company_name, business_meeting_purpose, inviting_contact_person
  3. Accommodation (country-specific):
     - accommodation_type (enum: hotel, airbnb, relative_or_friend_home, company_dormitory, other)
     - accommodation_booked (boolean)
     - accommodation_address (string)
  4. Financial & Sponsor (country-specific):
     - trip_payer (enum: myself, parent, spouse, employer, host_sponsor, other_sponsor)
     - when trip_payer != "myself": sponsor_name, sponsor_relationship, sponsor_occupation, sponsor_financial_proof_available
     - estimated_savings_available, bank_statement_available (6 months)
  5. Employment & Occupation (use show_when branching):
     - occupation (enum: employed, student, business_owner, freelancer, unemployed, retired)
     - when occupation == "employed": employer_name, job_title, monthly_salary, employment_start_date, approved_leave_secured
     - when occupation == "student": educational_institution, student_course, current_semester, student_leave_approved
     - when occupation == "business_owner": business_name, trade_license_number, annual_revenue
     - when occupation == "unemployed": financial_support_source
  6. Travel History & Compliance:
     - traveled_internationally_before (boolean)
     - when traveled_internationally_before == "true": countries_visited (string)
     - visited_destination_before (boolean)
     - prior_visa_refusal_any_country (boolean)
     - prior_overstay_history (boolean)
  7. Country-Specific Requirements (e.g. for Japan: Japanese guarantor / Invitation details; for UK: TB screening if applicable; for US: 214(b) home ties):
     - relatives_or_friends_in_destination (boolean)
     - when relatives_or_friends_in_destination == "true": connection_details (string)
- Branching: Do NOT ask every question upfront. Use "show_when" with {{"key": "parent_key", "equals": "expected_value"}} so that package tour fields only appear for package tours, sponsor fields only appear when sponsored, student fields only for students, and host/guarantor fields only when visiting hosts.
- "options" is required and non-empty for type "enum"; omit it otherwise.
- Every question needs a citation pointing to the official source URL.
- Group related questions under clear, intuitive "section" titles matching the destination flow.
- If the content only supports a handful of generic questions and doesn't cover the real form,
  set "insufficient": true and suggest "followup_queries" that would find the actual form.
{_CITATION_RULE}
{_FOLLOWUP_RULE}
"""

ELIGIBILITY_SYSTEM = f"""You are an immigration eligibility-rule extractor. Given scraped official
eligibility-criteria content and the applicant's own answers so far, extract the published,
checkable eligibility rules for this specific case — never your own judgment on whether they pass.

Return JSON only, no markdown fences:
{{
  "rules": [
    {{
      "key": "answer_key_this_rule_checks",
      "operator": "equals|min|max|in|nationality_in|not_empty",
      "value": "the published threshold or expected value",
      "failure_status": "fail|at_risk|out_of_scope",
      "message": "plain-language explanation of this rule",
      "citation": <citation>
    }}
  ],
  "insufficient": true|false,
  "followup_queries": ["...", "..."]
}}

Rules:
- "key" should match an answer already given by the applicant (see "Applicant's answers so far"
  in the prompt) wherever the source content ties a criterion to something the applicant stated.
- Only extract criteria explicitly published by the official source — never infer a rule from
  general knowledge, and never state whether this specific applicant passes or fails; the
  operator/value/key trio is all the caller needs to check that deterministically.
- If the content doesn't cover eligibility criteria for this exact case, set "insufficient": true
  with "followup_queries" that would find them.
{_CITATION_RULE}
{_FOLLOWUP_RULE}
"""

DOCUMENTS_SYSTEM = f"""You are an immigration document-checklist extractor. Given scraped official
document-requirement content, the applicant's answers, and (if available) their eligibility
screening result, extract the personalized document checklist for this specific case.

Return JSON only, no markdown fences:
{{
  "documents": [
    {{
      "code": "short_snake_case_code",
      "name": {{"en": "English name"}},
      "how_to_obtain": {{"en": "Where/how to get this document"}},
      "why_required": {{"en": "Why this document is required for this case"}},
      "is_required": true,
      "citation": <citation>
    }}
  ],
  "insufficient": true|false,
  "followup_queries": ["...", "..."]
}}

Rules:
- Only list documents the official source actually names as required or recommended for this
  visa/purpose — tailor to the applicant's stated nationality/residence/purpose where the source
  ties requirements to those facts (e.g. proof of residence for a third-country applicant).
- Distinguish required (true) from recommended (false) exactly as the source does.
- If content doesn't cover the document list for this case, set "insufficient": true with
  "followup_queries" that would find it.
{_CITATION_RULE}
{_FOLLOWUP_RULE}
"""

FORMS_SYSTEM = f"""You are an immigration form-mapping extractor. Given scraped official form and
form-instructions content plus the applicant's answers, identify the official form(s) this filing
requires and map each answer to the form field it belongs on.

Return JSON only, no markdown fences:
{{
  "forms": [
    {{
      "code": "official_form_code_or_short_name",
      "version": "YYYY-MM or the form's stated edition date",
      "official_title": "Full official form name",
      "citation": <citation>,
      "field_mappings": [
        {{
          "form_field": "section.field_name",
          "answer_key": "matches an applicant answer key",
          "required": true
        }}
      ]
    }}
  ],
  "insufficient": true|false,
  "followup_queries": ["...", "..."]
}}

Rules:
- Only map a field the official form/instructions actually define — never invent a field.
- "answer_key" should match the applicant's answer keys given in the prompt wherever the form
  asks for something already answered; where it asks for something not yet answered, use a new
  short snake_case key so the field can still be tracked (the caller will backfill an intake
  question for it).
- If the content doesn't identify the actual official form, set "insufficient": true with
  "followup_queries" that would find it (e.g. searching the form's official name/number).
{_CITATION_RULE}
{_FOLLOWUP_RULE}
"""

STAGE_SYSTEMS: dict[Stage, str] = {
    "admissibility": ADMISSIBILITY_SYSTEM,
    "intake": INTAKE_SYSTEM,
    "eligibility": ELIGIBILITY_SYSTEM,
    "documents": DOCUMENTS_SYSTEM,
    "forms": FORMS_SYSTEM,
}


def build_stage_queries(request: StageResearchRequest) -> list[str]:
    """Context-aware search queries for one stage of one case.

    Every stage names the destination and purpose so retrieved pages belong to this case even
    before the domain allowlist narrows them further; stages after ``intake`` fold in what the
    applicant has actually answered so the search is case-specific, not just scope-specific.
    """
    dest = country_label(request.destination_code)
    purpose = request.purpose_code.lower().replace("_", " ")
    action = request.action_code.lower().replace("_", " ")
    nationality = country_label(request.nationality)
    residence = country_label(request.residence_country)
    ctx = request.context

    if request.stage == "admissibility":
        queries = [
            f"does a {nationality} citizen need a visa to visit {dest} for {purpose}".strip(),
            f"{dest} visa requirements for {nationality} citizens {purpose}".strip(),
        ]
        if residence and residence != dest:
            queries.append(f"{dest} embassy or consulate in {residence} visa application")
            queries.append(
                f"{dest} visa accredited travel agency application centre {residence}"
            )
        return [q for q in queries if q]

    if request.stage == "intake":
        queries = [
            f"{dest} {purpose} visa {action} application form questions required information",
            f"{dest} {purpose} visa {action} official application form fields",
        ]
        if nationality:
            queries.append(f"{dest} {purpose} visa application form {nationality} citizens")
        return queries

    if request.stage == "eligibility":
        queries = [
            f"{dest} {purpose} visa {action} eligibility criteria requirements official",
            f"{dest} {purpose} visa financial requirements proof of funds",
        ]
        if nationality:
            queries.append(f"{dest} {purpose} visa eligibility {nationality} citizens official")
        return queries

    if request.stage == "documents":
        queries = [f"{dest} {purpose} visa {action} required documents checklist official"]
        if nationality and residence and nationality != residence:
            queries.append(
                f"{dest} {purpose} visa documents {nationality} citizen resident in {residence}"
            )
        findings = ctx.get("eligibility_findings") or []
        if any(isinstance(f, dict) and f.get("status") == "at_risk" for f in findings):
            queries.append(f"{dest} {purpose} visa additional supporting documents borderline case")
        return queries

    if request.stage == "forms":
        return [
            f"{dest} {purpose} visa {action} official application form download",
            f"{dest} visa application form official government website",
        ]

    return []


def _build_user_prompt(request: StageResearchRequest, content_block: str) -> str:
    dest = country_label(request.destination_code)
    nationality = country_label(request.nationality)
    residence = country_label(request.residence_country)
    now = datetime.now(UTC)

    lines = [
        f"Destination: {dest}",
        f"Visa/purpose: {request.purpose_code}",
        f"Action: {request.action_code}",
    ]
    if nationality:
        lines.append(f"Applicant nationality: {nationality}")
    if residence and residence != nationality:
        lines.append(f"Applicant current residence: {residence}")

    answers = request.context.get("answers")
    if answers:
        lines.append("Applicant's answers so far: " + json.dumps(answers, default=str))

    findings = request.context.get("eligibility_findings")
    if findings:
        lines.append("Eligibility screening findings: " + json.dumps(findings, default=str))

    lines.append(f"Today's date: {now.strftime('%Y-%m-%d')}")
    lines.append("")
    lines.append("Scraped content from official sources:")
    lines.append("")
    lines.append(content_block or "(no readable content retrieved)")
    lines.append("")
    lines.append("Return JSON only, per the schema in your system instructions.")
    return "\n".join(lines)


# Keys whose value is a single object (default {}) rather than a list (default []) when absent.
_OBJECT_KEYS = frozenset({"admission", "filing_channel", "process"})


def _stage_payload(stage: Stage, data: dict[str, Any]) -> dict[str, Any]:
    """Keep only the stage's substantive keys, defaulting missing ones to an empty value."""
    payload: dict[str, Any] = {}
    for key in _STAGE_CONTENT_KEYS[stage]:
        value = data.get(key)
        if value is not None:
            payload[key] = value
        else:
            payload[key] = {} if key in _OBJECT_KEYS else []
    return payload


class AgenticStageResearcher:
    """Runs one pipeline stage's live research for one case (or, for ``admissibility``, one
    scope+nationality+residence — no case exists yet).

    Round 1: build queries from context -> search (mission-domain-aware) -> scrape -> LLM
    extract. If the model reports ``insufficient`` and offers follow-up queries, round 2 widens
    the page set with those specific searches and re-extracts once over the union — this is the
    concrete "search with an LLM for additional info" behavior; a full multi-turn tool-calling
    agent is a natural later upgrade, not required to stop static per-scope content.
    """

    def __init__(self, *, search: SearchClient, chat: ChatClient, settings: Settings) -> None:
        self._search = search
        self._chat = chat
        self._settings = settings

    async def research_stage(self, request: StageResearchRequest) -> StageResearchResult:
        domains = official_domains_for(request.destination_code, request.nationality)
        queries = build_stage_queries(request)

        hits = await self._search_all(queries, domains)
        urls = [h.url for h in hits[: self._settings.scrape_max_pages]]
        content = await scrape_pages(
            urls,
            timeout_seconds=self._settings.tavily_timeout_seconds,
            page_chars=self._settings.scrape_page_chars,
        )

        raw = await self._extract(request, content)

        followups = raw.get("followup_queries") if isinstance(raw, dict) else None
        if raw.get("insufficient") and isinstance(followups, list) and followups:
            log.info(
                "agentic.followup_round",
                stage=request.stage,
                destination=request.destination_code,
                queries=followups[:_MAX_FOLLOWUP_QUERIES],
            )
            more_hits = await self._search_all(
                [str(q) for q in followups[:_MAX_FOLLOWUP_QUERIES]], domains
            )
            more_urls = [h.url for h in more_hits if h.url not in urls][
                : self._settings.scrape_max_pages
            ]
            if more_urls:
                more_content = await scrape_pages(
                    more_urls,
                    timeout_seconds=self._settings.tavily_timeout_seconds,
                    page_chars=self._settings.scrape_page_chars,
                )
                if more_content:
                    combined = content + more_content
                    raw = await self._extract(request, combined)
                    content = combined

        source_pages = [
            {"url": c["url"], "title": "", "retrieved_at": datetime.now(UTC).isoformat()}
            for c in content
        ]
        return StageResearchResult(
            stage=request.stage,
            items=_stage_payload(request.stage, raw),
            source_pages=source_pages,
            insufficient=bool(raw.get("insufficient")),
            researched_at=datetime.now(UTC).isoformat(),
        )

    async def _search_all(self, queries: list[str], domains: list[str] | None) -> list[Any]:
        all_hits: list[Any] = []
        for query in queries:
            hits = await self._search.search(query, domains=domains)
            all_hits.extend(hits)
            log.info("agentic.search", query=query, results=len(hits))
        seen: set[str] = set()
        unique: list[Any] = []
        for hit in all_hits:
            if hit.url not in seen:
                seen.add(hit.url)
                unique.append(hit)
        return unique

    async def _extract(
        self, request: StageResearchRequest, content: list[dict[str, str]]
    ) -> dict[str, Any]:
        system = STAGE_SYSTEMS[request.stage]
        content_block = "\n\n".join(
            f"=== Source {i + 1}: {c['url']} ===\n{c['text']}" for i, c in enumerate(content)
        )
        user_prompt = _build_user_prompt(request, content_block)
        try:
            reply = await self._chat.complete(system=system, user=user_prompt)
            data = extract_json(reply)
        except Exception as exc:  # noqa: BLE001 - any LLM/network failure degrades gracefully
            log.warning("agentic.llm_failed", stage=request.stage, error=str(exc))
            data = None
        if data is None:
            log.warning("agentic.extraction_failed", stage=request.stage)
            return {"insufficient": True, "followup_queries": []}
        return data
