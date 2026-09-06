"""OPS scraper — AI-powered daily collection of official immigration sources (US-25, US-26).

Uses Tavily to discover official government pages, scrapes their content, and uses the LLM
to extract structured data (eligibility rules, document requirements, form templates,
intake questions) ready for the API to ingest.

This is the automated replacement for manual OPS work: the worker runs daily, discovers
changes, and flags them for human review before anything goes live (NF-9).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import httpx
import structlog

from torii_ai.citations.resolver import resolve_official_citation
from torii_ai.config import Settings
from torii_ai.llm.groq import ChatClient
from torii_ai.services.web_fetch import fetch_govuk_text, scrape_pages
from torii_ai.tools.tavily import SearchClient

log = structlog.get_logger()

# Official domains to constrain search to, per destination country. Search is restricted to
# these so every extracted requirement traces to a government source (NF-2). Unknown
# destinations fall back to the settings-level allowlist.
OFFICIAL_DOMAINS: dict[str, list[str]] = {
    "JP": ["isa.go.jp", "moj.go.jp", "mofa.go.jp"],
    "US": ["uscis.gov", "travel.state.gov", "state.gov", "cbp.gov", "ice.gov"],
    "UK": ["gov.uk", "homeoffice.gov.uk"],
    "GB": ["gov.uk", "homeoffice.gov.uk"],
    "CA": ["canada.ca", "cic.gc.ca"],
    "AU": ["homeaffairs.gov.au", "gov.au"],
    "NZ": ["immigration.govt.nz", "govt.nz"],
    "DE": ["bmi.bund.de", "auswaertiges-amt.de", "bund.de"],
    "FR": ["france-visas.gouv.fr", "gouv.fr"],
    "SG": ["ica.gov.sg"],
    "KR": ["visa.go.kr", "hikorea.go.kr"],
    "IN": ["indianvisaonline.gov.in", "mea.gov.in"],
    "TH": ["immigration.go.th"],
    "MY": ["imi.gov.my"],
    "VN": ["vietnamvisa.govt.vn", "gov.vn"],
    "PH": ["immigration.gov.ph"],
    "ID": ["imigrasi.go.id"],
}

# Diplomatic-mission domain patterns, keyed by destination country. ``{cc}`` is filled with
# the applicant's nationality's lowercase ISO-2 code, so a Bangladeshi applicant to Japan
# reaches ``bd.emb-japan.go.jp`` — the page that actually states the origin-country filing
# channel, document list, and fee, which the destination-only domains above never surface.
MISSION_DOMAIN_PATTERNS: dict[str, list[str]] = {
    "JP": ["{cc}.emb-japan.go.jp"],
    "US": ["{cc}.usembassy.gov"],
    "UK": ["gov.uk"],
    "GB": ["gov.uk"],
    "CA": ["international.gc.ca"],
    "AU": ["{cc}.embassy.gov.au"],
}


def mission_domains_for(destination: str, nationality: str | None) -> list[str]:
    """Mission-in-origin-country domains for a destination + applicant nationality.

    Empty when the destination has no known mission-domain pattern or no nationality was
    given — callers union this with :func:`official_domains_for`'s destination domains.
    """
    if not nationality:
        return []
    patterns = MISSION_DOMAIN_PATTERNS.get(destination.upper())
    if not patterns:
        return []
    cc = nationality.lower()
    return [pattern.format(cc=cc) for pattern in patterns]


_COUNTRY_NAMES: dict[str, str] = {
    "JP": "Japan",
    "US": "United States",
    "UK": "United Kingdom",
    "GB": "United Kingdom",
    "CA": "Canada",
    "AU": "Australia",
    "NZ": "New Zealand",
    "DE": "Germany",
    "FR": "France",
    "SG": "Singapore",
    "KR": "South Korea",
    "IN": "India",
    "TH": "Thailand",
    "MY": "Malaysia",
    "VN": "Vietnam",
    "PH": "Philippines",
    "ID": "Indonesia",
    "BD": "Bangladesh",
}


def country_label(code: str | None) -> str:
    if not code:
        return ""
    return _COUNTRY_NAMES.get(code.upper(), code.upper())


def build_queries(
    *,
    destination: str,
    visa_category: str,
    action: str,
    origin_country: str | None = None,
    residence_country: str | None = None,
) -> list[str]:
    """Build targeted search queries for an arbitrary country pair + purpose.

    Every query names the destination country and the visa purpose so the retrieved pages
    belong to this case even before the domain allowlist is applied.
    """
    dest = country_label(destination)
    vc = visa_category.lower().replace("_", " ")
    act = action.lower().replace("_", " ")
    origin = country_label(origin_country)
    residence = country_label(residence_country) if residence_country else ""

    queries = [
        f"{dest} {vc} visa {act} requirements official government",
        f"{dest} {vc} visa {act} required documents official",
        f"{dest} visitor visa application {act} checklist documentation",
        f"{vc} visa {act} eligibility criteria {dest} official",
        f"{dest} visa application form official government",
        f"{vc} visa financial requirements supporting documents {dest}",
    ]
    if origin:
        queries.append(f"{dest} {vc} visa {act} for {origin} citizens official")
    if residence and residence != dest:
        queries.append(f"{vc} visa applying from {residence} proof of residence documents")
        queries.append(f"{dest} visa {act} from {residence} foreign resident official")
    return queries


def official_domains_for(destination: str, nationality: str | None = None) -> list[str] | None:
    """Official-domain allowlist for a destination, unioned with mission-in-origin domains
    for ``nationality`` when known. ``None`` (only when nothing at all matches) tells the
    caller to fall back to the settings-level base allowlist.
    """
    dest_domains = OFFICIAL_DOMAINS.get(destination.upper())
    mission = mission_domains_for(destination, nationality)
    if not dest_domains and not mission:
        return None
    combined = list(dest_domains or [])
    for domain in mission:
        if domain not in combined:
            combined.append(domain)
    return combined


EXTRACT_SYSTEM = """You are an immigration data extractor. Given scraped government page content,
extract structured immigration data for a specific jurisdiction and visa category.

Return JSON only, no markdown fences:
{
  "eligibility_rules": [
    {
      "key": "string_key_matching_intake_answer",
      "operator": "equals|min|max|in",
      "value": "the threshold value",
      "failure_status": "fail|at_risk|out_of_scope",
      "message": "plain language explanation of this rule",
      "citation": {"authority": "...", "title": "...", "url": "...", "source_version": "..."}
    }
  ],
  "document_requirements": [
    {
      "code": "short_code_like_passport",
      "name": {"en": "English name", "ja": "Japanese name if applicable"},
      "how_to_obtain": {"en": "How to get this document"},
      "why_required": {"en": "Why this document is needed"},
      "is_required": true,
      "citation": {"authority": "...", "title": "...", "url": "...", "source_version": "..."}
    }
  ],
  "intake_questions": [
    {
      "key": "unique_snake_case_key",
      "prompt": "Plain language question for the applicant",
      "type": "string|boolean|integer|enum|date",
      "options": ["opt1", "opt2"], // only for enum type
      "required": true,
      "section": "1. Personal Information | 2. Trip & Purpose | 3. Accommodation | 4. Financial & Sponsor | 5. Employment & Study | 6. Travel History | 7. Local Connections | 8. Document Readiness",
      "show_when": {"key": "parent_key", "equals": "matching_value"} // optional branching
    }
  ],
  "form_templates": [
    {
      "code": "form_code",
      "version": "YYYY-MM",
      "official_title": "Full official form name",
      "field_mappings": [
        {"form_field": "section.field_name", "answer_key": "intake_key", "required": true}
      ],
      "citation": {"authority": "...", "title": "...", "url": "...", "source_version": "..."}
    }
  ],
  "source_pages": [
    {"url": "...", "title": "...", "retrieved_at": "..."}
  ]
}

Rules:
- Only extract data that is explicitly stated or required for the destination jurisdiction and visa category.
- DYNAMIC VISA CATEGORY & CORRIDOR TAILORING:
  The questionnaire, document requirements, and eligibility rules must dynamically reflect the destination country (e.g. UK, Japan, US) and the specific visa category:

  A. STUDENT VISAS (e.g. UK Student Route, Japan Student, US F-1):
     1. Identity & Passport: full_name, date_of_birth, nationality, current_residence_country, passport_number, passport_expiry_date.
     2. University & Course: cas_number (or COE / I-20 reference number), institution_name, course_title, academic_level, course_start_date.
     3. Financial Requirements: has_financial_evidence (28-day maintenance funds e.g. £1,334/mo London or £1,023/mo outside / ¥120,000/mo), tuition_fees_paid, financial_sponsor_type (self, parents, official_scholarship).
     4. Academic & Language: english_language_level_met (IELTS/SELT/degree in English), atas_certificate_required.
     5. Travel History & Compliance: prior_visa_refusal_any_country, prior_overstay_history, traveled_internationally_before.

  B. WORK & EMPLOYMENT VISAS (e.g. UK Skilled Worker, Japan Work, US H-1B):
     1. Identity & Passport: full_name, date_of_birth, nationality, passport_number, passport_expiry_date.
     2. Sponsorship & Job Details: cos_number (or Certificate of Eligibility / petition number), employer_name, job_title, annual_salary, occupation_code.
     3. Maintenance & Qualifications: has_financial_evidence, english_proficiency_met, relevant_experience_years.
     4. Compliance: prior_visa_refusal_any_country, prior_overstay_history.

  C. TOURIST / VISITOR VISAS (e.g. Standard Visitor, Japan Tourist, US B1/B2):
     1. Personal Information: full_name, date_of_birth, nationality, current_residence_country, passport_number, passport_expiry_date.
     2. Trip & Purpose: planned_arrival_date, stay_duration_days, main_purpose, tour_type (independent_tourism, package_tour_via_agency, visiting_relatives_or_acquaintances, short_term_business).
     3. Accommodation: accommodation_type, accommodation_booked, accommodation_address.
     4. Financial & Sponsor: trip_payer (myself, parent, spouse, employer, host_sponsor), bank_statement_available, estimated_savings_available.
     5. Employment & Ties: occupation (employed, student, business_owner, freelancer, retired), employer_name, approved_leave_secured.
     6. Travel History & Compliance: traveled_internationally_before, prior_visa_refusal_any_country, prior_overstay_history.

- CRITICAL SYNC RULE: Every key evaluated in "eligibility_rules" MUST have an exact matching question in "intake_questions" with the same "key". Never produce an eligibility rule for a key that does not appear in intake_questions.
- Branching: Do NOT ask every question upfront. Use "show_when" with {"key": "parent_key", "equals": "expected_value"} so that conditional fields only appear when relevant.
- Every item MUST have a citation pointing to the official source URL.
- Group related questions under clear, intuitive "section" titles matching the destination flow.
- Use plain language for prompts — avoid unnecessary bureaucratic jargon.
- When the request states an origin country and/or residence country (e.g. Bangladesh -> UK / Japan), tailor the questions, required documents (e.g. TB clearance, VFS Dhaka procedures), and eligibility rules directly to that corridor.
"""


@dataclass
class ScrapeResult:
    """Structured data extracted from government sources for one jurisdiction."""

    jurisdiction_code: str
    visa_category: str
    action: str
    origin_country: str | None = None
    residence_country: str | None = None
    eligibility_rules: list[dict[str, Any]] = field(default_factory=list)
    document_requirements: list[dict[str, Any]] = field(default_factory=list)
    intake_questions: list[dict[str, Any]] = field(default_factory=list)
    form_templates: list[dict[str, Any]] = field(default_factory=list)
    source_pages: list[dict[str, Any]] = field(default_factory=list)
    scraped_at: str = ""


class OpsScraper:
    """AI-powered scraper that discovers and extracts immigration data from official sources."""

    def __init__(
        self,
        *,
        search: SearchClient,
        chat: ChatClient,
        settings: Settings,
        extract_chat: ChatClient | None = None,
    ) -> None:
        self._search = search
        self._chat = chat
        self._settings = settings
        # Structured extraction prefers the dedicated non-reasoning model when provided; a
        # reasoning model's <think> blocks can truncate the JSON under the TPM ceiling.
        self._extract_chat = extract_chat or chat

    async def scrape_jurisdiction(
        self,
        jurisdiction_code: str,
        visa_category: str = "work",
        action: str = "renewal",
        origin_country: str | None = None,
        residence_country: str | None = None,
    ) -> ScrapeResult:
        """Scrape official sources for a jurisdiction and extract structured data."""
        result: ScrapeResult | None = None
        async for event in self.iter_scrape(
            jurisdiction_code=jurisdiction_code,
            visa_category=visa_category,
            action=action,
            origin_country=origin_country,
            residence_country=residence_country,
        ):
            if event.get("type") == "complete" and isinstance(event.get("result"), ScrapeResult):
                result = event["result"]
        if result is None:
            return ScrapeResult(
                jurisdiction_code=jurisdiction_code,
                visa_category=visa_category,
                action=action,
                origin_country=origin_country,
                residence_country=residence_country,
                scraped_at=datetime.now(UTC).isoformat(),
            )
        return result

    async def iter_scrape(
        self,
        jurisdiction_code: str,
        visa_category: str = "work",
        action: str = "renewal",
        origin_country: str | None = None,
        residence_country: str | None = None,
    ):
        """Yield progress events, then a final ``complete`` event with the ScrapeResult.

        Used for streaming research UIs: each event is a dict with ``type`` of
        ``progress`` or ``complete``. Progress events include key/label/detail.
        """
        dest_label = country_label(jurisdiction_code) or jurisdiction_code
        yield {
            "type": "progress",
            "key": "prepare",
            "label": f"Preparing research for {dest_label}",
            "detail": f"{visa_category.replace('_', ' ')} · {action.replace('_', ' ')}",
        }

        queries = build_queries(
            destination=jurisdiction_code,
            visa_category=visa_category,
            action=action,
            origin_country=origin_country,
            residence_country=residence_country,
        )
        domains = official_domains_for(jurisdiction_code, origin_country)
        domains_label = (
            ", ".join(domains[:3]) if domains else "the configured official-source allowlist"
        )

        yield {
            "type": "progress",
            "key": "search",
            "label": "Searching official government sources",
            "detail": f"{len(queries)} targeted queries on {domains_label}",
        }

        # Phase 1: Discover sources via Tavily (restricted to official destination domains)
        all_hits = []
        for i, query in enumerate(queries):
            hits = await self._search.search(query, domains=domains)
            all_hits.extend(hits)
            log.info("scraper.search", query=query, results=len(hits))
            if i == 0 or i == len(queries) - 1:
                yield {
                    "type": "progress",
                    "key": "search",
                    "label": "Searching official government sources",
                    "detail": f"Query {i + 1}/{len(queries)} · {len(hits)} hits",
                }

        # Deduplicate by URL
        seen_urls: set[str] = set()
        unique_hits = []
        for hit in all_hits:
            if hit.url not in seen_urls:
                seen_urls.add(hit.url)
                unique_hits.append(hit)

        log.info(
            "scraper.sources_discovered",
            count=len(unique_hits),
            jurisdiction=jurisdiction_code,
        )

        if not unique_hits:
            log.warning("scraper.no_sources", jurisdiction=jurisdiction_code)
            yield {
                "type": "progress",
                "key": "search",
                "label": "No official pages found yet",
                "detail": "Finishing with an empty discovery set",
            }
            result = ScrapeResult(
                jurisdiction_code=jurisdiction_code,
                visa_category=visa_category,
                action=action,
                origin_country=origin_country,
                residence_country=residence_country,
                scraped_at=datetime.now(UTC).isoformat(),
            )
            yield {"type": "complete", "result": result}
            return

        yield {
            "type": "progress",
            "key": "discover",
            "label": f"Found {len(unique_hits)} official pages",
            "detail": unique_hits[0].url if unique_hits else "",
        }

        # Phase 2: Scrape content from discovered pages
        urls = [h.url for h in unique_hits[: self._settings.scrape_max_pages]]
        yield {
            "type": "progress",
            "key": "fetch",
            "label": f"Reading {len(urls)} government page(s)",
            "detail": "Pulling eligibility and document guidance",
        }
        scraped_content = await self._scrape_pages(urls)
        yield {
            "type": "progress",
            "key": "fetch",
            "label": f"Read {len(scraped_content)} page(s) successfully",
            "detail": scraped_content[0]["url"] if scraped_content else "No readable content",
        }

        # Phase 3: Extract structured data using LLM
        yield {
            "type": "progress",
            "key": "extract",
            "label": "Extracting eligibility rules, documents, and forms",
            "detail": "Cross-checking citations against source pages",
        }
        extracted = await self._extract_data(
            content=scraped_content,
            jurisdiction_code=jurisdiction_code,
            visa_category=visa_category,
            action=action,
            origin_country=origin_country,
            residence_country=residence_country,
        )
        yield {
            "type": "progress",
            "key": "validate",
            "label": "Packaging research for your case",
            "detail": (
                f"{len(extracted.eligibility_rules)} rules · "
                f"{len(extracted.document_requirements)} documents · "
                f"{len(extracted.form_templates)} forms"
            ),
        }
        yield {"type": "complete", "result": extracted}

    async def _scrape_pages(self, urls: list[str]) -> list[dict[str, str]]:
        """Fetch page content from URLs with timeout and error handling.

        Delegates to :mod:`torii_ai.services.web_fetch`, shared with the per-stage agentic
        research engine so both scrape identically (gov.uk content-API handling, dedup by
        content hash).
        """
        return await scrape_pages(
            urls,
            timeout_seconds=self._settings.tavily_timeout_seconds,
            page_chars=self._settings.scrape_page_chars,
        )

    async def _scrape_govuk(self, client: httpx.AsyncClient, page_url: str) -> str:
        """Read a gov.uk article via its public content API. Delegates to ``web_fetch``."""
        return await fetch_govuk_text(client, page_url)

    async def _extract_data(
        self,
        content: list[dict[str, str]],
        jurisdiction_code: str,
        visa_category: str,
        action: str,
        origin_country: str | None = None,
        residence_country: str | None = None,
    ) -> ScrapeResult:
        """Use LLM to extract structured data from scraped content."""
        now = datetime.now(UTC)

        # Build the prompt with all scraped content
        content_block = "\n\n".join(
            f"=== Source {i + 1}: {c['url']} ===\n{c['text']}" for i, c in enumerate(content)
        )

        origin_label = country_label(origin_country)
        residence_label = country_label(residence_country)
        case_context = "Applicant profile: standard case for this destination."
        if origin_label and residence_label and origin_label != residence_label:
            case_context = (
                f"Applicant profile: a citizen of {origin_label} currently residing in "
                f"{residence_label}. Tailor documents/questions/rules to this profile."
            )
        elif origin_label:
            case_context = (
                f"Applicant profile: a citizen of {origin_label}. "
                "Tailor documents/questions/rules to this profile."
            )

        user_prompt = f"""Jurisdiction: {jurisdiction_code}
Visa category: {visa_category}
Action: {action}
{case_context}
Scraped date: {now.strftime("%Y-%m-%d")}

Scraped content from official government sources:

{content_block}

Extract the structured immigration data from these sources. Focus on:
1. Eligibility rules for {visa_category} visa {action} in {jurisdiction_code}
2. Required documents for this process
3. Intake questions needed from the applicant
4. Official forms that need to be filled out

Return JSON only."""

        try:
            raw = await self._extract_chat.complete(system=EXTRACT_SYSTEM, user=user_prompt)
            data = extract_json(raw)
        except Exception as exc:
            log.warning("scraper.llm_failed", error=str(exc))
            data = None

        if data is None:
            log.warning("scraper.extraction_failed", jurisdiction=jurisdiction_code)
            return ScrapeResult(
                jurisdiction_code=jurisdiction_code,
                visa_category=visa_category,
                action=action,
                origin_country=origin_country,
                residence_country=residence_country,
                source_pages=[
                    {"url": c["url"], "title": "", "retrieved_at": now.isoformat()} for c in content
                ],
                scraped_at=now.isoformat(),
            )

        default_url = (
            content[0]["url"]
            if content and content[0].get("url")
            else (
                "https://www.isa.go.jp/en/applications/procedures/16-1.html"
                if jurisdiction_code.upper() == "JP"
                else f"https://www.gov.{jurisdiction_code.lower()}/visa"
            )
        )
        dest_name = country_label(jurisdiction_code) or jurisdiction_code
        default_authority = f"{dest_name} Immigration Authority"

        # Normalize and guarantee specific valid citations with current date
        version_str = now.strftime("%Y-%m")
        for category in ["eligibility_rules", "document_requirements", "form_templates"]:
            for item in data.get(category, []):
                if isinstance(item, dict):
                    _normalize_item_citation(
                        item,
                        jurisdiction_code=jurisdiction_code,
                        visa_category=visa_category,
                        default_authority=default_authority,
                        default_url=default_url,
                        version=version_str,
                    )

        result = ScrapeResult(
            jurisdiction_code=jurisdiction_code,
            visa_category=visa_category,
            action=action,
            origin_country=origin_country,
            residence_country=residence_country,
            eligibility_rules=data.get("eligibility_rules", []),
            document_requirements=data.get("document_requirements", []),
            intake_questions=data.get("intake_questions", []),
            form_templates=data.get("form_templates", []),
            source_pages=data.get("source_pages")
            or [{"url": c["url"], "title": "", "retrieved_at": now.isoformat()} for c in content]
            or [
                {
                    "url": default_url,
                    "title": f"Official {dest_name} Immigration",
                    "retrieved_at": now.isoformat(),
                }
            ],
            scraped_at=now.isoformat(),
        )

        log.info(
            "scraper.extracted",
            jurisdiction=jurisdiction_code,
            eligibility_rules=len(result.eligibility_rules),
            document_requirements=len(result.document_requirements),
            intake_questions=len(result.intake_questions),
            form_templates=len(result.form_templates),
        )

        return result


def _normalize_item_citation(
    item: dict[str, Any],
    jurisdiction_code: str,
    visa_category: str,
    default_authority: str,
    default_url: str,
    version: str,
) -> None:
    item_key = str(
        item.get("key") or item.get("code") or item.get("name") or item.get("official_title") or ""
    )
    specific = resolve_official_citation(
        jurisdiction_code=jurisdiction_code,
        visa_category=visa_category,
        item_key_or_code=item_key,
        existing_citation=item.get("citation"),
        default_version=version,
    )
    item["citation"] = specific


def _fallback_structured_data(
    *,
    jurisdiction_code: str,
    visa_category: str,
    action: str,
    origin_country: str | None,
    residence_country: str | None,
    default_url: str,
    default_authority: str,
) -> dict[str, Any]:
    dest = country_label(jurisdiction_code) or jurisdiction_code
    cat_label = visa_category.replace("_", " ").title()
    act_label = action.replace("_", " ").title()
    now_str = datetime.now(UTC).strftime("%Y-%m")

    questions = [
        {
            "key": "full_name",
            "prompt": "What is your full name (as written in your passport)?",
            "type": "string",
            "required": True,
            "section": "1. Personal Information",
        },
        {
            "key": "nationality",
            "prompt": "What is your nationality / citizenship?",
            "type": "string",
            "required": True,
            "section": "1. Personal Information",
        },
        {
            "key": "passport_number",
            "prompt": "Passport number",
            "type": "string",
            "required": True,
            "section": "1. Personal Information",
        },
        {
            "key": "passport_expiry",
            "prompt": "Passport expiration date",
            "type": "date",
            "required": True,
            "section": "1. Personal Information",
        },
        {
            "key": "date_of_birth",
            "prompt": "Date of birth",
            "type": "date",
            "required": True,
            "section": "1. Personal Information",
        },
        {
            "key": "current_country",
            "prompt": "Current country of residence",
            "type": "string",
            "required": True,
            "section": "1. Personal Information",
        },
        {
            "key": "purpose_of_stay",
            "prompt": f"Detailed purpose for {cat_label} ({act_label})",
            "type": "string",
            "required": True,
            "section": "2. Trip & Purpose",
        },
        {
            "key": "planned_arrival_date",
            "prompt": f"Intended arrival date in {dest}",
            "type": "date",
            "required": True,
            "section": "2. Trip & Purpose",
        },
        {
            "key": "stay_duration_months",
            "prompt": "Intended duration of stay (months)",
            "type": "integer",
            "required": True,
            "section": "2. Trip & Purpose",
        },
        {
            "key": "has_host_or_sponsor",
            "prompt": "Do you have an inviting host institution, school, or employer in destination?",
            "type": "boolean",
            "required": True,
            "section": "3. Sponsor & Organization",
        },
        {
            "key": "sponsor_organization_name",
            "prompt": "Name of host school, university, employer, or sponsoring organization",
            "type": "string",
            "required": False,
            "section": "3. Sponsor & Organization",
            "show_when": {"key": "has_host_or_sponsor", "equals": True},
        },
        {
            "key": "has_sufficient_funds",
            "prompt": "Do you have verified proof of sufficient funds / financial sponsorship?",
            "type": "boolean",
            "required": True,
            "section": "4. Financial Support",
        },
        {
            "key": "financial_support_details",
            "prompt": "Total funds available or sponsor declaration details",
            "type": "string",
            "required": False,
            "section": "4. Financial Support",
        },
        {
            "key": "has_prior_visa_refusals",
            "prompt": "Have you ever had a visa refusal or immigration violation in any country?",
            "type": "boolean",
            "required": True,
            "section": "5. Compliance & History",
        },
    ]

    rules = [
        {
            "key": "passport_expiry",
            "operator": "not_empty",
            "value": None,
            "failure_status": "fail",
            "message": f"Must possess a valid passport recognized by {dest} immigration authorities.",
            "citation": resolve_official_citation(
                jurisdiction_code=jurisdiction_code,
                visa_category=visa_category,
                item_key_or_code="passport",
                default_version=now_str,
            ),
        },
        {
            "key": "has_sufficient_funds",
            "operator": "equals",
            "value": True,
            "failure_status": "fail",
            "message": f"Applicants must demonstrate adequate financial capability for the intended {cat_label} stay.",
            "citation": resolve_official_citation(
                jurisdiction_code=jurisdiction_code,
                visa_category=visa_category,
                item_key_or_code="funds",
                default_version=now_str,
            ),
        },
        {
            "key": "has_prior_visa_refusals",
            "operator": "equals",
            "value": False,
            "failure_status": "at_risk",
            "message": "Prior visa refusals or immigration violations require disclosure and supporting explanation.",
            "citation": resolve_official_citation(
                jurisdiction_code=jurisdiction_code,
                visa_category=visa_category,
                item_key_or_code="criminal",
                default_version=now_str,
            ),
        },
    ]

    documents = [
        {
            "code": "passport",
            "name": {
                "en": "Valid Passport (Bio-data & Signature Page)",
                "ja": "旅券（パスポート）写し",
            },
            "how_to_obtain": {
                "en": "Color copy of the bio-data page of your valid national passport."
            },
            "why_required": {
                "en": "Required for primary international identification and visa issuance."
            },
            "is_required": True,
            "citation": resolve_official_citation(
                jurisdiction_code=jurisdiction_code,
                visa_category=visa_category,
                item_key_or_code="passport",
                default_version=now_str,
            ),
        },
        {
            "code": "photo",
            "name": {
                "en": "Official Visa Photograph (45x35mm, White Background)",
                "ja": "写真（縦4cm×横3cm）",
            },
            "how_to_obtain": {
                "en": "Standard recent passport-style photograph taken within the last 3 months."
            },
            "why_required": {
                "en": "Required for visa certificate and immigration registration records."
            },
            "is_required": True,
            "citation": resolve_official_citation(
                jurisdiction_code=jurisdiction_code,
                visa_category=visa_category,
                item_key_or_code="photo",
                default_version=now_str,
            ),
        },
        {
            "code": "proof_of_funds",
            "name": {
                "en": "Proof of Financial Capability / Bank Statement",
                "ja": "経費支弁能力を証する文書",
            },
            "how_to_obtain": {
                "en": "Official bank balance certificate, bank statements (last 3-6 months), or sponsor financial guarantee."
            },
            "why_required": {
                "en": "Demonstrates capability to cover tuition, living expenses, and travel costs."
            },
            "is_required": True,
            "citation": resolve_official_citation(
                jurisdiction_code=jurisdiction_code,
                visa_category=visa_category,
                item_key_or_code="funds",
                default_version=now_str,
            ),
        },
        {
            "code": "sponsor_certificate",
            "name": {
                "en": "Certificate of Eligibility (COE) / Admission or Employment Letter",
                "ja": "在留資格認定証明書または受入機関文書",
            },
            "how_to_obtain": {
                "en": "Issued by the host institution, university, language school, or sponsoring entity."
            },
            "why_required": {
                "en": "Validates official acceptance, sponsoring status, and qualification for the immigration route."
            },
            "is_required": True,
            "citation": resolve_official_citation(
                jurisdiction_code=jurisdiction_code,
                visa_category=visa_category,
                item_key_or_code="work" if "work" in visa_category.lower() else "student",
                default_version=now_str,
            ),
        },
    ]

    forms = [
        {
            "code": f"{jurisdiction_code.lower()}_{visa_category.lower()}_application_form",
            "version": "2026-01",
            "official_title": f"{dest} {cat_label} Application Form",
            "field_mappings": [
                {"form_field": "applicant.full_name", "answer_key": "full_name", "required": True},
                {
                    "form_field": "applicant.nationality",
                    "answer_key": "nationality",
                    "required": True,
                },
                {
                    "form_field": "applicant.passport_number",
                    "answer_key": "passport_number",
                    "required": True,
                },
                {
                    "form_field": "applicant.date_of_birth",
                    "answer_key": "date_of_birth",
                    "required": True,
                },
                {"form_field": "stay.purpose", "answer_key": "purpose_of_stay", "required": True},
            ],
            "citation": resolve_official_citation(
                jurisdiction_code=jurisdiction_code,
                visa_category=visa_category,
                item_key_or_code="work"
                if "work" in visa_category.lower()
                else "student"
                if "student" in visa_category.lower()
                else "tourist",
                default_version=now_str,
            ),
        }
    ]

    return {
        "eligibility_rules": rules,
        "document_requirements": documents,
        "intake_questions": questions,
        "form_templates": forms,
    }


def extract_json(raw: str) -> dict[str, Any] | None:
    """Extract JSON from LLM response, handling markdown fences and <think> blocks."""
    text = raw.strip()
    # Reasoning models prepend a <think>...</think> deliberation block — drop it so the
    # final JSON (which follows it) is what gets parsed.
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            data = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return None
    return data if isinstance(data, dict) else None
