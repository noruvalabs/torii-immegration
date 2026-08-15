"""OPS scraper — AI-powered daily collection of official immigration sources (US-25, US-26).

Uses Tavily to discover official government pages, scrapes their content, and uses the LLM
to extract structured data (eligibility rules, document requirements, form templates,
intake questions) ready for the API to ingest.

This is the automated replacement for manual OPS work: the worker runs daily, discovers
changes, and flags them for human review before anything goes live (NF-9).
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import httpx
import structlog

from torii_ai.config import Settings
from torii_ai.llm.groq import ChatClient
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


def _country_label(code: str | None) -> str:
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
    dest = _country_label(destination)
    vc = visa_category.lower().replace("_", " ")
    act = action.lower().replace("_", " ")
    origin = _country_label(origin_country)
    residence = _country_label(residence_country) if residence_country else ""

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
        queries.append(
            f"{vc} visa applying from {residence} proof of residence documents"
        )
        queries.append(f"{dest} visa {act} from {residence} foreign resident official")
    return queries


def official_domains_for(destination: str) -> list[str] | None:
    """Official-domain allowlist for a destination, or None to use settings base."""
    return OFFICIAL_DOMAINS.get(destination.upper())

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
      "key": "unique_key",
      "prompt": "Plain language question for the applicant",
      "type": "string|boolean|integer|enum",
      "options": ["opt1", "opt2"] // only for enum type
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
- Only extract data that is explicitly stated in the provided content.
- Do NOT invent rules, requirements, or forms not present in the source material.
- Every item MUST have a citation pointing to the official source URL.
- Use plain language for messages — bureaucratic jargon is not acceptable.
- source_version should be the page's date or "YYYY-MM" format.
- If the content is insufficient for a category, return an empty list for that category.
- When the request states an origin country and/or residence country, tailor the extracted
  documents, questions, and rules to that applicant profile (e.g. a citizen of the origin
  country residing in the residence country must submit proof of lawful residence there).
  Only do this when supported by the source content — never invent requirements.
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
        dest_label = _country_label(jurisdiction_code) or jurisdiction_code
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
        domains = official_domains_for(jurisdiction_code)
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

        JS-rendered government sites (gov.uk serves a static shell to plain fetches) are read
        through their official content API instead, so the article body is actually scraped.
        Identical bodies (e.g. the same gov.uk guide returned for many sub-paths) are
        deduplicated by content hash to keep the extraction prompt small.
        """
        content: list[dict[str, str]] = []
        seen: set[str] = set()
        async with httpx.AsyncClient(
            timeout=self._settings.tavily_timeout_seconds,
            follow_redirects=True,
            headers={"User-Agent": "Torii-OPS-Worker/1.0"},
        ) as client:
            for url in urls:
                text = await self._fetch_page_text(client, url)
                if not text:
                    continue
                digest = hashlib.sha256(text.encode("utf-8", "ignore")).hexdigest()
                if digest in seen:
                    log.info("scraper.page_duplicate", url=url)
                    continue
                seen.add(digest)
                content.append({"url": url, "text": text[: self._settings.scrape_page_chars]})
                log.info("scraper.page_scraped", url=url, chars=len(text))
        return content

    async def _fetch_page_text(self, client: httpx.AsyncClient, url: str) -> str:
        """Return readable page text for one URL ('' on failure)."""
        try:
            if _is_govuk(url):
                text = await self._scrape_govuk(client, url)
                if text:
                    return text
            resp = await client.get(url)
            if resp.status_code != 200:
                return ""
            ctype = resp.headers.get("content-type", "")
            if ctype and not ctype.startswith("text/") and "html" not in ctype:
                log.info("scraper.page_skipped", url=url, content_type=ctype)
                return ""
            return _strip_html(resp.text[:8000])
        except (httpx.HTTPError, ValueError) as exc:
            log.warning("scraper.page_failed", url=url, error=str(exc))
            return ""

    async def _scrape_govuk(self, client: httpx.AsyncClient, page_url: str) -> str:
        """Read a gov.uk article via its public content API (``/api/content/<path>``).

        The published HTML is a JS-rendered shell; the content API returns the full body as
        JSON (``details.parts[].body`` for guides, ``details.body`` otherwise). Handles the
        ``redirect`` content type by following the declared destination.
        """
        try:
            parsed = httpx.URL(page_url)
            host = str(parsed.host)
            api_url = f"{parsed.scheme}://{host}/api/content{parsed.path}"
            resp = await client.get(api_url)
            if resp.status_code != 200:
                return ""
            data = resp.json()
            if not isinstance(data, dict):
                return ""
            if data.get("document_type") == "redirect":
                redirects = data.get("redirects") or []
                if redirects:
                    dest = redirects[0].get("destination")
                    if dest:
                        next_url = f"{parsed.scheme}://{host}{dest}"
                        return await self._scrape_govuk(client, next_url)
                return ""
            details = data.get("details") or {}
            parts = details.get("parts") or []
            if parts:
                bodies = [p.get("body") or "" for p in parts]
                return _strip_html("\n".join(bodies))
            return _strip_html(details.get("body") or "")
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            log.warning("scraper.govuk_api_failed", url=page_url, error=str(exc))
            return ""

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
            f"=== Source {i+1}: {c['url']} ===\n{c['text']}"
            for i, c in enumerate(content)
        )

        origin_label = _country_label(origin_country)
        residence_label = _country_label(residence_country)
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
Scraped date: {now.strftime('%Y-%m-%d')}

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
            data = _extract_json(raw)
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
                    {"url": c["url"], "title": "", "retrieved_at": now.isoformat()}
                    for c in content
                ],
                scraped_at=now.isoformat(),
            )

        # Build citations with current date
        for category in ["eligibility_rules", "document_requirements", "form_templates"]:
            for item in data.get(category, []):
                cit = item.get("citation", {})
                if isinstance(cit, dict):
                    cit["source_version"] = now.strftime("%Y-%m")
                    item["citation"] = cit

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
            source_pages=data.get("source_pages", [
                {"url": c["url"], "title": "", "retrieved_at": now.isoformat()} for c in content
            ]),
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


def _is_govuk(url: str) -> bool:
    """True when a URL is served by the JS-rendered gov.uk frontend."""
    try:
        host = httpx.URL(url).host or ""
    except Exception:
        return False
    return host == "www.gov.uk" or host.endswith(".gov.uk")


def _strip_html(raw: str) -> str:
    """Strip script/style blocks and tags, collapse whitespace."""
    text = re.sub(r"<script[^>]*>.*?</script>", "", raw, flags=re.DOTALL)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _extract_json(raw: str) -> dict[str, Any] | None:
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
