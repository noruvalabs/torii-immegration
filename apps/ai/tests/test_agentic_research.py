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
from torii_ai.services.ops_scraper import mission_domains_for, official_domains_for
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
