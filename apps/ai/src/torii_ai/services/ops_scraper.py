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

from torii_ai.config import Settings
from torii_ai.llm.groq import ChatClient
from torii_ai.tools.tavily import SearchClient

log = structlog.get_logger()

# Jurisdiction-specific search queries — one set per country.
JURISDICTION_QUERIES: dict[str, list[str]] = {
    "JP": [
        "Japan Immigration Services Agency visa renewal requirements site:isa.go.jp",
        "Japan work visa extension requirements documentation site:moj.go.jp",
        "在留資格 更新 必要書類 入管府",
        "Japan Certificate of Eligibility COE requirements",
        "Japan residence card renewal process official",
        "Japan visa application form extension stay official",
    ],
    "US": [
        "H-1B specialty occupation requirements site:uscis.gov",
        "Form I-129 H-1B petition documents checklist site:uscis.gov",
        "H-1B extension of stay requirements USCIS",
        "H-1B specialty occupation degree requirement official",
        "USCIS H-1B Cap and petition filing process",
        "I-94 arrival departure record CBP official",
    ],
}

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
"""


@dataclass
class ScrapeResult:
    """Structured data extracted from government sources for one jurisdiction."""

    jurisdiction_code: str
    visa_category: str
    action: str
    eligibility_rules: list[dict[str, Any]] = field(default_factory=list)
    document_requirements: list[dict[str, Any]] = field(default_factory=list)
    intake_questions: list[dict[str, Any]] = field(default_factory=list)
    form_templates: list[dict[str, Any]] = field(default_factory=list)
    source_pages: list[dict[str, Any]] = field(default_factory=list)
    scraped_at: str = ""


class OpsScraper:
    """AI-powered scraper that discovers and extracts immigration data from official sources."""

    def __init__(self, *, search: SearchClient, chat: ChatClient, settings: Settings) -> None:
        self._search = search
        self._chat = chat
        self._settings = settings

    async def scrape_jurisdiction(
        self,
        jurisdiction_code: str,
        visa_category: str = "work",
        action: str = "renewal",
    ) -> ScrapeResult:
        """Scrape official sources for a jurisdiction and extract structured data."""
        queries = JURISDICTION_QUERIES.get(jurisdiction_code, [])
        if not queries:
            log.warning("scraper.no_queries", jurisdiction=jurisdiction_code)
            return ScrapeResult(
                jurisdiction_code=jurisdiction_code,
                visa_category=visa_category,
                action=action,
                scraped_at=datetime.now(UTC).isoformat(),
            )

        # Phase 1: Discover sources via Tavily
        all_hits = []
        for query in queries:
            hits = await self._search.search(query)
            all_hits.extend(hits)
            log.info("scraper.search", query=query, results=len(hits))

        # Deduplicate by URL
        seen_urls: set[str] = set()
        unique_hits = []
        for hit in all_hits:
            if hit.url not in seen_urls:
                seen_urls.add(hit.url)
                unique_hits.append(hit)

        log.info("scraper.sources_discovered", count=len(unique_hits), jurisdiction=jurisdiction_code)

        if not unique_hits:
            log.warning("scraper.no_sources", jurisdiction=jurisdiction_code)
            return ScrapeResult(
                jurisdiction_code=jurisdiction_code,
                visa_category=visa_category,
                action=action,
                scraped_at=datetime.now(UTC).isoformat(),
            )

        # Phase 2: Scrape content from discovered pages
        scraped_content = await self._scrape_pages([h.url for h in unique_hits[:8]])

        # Phase 3: Extract structured data using LLM
        extracted = await self._extract_data(
            content=scraped_content,
            jurisdiction_code=jurisdiction_code,
            visa_category=visa_category,
            action=action,
        )

        return extracted

    async def _scrape_pages(self, urls: list[str]) -> list[dict[str, str]]:
        """Fetch page content from URLs with timeout and error handling."""
        content: list[dict[str, str]] = []
        async with httpx.AsyncClient(
            timeout=self._settings.tavily_timeout_seconds,
            follow_redirects=True,
            headers={"User-Agent": "Torii-OPS-Worker/1.0"},
        ) as client:
            for url in urls:
                try:
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        text = resp.text[:8000]  # Limit to avoid token overflow
                        # Basic HTML stripping
                        text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL)
                        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
                        text = re.sub(r"<[^>]+>", " ", text)
                        text = re.sub(r"\s+", " ", text).strip()
                        if text:
                            content.append({"url": url, "text": text[:6000]})
                            log.info("scraper.page_scraped", url=url, chars=len(text))
                except (httpx.HTTPError, ValueError) as exc:
                    log.warning("scraper.page_failed", url=url, error=str(exc))
        return content

    async def _extract_data(
        self,
        content: list[dict[str, str]],
        jurisdiction_code: str,
        visa_category: str,
        action: str,
    ) -> ScrapeResult:
        """Use LLM to extract structured data from scraped content."""
        now = datetime.now(UTC)

        # Build the prompt with all scraped content
        content_block = "\n\n".join(
            f"=== Source {i+1}: {c['url']} ===\n{c['text']}"
            for i, c in enumerate(content)
        )

        user_prompt = f"""Jurisdiction: {jurisdiction_code}
Visa category: {visa_category}
Action: {action}
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
            raw = await self._chat.complete(system=EXTRACT_SYSTEM, user=user_prompt)
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
                source_pages=[{"url": c["url"], "title": "", "retrieved_at": now.isoformat()} for c in content],
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


def _extract_json(raw: str) -> dict[str, Any] | None:
    """Extract JSON from LLM response, handling markdown fences."""
    text = raw.strip()
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
