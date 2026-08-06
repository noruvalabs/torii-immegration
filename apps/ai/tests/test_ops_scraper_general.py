"""Tests for the generalized OPS scraper (per-destination domains + case-specific queries)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from torii_ai.citations.models import Citation
from torii_ai.config import Settings
from torii_ai.llm.groq import FakeChatClient
from torii_ai.services.ops_scraper import (
    OFFICIAL_DOMAINS,
    OpsScraper,
    ScrapeResult,
    build_queries,
    official_domains_for,
)
from torii_ai.tools.tavily import FakeSearchClient, TavilySearchResult

LLM_REPLY = """{
  "eligibility_rules": [
    {"key": "purpose", "operator": "in", "value": "visit", "failure_status": "fail",
     "message": "You must be visiting for a permitted purpose.",
     "citation": {"authority": "gov.uk", "title": "Standard Visitor",
                  "url": "https://www.gov.uk/standard-visitor"}}
  ],
  "document_requirements": [
    {"code": "passport", "name": {"en": "Passport"},
     "how_to_obtain": {"en": "Apply in your country"},
     "why_required": {"en": "Proves identity"}, "is_required": true,
     "citation": {"authority": "gov.uk", "title": "Documents",
                  "url": "https://www.gov.uk/standard-visitor/documents"}}
  ],
  "intake_questions": [
    {"key": "purpose", "prompt": "Why are you visiting the UK?", "type": "string"}
  ],
  "form_templates": [
    {"code": "visa4", "version": "2026-08", "official_title": "Visa application",
     "field_mappings": [{"form_field": "a.b", "answer_key": "purpose", "required": true}],
     "citation": {"authority": "gov.uk", "title": "Form", "url": "https://www.gov.uk/visa4"}}
  ],
  "source_pages": [{"url": "https://www.gov.uk/standard-visitor", "title": "Standard Visitor",
                    "retrieved_at": "2026-08-01"}]
}"""


def _hit(url: str = "https://www.gov.uk/standard-visitor") -> TavilySearchResult:
    cite = Citation(
        authority="gov.uk",
        title="Standard Visitor visa",
        url=url,
        retrieved_at=datetime.now(UTC),
        source_version="2026-08",
    )
    return TavilySearchResult(
        title=cite.title, url=url, content="Official UK visitor visa pages.", citation=cite
    )


def test_official_domains_for_known_destinations() -> None:
    assert official_domains_for("UK") == ["gov.uk", "homeoffice.gov.uk"]
    assert official_domains_for("gb") == ["gov.uk", "homeoffice.gov.uk"]  # case-insensitive
    assert "gov.uk" in OFFICIAL_DOMAINS["GB"]


def test_official_domains_for_unknown_returns_none() -> None:
    assert official_domains_for("XX") is None


def test_build_queries_include_origin_and_residence_context() -> None:
    queries = build_queries(
        destination="UK",
        visa_category="visitor",
        action="apply",
        origin_country="BD",
        residence_country="JP",
    )
    joined = "\n".join(queries).lower()
    assert "united kingdom" in joined
    assert "visitor" in joined
    # origin country named so results belong to this applicant profile
    assert "bangladesh" in joined
    # residence country included for cross-border applicants
    assert "japan" in joined


def test_build_queries_without_origin_or_residence() -> None:
    queries = build_queries(destination="JP", visa_category="work", action="renewal")
    assert queries
    assert all("japan" in q.lower() for q in queries)


@pytest.mark.asyncio
async def test_scrape_jurisdiction_uk_restricts_domains_and_uses_case_context() -> None:
    search = FakeSearchClient([_hit()])
    chat = FakeChatClient(reply=LLM_REPLY)
    scraper = OpsScraper(search=search, chat=chat, settings=Settings())

    async def fake_scrape_pages(urls: list[str]) -> list[dict[str, str]]:
        return [
            {
                "url": urls[0],
                "text": "Official Standard Visitor requirements for a Bangladeshi"
                " citizen residing in Japan.",
            }
        ]

    scraper._scrape_pages = fake_scrape_pages  # type: ignore[method-assign]

    result = await scraper.scrape_jurisdiction(
        "UK", visa_category="visitor", action="apply", origin_country="BD", residence_country="JP"
    )

    assert isinstance(result, ScrapeResult)
    assert result.jurisdiction_code == "UK"
    assert result.origin_country == "BD"
    assert result.residence_country == "JP"
    assert search.domains == ["gov.uk", "homeoffice.gov.uk"]
    assert search.queries, "expected at least one query"
    assert len(result.eligibility_rules) == 1
    assert len(result.document_requirements) == 1
    assert len(result.intake_questions) == 1
    assert len(result.form_templates) == 1
    assert result.form_templates[0]["citation"]["source_version"]  # source_version stamped
    assert result.scraped_at

    # The origin/residence made it into the extraction prompt (case-specific docs).
    assert "Bangladesh" in chat.calls[0]["user"]
    assert "Japan" in chat.calls[0]["user"]


@pytest.mark.asyncio
async def test_scrape_jurisdiction_empty_sources_preserves_case() -> None:
    search = FakeSearchClient([])
    scraper = OpsScraper(search=search, chat=FakeChatClient(), settings=Settings())

    result = await scraper.scrape_jurisdiction(
        "UK", visa_category="visitor", action="apply", origin_country="BD", residence_country="JP"
    )

    assert result.origin_country == "BD"
    assert result.residence_country == "JP"
    assert result.eligibility_rules == []
    assert result.source_pages == []


@pytest.mark.asyncio
async def test_scrape_jurisdiction_bad_llm_json_keeps_source_pages() -> None:
    search = FakeSearchClient([_hit()])
    chat = FakeChatClient(reply="this is not json")
    scraper = OpsScraper(search=search, chat=chat, settings=Settings())

    async def fake_scrape_pages(urls: list[str]) -> list[dict[str, str]]:
        return [{"url": urls[0], "text": "some official text"}]

    scraper._scrape_pages = fake_scrape_pages  # type: ignore[method-assign]

    result = await scraper.scrape_jurisdiction("UK", visa_category="visitor", action="apply")

    assert result.eligibility_rules == []
    assert result.document_requirements == []
    assert len(result.source_pages) == 1


@pytest.mark.asyncio
async def test_scrape_govuk_via_content_api() -> None:
    """gov.uk JS shell is read via its content API, not the empty HTML wrapper."""


    settings = Settings()
    scraper = OpsScraper(search=FakeSearchClient(), chat=FakeChatClient(), settings=settings)
    captured: list[str] = []

    class _FakeResp:
        def __init__(self, status_code: int, payload: dict) -> None:
            self.status_code = status_code
            self._payload = payload

        def json(self) -> dict:
            return self._payload

    class _FakeClient:
        async def get(self, url: str):
            captured.append(url)
            if url == "https://www.gov.uk/api/content/standard-visitor":
                return _FakeResp(200, {"document_type": "guide", "details": {
                    "parts": [{"body": "<p>You must be a genuine visitor.</p>"}]}})
            return _FakeResp(404, {})

    client = _FakeClient()
    text = await scraper._scrape_govuk(client, "https://www.gov.uk/standard-visitor")
    assert "genuine visitor" in text
    assert captured == ["https://www.gov.uk/api/content/standard-visitor"]


@pytest.mark.asyncio
async def test_scrape_govuk_follows_redirects() -> None:


    settings = Settings()
    scraper = OpsScraper(search=FakeSearchClient(), chat=FakeChatClient(), settings=settings)
    captured: list[str] = []

    class _FakeResp:
        def __init__(self, payload: dict) -> None:
            self.status_code = 200
            self._payload = payload

        def json(self) -> dict:
            return self._payload

    class _FakeClient:
        async def get(self, url: str):
            captured.append(url)
            if url == "https://www.gov.uk/api/content/standard-visitor-visa":
                return _FakeResp({"document_type": "redirect",
                    "redirects": [{"destination": "/standard-visitor"}]})
            return _FakeResp({"document_type": "guide", "details": {
                "body": "<h2>What you need to do</h2><p>Apply online.</p>"}})

    client = _FakeClient()
    text = await scraper._scrape_govuk(client, "https://www.gov.uk/standard-visitor-visa")
    assert "Apply online" in text
    assert captured == [
        "https://www.gov.uk/api/content/standard-visitor-visa",
        "https://www.gov.uk/api/content/standard-visitor",
    ]


@pytest.mark.asyncio
async def test_scrape_govuk_unknown_path_returns_empty() -> None:

    settings = Settings()
    scraper = OpsScraper(search=FakeSearchClient(), chat=FakeChatClient(), settings=settings)

    class _FakeResp:
        def __init__(self) -> None:
            self.status_code = 404

    class _FakeClient:
        async def get(self, url: str):
            return _FakeResp()

    text = await scraper._scrape_govuk(_FakeClient(), "https://www.gov.uk/not-found")
    assert text == ""
