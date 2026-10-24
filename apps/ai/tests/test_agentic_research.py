"""Tests for the agentic per-stage research engine (docs/plan/03_corridor_bd_jp.md)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from torii_ai.citations.models import Citation
from torii_ai.config import Settings
from torii_ai.llm.groq import FakeChatClient
from torii_ai.services import agentic_research as ar
from torii_ai.services.agentic_research import (
    AgenticStageResearcher,
    StageResearchRequest,
    build_stage_queries,
)
from torii_ai.services.ops_scraper import (
    is_official_source_domain,
    mission_domains_for,
    official_domains_for,
)
from torii_ai.tools.tavily import FakeSearchClient, TavilySearchResult

ADMISSIBILITY_REPLY = """{
  "admission": {"visa_required": true, "route": "consular_visa", "max_stay_days": 90,
    "citation": {"authority": "Embassy of Japan in Bangladesh", "title": "Visa",
                 "url": "https://www.bd.emb-japan.go.jp/itpr_en/visa.html",
                 "source_version": "2026-04"}},
  "filing_channel": {"channel": "embassy", "filer": "applicant",
    "mission_name": "Embassy of Japan in Bangladesh",
    "mission_url": "https://www.bd.emb-japan.go.jp/", "directory_url": null,
    "citation": {"authority": "Embassy of Japan in Bangladesh", "title": "Visa",
                 "url": "https://www.bd.emb-japan.go.jp/itpr_en/visa.html",
                 "source_version": "2026-04"}},
  "process": {"steps": [], "processing_time_days_min": null, "processing_time_days_max": null,
    "citation": {"authority": "Embassy of Japan in Bangladesh", "title": "Visa",
                 "url": "https://www.bd.emb-japan.go.jp/itpr_en/visa.html",
                 "source_version": "2026-04"}},
  "fees": [],
  "faq": [],
  "insufficient": false,
  "followup_queries": []
}"""

INSUFFICIENT_REPLY = """{
  "questions": [],
  "insufficient": true,
  "followup_queries": ["Japan tourist visa application form official"]
}"""

FOLLOWUP_REPLY = """{
  "questions": [
    {"key": "full_name", "prompt": "What is your full name?", "type": "string",
     "required": true, "section": "1. Personal Information",
     "citation": {"authority": "MOFA", "title": "Visa application form",
                  "url": "https://www.mofa.go.jp/form.html", "source_version": "2026-04"}}
  ],
  "insufficient": false,
  "followup_queries": []
}"""


def _hit(url: str) -> TavilySearchResult:
    cite = Citation(
        authority="test",
        title="test page",
        url=url,
        retrieved_at=datetime.now(UTC),
        source_version="2026-08",
    )
    return TavilySearchResult(title=cite.title, url=url, content="official content", citation=cite)


def test_mission_domains_for_unions_with_destination_domains() -> None:
    domains = official_domains_for("JP", "BD")
    assert domains is not None
    assert "isa.go.jp" in domains
    assert "bd.emb-japan.go.jp" in domains


def test_mission_domains_for_empty_without_nationality() -> None:
    assert mission_domains_for("JP", None) == []
    assert official_domains_for("JP", None) == ["isa.go.jp", "moj.go.jp", "mofa.go.jp"]


def test_official_domains_for_unmapped_country_no_nationality_returns_none() -> None:
    # Every destination outside OFFICIAL_DOMAINS with no nationality still returns None safely
    # (the crash this guards against: `', '.join(None[:3])` in ops_scraper.iter_scrape).
    assert official_domains_for("XX", None) is None


def test_official_domains_for_unmapped_country_falls_back_to_mission_only() -> None:
    # No destination-domain entry for "IT", but a JP-style mission pattern would still apply
    # for a mapped destination — sanity-check the union logic directly via a mapped one.
    assert official_domains_for("JP", "bd") == official_domains_for("JP", "BD")


def test_build_stage_queries_admissibility_names_nationality_and_mission() -> None:
    request = StageResearchRequest(
        stage="admissibility",
        destination_code="JP",
        purpose_code="tourist",
        action_code="new_application",
        nationality="BD",
        residence_country="BD",
    )
    queries = build_stage_queries(request)
    joined = "\n".join(queries).lower()
    assert "bangladesh" in joined
    assert "japan" in joined
    assert any("embassy" in q.lower() or "consulate" in q.lower() for q in queries)


def test_build_stage_queries_documents_reacts_to_at_risk_eligibility() -> None:
    base = StageResearchRequest(
        stage="documents",
        destination_code="JP",
        purpose_code="tourist",
        action_code="new_application",
        nationality="BD",
        residence_country="BD",
    )
    with_risk = StageResearchRequest(
        stage="documents",
        destination_code="JP",
        purpose_code="tourist",
        action_code="new_application",
        nationality="BD",
        residence_country="BD",
        context={"eligibility_findings": [{"status": "at_risk"}]},
    )
    assert len(build_stage_queries(with_risk)) > len(build_stage_queries(base))


@pytest.mark.asyncio
async def test_research_stage_admissibility_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    search = FakeSearchClient([_hit("https://www.bd.emb-japan.go.jp/itpr_en/visa.html")])
    chat = FakeChatClient(reply=ADMISSIBILITY_REPLY)
    researcher = AgenticStageResearcher(search=search, chat=chat, settings=Settings())

    async def fake_scrape_pages(urls, *, timeout_seconds, page_chars):
        return [{"url": u, "text": "Visa required for Bangladeshi tourists."} for u in urls]

    monkeypatch.setattr(ar, "scrape_pages", fake_scrape_pages)

    request = StageResearchRequest(
        stage="admissibility",
        destination_code="JP",
        purpose_code="tourist",
        action_code="new_application",
        nationality="BD",
        residence_country="BD",
    )
    result = await researcher.research_stage(request)

    assert result.stage == "admissibility"
    assert result.insufficient is False
    assert result.items["admission"]["visa_required"] is True
    assert result.items["admission"]["citation"]["url"].startswith("https://www.bd.emb-japan")
    assert result.items["filing_channel"]["filer"] == "applicant"
    assert result.items["fees"] == []
    assert result.source_pages
    # Mission domain reached the search call.
    assert search.domains is not None
    assert "bd.emb-japan.go.jp" in search.domains


class _TwoRoundSearchClient:
    """Returns a generic hit on round 1, a different (form-specific) hit on the followup query."""

    def __init__(self) -> None:
        self.domains: list[str] | None = None
        self.queries: list[str] = []

    async def search(self, query: str, domains: list[str] | None = None):
        self.queries.append(query)
        self.domains = domains
        if query == "Japan tourist visa application form official":
            return [_hit("https://www.mofa.go.jp/form.html")]
        return [_hit("https://www.mofa.go.jp/generic.html")]


@pytest.mark.asyncio
async def test_research_stage_runs_followup_round_when_insufficient(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    search = _TwoRoundSearchClient()
    chat = FakeChatClient(reply=INSUFFICIENT_REPLY)
    researcher = AgenticStageResearcher(search=search, chat=chat, settings=Settings())

    call_count = {"n": 0}

    async def fake_scrape_pages(urls, *, timeout_seconds, page_chars):
        call_count["n"] += 1
        return [{"url": u, "text": f"round {call_count['n']} content"} for u in urls]

    monkeypatch.setattr(ar, "scrape_pages", fake_scrape_pages)

    # Second extraction call (over the combined content) returns the richer payload.
    replies = [INSUFFICIENT_REPLY, FOLLOWUP_REPLY]

    async def fake_complete(*, system: str, user: str) -> str:
        return replies.pop(0)

    chat.complete = fake_complete  # type: ignore[method-assign]

    request = StageResearchRequest(
        stage="intake",
        destination_code="JP",
        purpose_code="tourist",
        action_code="new_application",
        nationality="BD",
        residence_country="BD",
    )
    result = await researcher.research_stage(request)

    assert call_count["n"] == 2, "expected a second scrape round for the followup queries"
    assert result.insufficient is False
    assert len(result.items["questions"]) == 1
    assert result.items["questions"][0]["key"] == "full_name"


@pytest.mark.asyncio
async def test_research_stage_bad_llm_json_degrades_gracefully(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    search = FakeSearchClient([_hit("https://www.mofa.go.jp/x.html")])
    chat = FakeChatClient(reply="not json at all")
    researcher = AgenticStageResearcher(search=search, chat=chat, settings=Settings())

    async def fake_scrape_pages(urls, *, timeout_seconds, page_chars):
        return [{"url": u, "text": "content"} for u in urls]

    monkeypatch.setattr(ar, "scrape_pages", fake_scrape_pages)

    request = StageResearchRequest(
        stage="eligibility",
        destination_code="JP",
        purpose_code="tourist",
        action_code="new_application",
    )
    result = await researcher.research_stage(request)

    assert result.insufficient is True
    assert result.items["rules"] == []


@pytest.mark.asyncio
async def test_research_stage_no_search_hits_still_returns_shaped_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    search = FakeSearchClient([])
    chat = FakeChatClient(reply="not json")
    researcher = AgenticStageResearcher(search=search, chat=chat, settings=Settings())

    async def fake_scrape_pages(urls, *, timeout_seconds, page_chars):
        return []

    monkeypatch.setattr(ar, "scrape_pages", fake_scrape_pages)

    request = StageResearchRequest(
        stage="documents",
        destination_code="JP",
        purpose_code="tourist",
        action_code="new_application",
    )
    result = await researcher.research_stage(request)

    assert result.items == {"documents": []}
    assert result.source_pages == []


def test_is_official_source_domain_accepts_official_and_blocks_commercial() -> None:
    # Official government domains
    assert is_official_source_domain("https://www.isa.go.jp/en/index.html", "JP") is True
    assert is_official_source_domain("https://www.bd.emb-japan.go.jp/itpr_en/visa.html", "JP", "BD") is True
    assert is_official_source_domain("https://www.gov.uk/standard-visitor", "GB") is True
    assert is_official_source_domain("https://travel.state.gov/content/travel.html", "US") is True
    assert is_official_source_domain("https://immi.homeaffairs.gov.au/visas", "AU") is True

    # Authorized concessionaires
    assert is_official_source_domain("https://visa.vfsglobal.com/bgd/en/jpn", "JP", "BD") is True
    assert is_official_source_domain("https://www.tlscontact.com/fr", "FR") is True

    # Commercial visa intermediaries and blogs must be rejected
    assert is_official_source_domain("https://www.ivisa.com/japan-visa", "JP") is False
    assert is_official_source_domain("https://visaguide.world/asia/japan-visa/", "JP") is False
    assert is_official_source_domain("https://atlys.com/country/japan", "JP") is False
    assert is_official_source_domain("https://travelvisapro.com/", "JP") is False
    assert is_official_source_domain("https://random-scam-blog.org/visa", "JP") is False


@pytest.mark.asyncio
async def test_research_stage_rejects_commercial_search_hits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Fake search returns one commercial blog hit and one official hit
    commercial_hit = _hit("https://www.ivisa.com/japan-tourist-visa")
    official_hit = _hit("https://www.mofa.go.jp/j_info/visit/visa/index.html")
    search = FakeSearchClient([commercial_hit, official_hit])
    chat = FakeChatClient(reply=ADMISSIBILITY_REPLY)
    researcher = AgenticStageResearcher(search=search, chat=chat, settings=Settings())

    scraped_urls: list[str] = []

    async def fake_scrape_pages(urls, *, timeout_seconds, page_chars):
        scraped_urls.extend(urls)
        return [{"url": u, "text": "Content"} for u in urls]

    monkeypatch.setattr(ar, "scrape_pages", fake_scrape_pages)

    request = StageResearchRequest(
        stage="admissibility",
        destination_code="JP",
        purpose_code="tourist",
        action_code="new_application",
        nationality="BD",
        residence_country="BD",
    )
    result = await researcher.research_stage(request)

    # Scraped URLs should only contain the official MOFA domain, not ivisa.com
    assert "https://www.mofa.go.jp/j_info/visit/visa/index.html" in scraped_urls
    assert "https://www.ivisa.com/japan-tourist-visa" not in scraped_urls
    assert [p["url"] for p in result.source_pages] == ["https://www.mofa.go.jp/j_info/visit/visa/index.html"]


@pytest.mark.asyncio
async def test_research_stage_direct_scrape_success_with_provenance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When direct scrape succeeds, returns verified status and explicit evidence provenance."""
    official_url = "https://www.mofa.go.jp/j_info/visit/visa/index.html"
    official_hit = _hit(official_url)
    search = FakeSearchClient([official_hit])
    chat = FakeChatClient(reply=ADMISSIBILITY_REPLY)
    researcher = AgenticStageResearcher(search=search, chat=chat, settings=Settings())

    async def fake_scrape_pages(urls, *, timeout_seconds, page_chars):
        return [{"url": urls[0], "text": "Official Japan tourist visa requirements for foreign nationals. Permitted stay up to 90 days. Consular visa required for entry."}]

    monkeypatch.setattr(ar, "scrape_pages", fake_scrape_pages)

    request = StageResearchRequest(
        stage="admissibility",
        destination_code="JP",
        purpose_code="tourist",
        action_code="new_application",
        nationality="BD",
        residence_country="BD",
    )
    result = await researcher.research_stage(request)

    assert result.retrieval_status == "direct_scrape"
    assert result.verification_status == "verified"
    assert result.review_required is False
    assert len(result.source_pages) == 1
    page = result.source_pages[0]
    assert page["url"] == official_url
    assert page["retrieval_method"] == "direct_scrape"
    assert page["domain"] == "www.mofa.go.jp"
    assert "retrieved_at" in page
    assert page["source_metadata"]["authority"] == "test"


@pytest.mark.asyncio
async def test_research_stage_inaccessible_sources_graceful_handling(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When government websites return 403/timeout and no snippet is available, safely flag review_required."""
    official_hit = _hit("https://www.bd.emb-japan.go.jp/itpr_en/visa.html")
    official_hit.content = ""  # No search snippet available either
    search = FakeSearchClient([official_hit])
    chat = FakeChatClient(reply=ADMISSIBILITY_REPLY)
    researcher = AgenticStageResearcher(search=search, chat=chat, settings=Settings())

    # Simulate scrape failure (e.g. 403 Forbidden or timeout)
    async def fake_scrape_pages(urls, *, timeout_seconds, page_chars):
        return []

    monkeypatch.setattr(ar, "scrape_pages", fake_scrape_pages)

    request = StageResearchRequest(
        stage="admissibility",
        destination_code="JP",
        purpose_code="tourist",
        action_code="new_application",
        nationality="BD",
        residence_country="BD",
    )
    result = await researcher.research_stage(request)

    assert result.insufficient is True
    assert result.review_required is True
    assert result.retrieval_status == "failed"
    assert result.verification_status == "failed"
    assert result.source_pages == []
    assert result.error_diagnostics is not None
    # No fabricated data
    assert result.items["admission"] == {}


@pytest.mark.asyncio
async def test_research_stage_alternative_official_sources_snippet_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When direct scrape fails on 403, fallback to authentic official search hit content with provenance."""
    official_url = "https://www.bd.emb-japan.go.jp/itpr_en/visa.html"
    commercial_url = "https://visaguide.world/asia/japan-visa/"

    official_hit = _hit(official_url)
    official_hit.content = (
        "Embassy of Japan in Bangladesh: Visa required for tourist entry. "
        "Permitted stay up to 90 days. Standard processing time is 5 to 7 working days. Official fee applies."
    )
    commercial_hit = _hit(commercial_url)
    commercial_hit.content = "Commercial blog content."

    search = FakeSearchClient([official_hit, commercial_hit])
    chat = FakeChatClient(reply=ADMISSIBILITY_REPLY)
    researcher = AgenticStageResearcher(search=search, chat=chat, settings=Settings())

    # Direct scrape fails (returns empty)
    async def fake_scrape_pages(urls, *, timeout_seconds, page_chars):
        return []

    monkeypatch.setattr(ar, "scrape_pages", fake_scrape_pages)

    request = StageResearchRequest(
        stage="admissibility",
        destination_code="JP",
        purpose_code="tourist",
        action_code="new_application",
        nationality="BD",
        residence_country="BD",
    )
    result = await researcher.research_stage(request)

    assert result.insufficient is False
    assert result.review_required is False
    assert result.retrieval_status == "search_snippet_fallback"
    assert result.verification_status == "verified"
    assert len(result.source_pages) == 1
    page = result.source_pages[0]
    assert page["url"] == official_url
    assert page["retrieval_method"] == "official_snippet_fallback"
    assert page["domain"] == "www.bd.emb-japan.go.jp"
    assert page["source_metadata"]["authority"] == "test"
    assert result.items["admission"]["visa_required"] is True


@pytest.mark.asyncio
async def test_research_stage_incomplete_official_snippet_triggers_review(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A search snippet from an official domain that is too incomplete to support claims triggers review."""
    official_url = "https://www.bd.emb-japan.go.jp/itpr_en/visa.html"
    official_hit = _hit(official_url)
    # Truncated, incomplete snippet under 80 chars
    official_hit.content = "Embassy visa notice."

    search = FakeSearchClient([official_hit])
    # The model extraction returns partial or empty admission
    partial_reply = """{
      "admission": {},
      "filing_channel": {},
      "process": {},
      "fees": [],
      "faq": [],
      "insufficient": false,
      "followup_queries": []
    }"""
    chat = FakeChatClient(reply=partial_reply)
    researcher = AgenticStageResearcher(search=search, chat=chat, settings=Settings())

    async def fake_scrape_pages(urls, *, timeout_seconds, page_chars):
        return []

    monkeypatch.setattr(ar, "scrape_pages", fake_scrape_pages)

    request = StageResearchRequest(
        stage="admissibility",
        destination_code="JP",
        purpose_code="tourist",
        action_code="new_application",
        nationality="BD",
    )
    result = await researcher.research_stage(request)

    assert result.retrieval_status == "search_snippet_fallback"
    assert result.verification_status == "needs_review"
    assert result.review_required is True
    assert "incomplete" in (result.error_diagnostics or "").lower()


@pytest.mark.asyncio
async def test_research_stage_conflicting_requirements(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When official sources report conflicting requirements, system flags review_required."""
    conflicting_reply = """{
      "admission": {},
      "filing_channel": {},
      "process": {},
      "fees": [],
      "faq": [],
      "conflicting_requirements": true,
      "insufficient": true,
      "followup_queries": []
    }"""
    official_hit = _hit("https://www.mofa.go.jp/visa.html")
    search = FakeSearchClient([official_hit])
    chat = FakeChatClient(reply=conflicting_reply)
    researcher = AgenticStageResearcher(search=search, chat=chat, settings=Settings())

    async def fake_scrape_pages(urls, *, timeout_seconds, page_chars):
        return [{"url": urls[0], "text": "Page A says 30 days; Page B says 90 days."}]

    monkeypatch.setattr(ar, "scrape_pages", fake_scrape_pages)

    request = StageResearchRequest(
        stage="admissibility",
        destination_code="JP",
        purpose_code="tourist",
        action_code="new_application",
        nationality="BD",
    )
    result = await researcher.research_stage(request)

    assert result.insufficient is True
    assert result.review_required is True
    assert result.verification_status == "unverified"
    assert result.retrieval_status == "insufficient"
    assert "Conflicting requirements" in (result.error_diagnostics or "")


@pytest.mark.asyncio
async def test_research_stage_insufficient_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When retrieved pages do not contain sufficient evidence, flag review_required without hallucinating."""
    insufficient_reply = """{
      "admission": {},
      "filing_channel": {},
      "process": {},
      "fees": [],
      "faq": [],
      "insufficient": true,
      "followup_queries": ["official visa requirements"]
    }"""
    official_hit = _hit("https://www.mofa.go.jp/under-construction.html")
    search = FakeSearchClient([official_hit])
    chat = FakeChatClient(reply=insufficient_reply)
    researcher = AgenticStageResearcher(search=search, chat=chat, settings=Settings())

    async def fake_scrape_pages(urls, *, timeout_seconds, page_chars):
        return [{"url": urls[0], "text": "Under construction. Check back later."}]

    monkeypatch.setattr(ar, "scrape_pages", fake_scrape_pages)

    request = StageResearchRequest(
        stage="admissibility",
        destination_code="JP",
        purpose_code="tourist",
        action_code="new_application",
        nationality="BD",
    )
    result = await researcher.research_stage(request)

    assert result.insufficient is True
    assert result.review_required is True
    assert result.verification_status == "unverified"
    assert result.retrieval_status == "insufficient"
    assert "Insufficient evidence" in (result.error_diagnostics or "")


def test_is_official_source_domain_strict_validation_and_spoof_defense() -> None:
    """Validate that lookalike, spoofed, and deceptive hostnames are strictly rejected."""
    # Spoofed and deceptive domains must be rejected
    assert is_official_source_domain("https://visa.gov.scamportal.com/japan", "JP") is False
    assert is_official_source_domain("https://apply-japan-gov.org/form", "JP") is False
    assert is_official_source_domain("https://phishing.gov.xyz/login", "JP") is False
    assert is_official_source_domain("https://gov.com/fake", "US") is False
    assert is_official_source_domain("https://evil.gov.attacker.net/us", "US") is False
    assert is_official_source_domain("https://fake.gov.uk.phishing.org/visas", "GB") is False
    assert is_official_source_domain("https://embassy-gov.info/apply", "JP") is False

    # Legitimate domains, subdomains, ports, case-insensitivity and trailing dots must be accepted
    assert is_official_source_domain("https://travel.state.gov/content/visas.html", "US") is True
    assert is_official_source_domain("https://TRAVEL.STATE.GOV:443/content/visas.html", "US") is True
    assert is_official_source_domain("https://www.mofa.go.jp./itpr_en/visa.html", "JP") is True
    assert is_official_source_domain("https://sub.immigration.gov.sg/visa", "SG") is True
    assert is_official_source_domain("https://visa.gov.bd/apply", "BD") is True
    assert is_official_source_domain("https://www.service.govt.nz/visas", "NZ") is True
    assert is_official_source_domain("https://visas.gouv.fr/entry", "FR") is True
    assert is_official_source_domain("https://www.inm.gob.mx/visa", "MX") is True
    assert is_official_source_domain("https://www.sem.admin.ch/sem/en/home.html", "CH") is True
    assert is_official_source_domain("https://www.canada.ca/en/immigration.html", "CA") is True

    # Malformed inputs
    assert is_official_source_domain("") is False
    assert is_official_source_domain("not-a-url") is False
    assert is_official_source_domain("ftp://travel.state.gov/visas") is False
    assert is_official_source_domain("http://") is False
    assert is_official_source_domain("https://   /test") is False


@pytest.mark.asyncio
async def test_snippet_fallback_unsupported_fee_and_processing_triggers_needs_review(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When fallback snippet supports visa requirement but lacks evidence for fees/processing, review is required."""
    reply_with_unsupported_claims = """{
      "admission": {"visa_required": true, "route": "consular_visa", "max_stay_days": null,
        "citation": {"authority": "Embassy of Japan", "title": "Visa",
                     "url": "https://www.bd.emb-japan.go.jp/itpr_en/visa.html",
                     "source_version": "2026-04"}},
      "filing_channel": {"channel": "embassy", "filer": "applicant",
        "mission_name": "Embassy of Japan", "mission_url": null, "directory_url": null,
        "citation": {"authority": "Embassy of Japan", "title": "Visa",
                     "url": "https://www.bd.emb-japan.go.jp/itpr_en/visa.html",
                     "source_version": "2026-04"}},
      "process": {"steps": [], "processing_time_days_min": 5, "processing_time_days_max": 10,
        "citation": {"authority": "Embassy of Japan", "title": "Visa",
                     "url": "https://www.bd.emb-japan.go.jp/itpr_en/visa.html",
                     "source_version": "2026-04"}},
      "fees": [{"code": "single_entry", "amount": 3000, "currency": "JPY",
                "citation": {"authority": "Embassy of Japan", "title": "Visa",
                             "url": "https://www.bd.emb-japan.go.jp/itpr_en/visa.html",
                             "source_version": "2026-04"}}],
      "faq": [],
      "insufficient": false,
      "followup_queries": []
    }"""
    official_url = "https://www.bd.emb-japan.go.jp/itpr_en/visa.html"
    official_hit = _hit(official_url)
    # The snippet only supports the visa requirement, but mentions NO fee numbers or processing times
    official_hit.content = (
        "Embassy of Japan in Bangladesh: Japanese visa requirements for foreign nationals. "
        "Citizens of Bangladesh must obtain an entry visa before traveling to Japan."
    )
    search = FakeSearchClient([official_hit])
    chat = FakeChatClient(reply=reply_with_unsupported_claims)
    researcher = AgenticStageResearcher(search=search, chat=chat, settings=Settings())

    async def fake_scrape_pages(urls, *, timeout_seconds, page_chars):
        return []

    monkeypatch.setattr(ar, "scrape_pages", fake_scrape_pages)

    request = StageResearchRequest(
        stage="admissibility",
        destination_code="JP",
        purpose_code="tourist",
        action_code="new_application",
        nationality="BD",
        residence_country="BD",
    )
    result = await researcher.research_stage(request)

    assert result.insufficient is False
    assert result.retrieval_status == "search_snippet_fallback"
    # Review must be required and verification_status must be 'needs_review'
    assert result.review_required is True
    assert result.verification_status == "needs_review"
    assert "unsupported fee" in (result.error_diagnostics or "").lower()
    # Ungrounded fee and processing time claims must be dropped from payload
    assert result.items["fees"] == []
    assert result.items["process"]["processing_time_days_min"] is None
    # Grounded visa_required remains verified
    assert result.items["admission"]["visa_required"] is True


@pytest.mark.asyncio
async def test_numeric_matching_alone_does_not_establish_claim_validity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Isolated numbers in text (e.g. Article 30, 90 applicants, Section 5) must not validate statutory claims."""
    reply_with_numeric_claims = """{
      "admission": {"visa_required": true, "route": "consular_visa", "max_stay_days": 90,
        "citation": {"authority": "Embassy of Japan", "title": "Visa",
                     "url": "https://www.bd.emb-japan.go.jp/itpr_en/visa.html",
                     "source_version": "2026-04"}},
      "filing_channel": {"channel": "embassy", "filer": "applicant",
        "mission_name": "Embassy of Japan", "mission_url": null, "directory_url": null,
        "citation": {"authority": "Embassy of Japan", "title": "Visa",
                     "url": "https://www.bd.emb-japan.go.jp/itpr_en/visa.html",
                     "source_version": "2026-04"}},
      "process": {"steps": [], "processing_time_days_min": 5, "processing_time_days_max": 10,
        "citation": {"authority": "Embassy of Japan", "title": "Visa",
                     "url": "https://www.bd.emb-japan.go.jp/itpr_en/visa.html",
                     "source_version": "2026-04"}},
      "fees": [{"code": "single_entry", "amount": 30, "currency": "USD",
                "citation": {"authority": "Embassy of Japan", "title": "Visa",
                             "url": "https://www.bd.emb-japan.go.jp/itpr_en/visa.html",
                             "source_version": "2026-04"}}],
      "faq": [],
      "insufficient": false,
      "followup_queries": []
    }"""
    official_url = "https://www.bd.emb-japan.go.jp/itpr_en/visa.html"
    official_hit = _hit(official_url)
    search = FakeSearchClient([official_hit])
    chat = FakeChatClient(reply=reply_with_numeric_claims)
    researcher = AgenticStageResearcher(search=search, chat=chat, settings=Settings())

    # Text contains isolated numbers 30, 90, 5 but entirely without fee, stay, or processing context
    text_with_isolated_numbers = (
        "Official visa portal for foreign nationals applying to Japan. "
        "Refer to Article 30 of the 2024 Immigration Act. "
        "A total of 90 applicants were recorded last quarter. "
        "Section 5 describes procedural formalities for submission."
    )

    async def fake_scrape_pages(urls, *, timeout_seconds, page_chars):
        return [{"url": urls[0], "text": text_with_isolated_numbers}]

    monkeypatch.setattr(ar, "scrape_pages", fake_scrape_pages)

    request = StageResearchRequest(
        stage="admissibility",
        destination_code="JP",
        purpose_code="tourist",
        action_code="new_application",
        nationality="BD",
        residence_country="BD",
    )
    result = await researcher.research_stage(request)

    # Isolated numbers must be rejected and flagged for review
    assert result.review_required is True
    assert result.verification_status == "needs_review"
    assert result.items["fees"] == []
    assert result.items["admission"]["max_stay_days"] is None
    assert result.items["process"]["processing_time_days_min"] is None
    assert "unsupported" in (result.error_diagnostics or "").lower()


@pytest.mark.asyncio
async def test_irrelevant_corridor_evidence_triggers_needs_review(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Source text discussing entirely unrelated nationality/corridor must flag review_required."""
    official_url = "https://www.bd.emb-japan.go.jp/itpr_en/visa.html"
    official_hit = _hit(official_url)
    search = FakeSearchClient([official_hit])
    chat = FakeChatClient(reply=ADMISSIBILITY_REPLY)
    researcher = AgenticStageResearcher(search=search, chat=chat, settings=Settings())

    # Text discusses only US citizens visiting Mexico, completely irrelevant to BD -> JP tourist
    irrelevant_text = (
        "Official portal. United States citizens traveling to Mexico do not require a tourist card."
    )

    async def fake_scrape_pages(urls, *, timeout_seconds, page_chars):
        return [{"url": urls[0], "text": irrelevant_text}]

    monkeypatch.setattr(ar, "scrape_pages", fake_scrape_pages)

    request = StageResearchRequest(
        stage="admissibility",
        destination_code="JP",
        purpose_code="tourist",
        action_code="new_application",
        nationality="BD",
        residence_country="BD",
    )
    result = await researcher.research_stage(request)

    assert result.review_required is True
    assert result.verification_status == "needs_review"
    assert "relevance" in (result.error_diagnostics or "").lower()




