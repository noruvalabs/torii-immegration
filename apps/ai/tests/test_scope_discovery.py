"""Reading a country's published visa routes off its own immigration pages.

The gate these tests guard is NF-2: a route reaches the admin panel only if it names the
official page it came from, and the citation has to point at a page the run actually read.
A model asked for a URL will produce a plausible one whether or not it saw it, so a
plausible-looking citation to somewhere else is a guess, and a guess is dropped.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from torii_ai.citations.models import Citation
from torii_ai.config import Settings
from torii_ai.llm.groq import FakeChatClient
from torii_ai.services import scope_discovery
from torii_ai.services.scope_discovery import (
    DISCOVERY_MAX_PAGES,
    DISCOVERY_PAGE_CHARS,
    MAX_CATEGORIES,
    ScopeDiscovery,
    build_discovery_queries,
    normalize_scopes,
    official_citation,
)
from torii_ai.tools.tavily import FakeSearchClient, TavilySearchResult

ISA_PAGE = "https://www.isa.go.jp/en/applications/procedures/index.html"

LLM_REPLY = """{
  "visa_categories": [
    {"code": "Highly Skilled Professional", "name": "Highly Skilled Professional - 高度専門職",
     "description": "Points-based fast track to permanent residency.",
     "citation": {"authority": "ISA", "title": "Statuses of residence",
                  "url": "https://www.isa.go.jp/en/applications/procedures/index.html"}},
    {"code": "student", "name": "Student - 留学",
     "description": "Study at a university, college, or language school.",
     "citation": {"authority": "ISA", "title": "Statuses of residence",
                  "url": "https://www.moj.go.jp/isa/applications/procedures/16-4.html"}},
    {"code": "invented", "name": "A route nobody published",
     "description": "No citation at all."}
  ],
  "case_actions": [
    {"code": "change_of_status", "name": "Change of status",
     "description": "Switch to a different route from inside Japan.",
     "citation": {"authority": "ISA", "title": "Procedures",
                  "url": "https://www.isa.go.jp/en/applications/procedures/index.html"}}
  ]
}"""


def _hit(url: str = ISA_PAGE) -> TavilySearchResult:
    cite = Citation(
        authority="ISA",
        title="Immigration procedures",
        url=url,
        retrieved_at=datetime.now(UTC),
        source_version="2026-08",
    )
    return TavilySearchResult(
        title=cite.title, url=url, content="Official Japanese immigration pages.", citation=cite
    )


def _fakes(
    reply: str = LLM_REPLY, hits: list[TavilySearchResult] | None = None
) -> tuple[ScopeDiscovery, FakeSearchClient, FakeChatClient]:
    """A discovery wired to fakes, returned alongside them so tests can read what was asked."""
    search = FakeSearchClient(hits if hits is not None else [_hit()])
    chat = FakeChatClient(reply=reply)
    return ScopeDiscovery(search=search, chat=chat, settings=Settings()), search, chat


def _discovery(reply: str = LLM_REPLY, hits: list[TavilySearchResult] | None = None):
    return _fakes(reply, hits)[0]


@pytest.fixture
def read_one_page(monkeypatch: pytest.MonkeyPatch):
    """Stand in for the network: every requested URL comes back with page text."""

    async def fake_scrape_pages(urls, **_kwargs):
        return [{"url": url, "text": "Statuses of residence and how to apply."} for url in urls]

    monkeypatch.setattr(scope_discovery, "scrape_pages", fake_scrape_pages)


# ── The citation gate ──────────────────────────────────────────────────────────


def test_a_citation_counts_when_it_points_at_a_host_we_read() -> None:
    hosts = {"isa.go.jp"}
    assert official_citation({"url": ISA_PAGE}, hosts) is not None
    # A subdomain of a read host is still that authority's page.
    assert official_citation({"url": "https://x.isa.go.jp/a"}, hosts) is not None


@pytest.mark.parametrize(
    "citation",
    [
        None,
        "https://www.isa.go.jp/a",  # a bare string, not a citation object
        {},
        {"url": ""},
        {"url": "isa.go.jp/en"},  # not an absolute URL
        {"url": "https://blog.example.com/japan-visas"},  # somewhere we never read
    ],
)
def test_a_citation_that_is_a_guess_does_not_count(citation: object) -> None:
    assert official_citation(citation, {"isa.go.jp"}) is None


def test_normalize_keeps_the_cited_and_slugs_the_code() -> None:
    kept = normalize_scopes(
        [
            {
                "code": "Highly Skilled Professional!",
                "name": "  高度専門職  ",
                "description": "Fast track.",
                "citation": {"url": ISA_PAGE, "authority": "ISA", "title": "Procedures"},
            },
            {"code": "uncited", "name": "Uncited"},
            {"code": "", "name": "No code and no name to slug from"},
            "not even a dict",
        ],
        allowed_hosts={"isa.go.jp"},
        limit=MAX_CATEGORIES,
    )
    assert [item["code"] for item in kept] == ["highly_skilled_professional"]
    assert kept[0]["name"] == "高度専門職"
    assert kept[0]["citation"]["url"] == ISA_PAGE


def test_normalize_keeps_the_first_of_a_repeated_code_and_honours_the_cap() -> None:
    items = [{"code": "work", "name": f"Work {i}", "citation": {"url": ISA_PAGE}} for i in range(3)]
    kept = normalize_scopes(items, allowed_hosts={"isa.go.jp"}, limit=MAX_CATEGORIES)
    assert [item["name"] for item in kept] == ["Work 0"]

    distinct = [
        {"code": f"route_{i}", "name": f"Route {i}", "citation": {"url": ISA_PAGE}}
        for i in range(5)
    ]
    assert len(normalize_scopes(distinct, allowed_hosts={"isa.go.jp"}, limit=2)) == 2


def test_normalize_of_a_non_list_is_empty_not_an_error() -> None:
    assert normalize_scopes({"code": "work"}, allowed_hosts={"isa.go.jp"}, limit=5) == []
    assert normalize_scopes(None, allowed_hosts={"isa.go.jp"}, limit=5) == []


# ── The queries and the search ─────────────────────────────────────────────────


def test_queries_name_the_destination_in_words_not_just_its_code() -> None:
    queries = build_discovery_queries("JP")
    assert queries
    assert all("japan" in query.lower() for query in queries)


# ── End to end, with the network stood in for ──────────────────────────────────


@pytest.mark.asyncio
async def test_discovery_returns_the_cited_routes_and_drops_the_rest(read_one_page) -> None:
    discovery = _discovery()

    result = await discovery.discover("JP")

    assert result.jurisdiction_code == "JP"
    codes = [item["code"] for item in result.visa_categories]
    # The HSP route's free-text code is slugged; the student route cites a sibling official
    # domain, which counts; the uncited one is gone.
    assert codes == ["highly_skilled_professional", "student"]
    assert "invented" not in codes
    assert [item["code"] for item in result.case_actions] == ["change_of_status"]
    assert result.source_pages[0]["url"] == ISA_PAGE
    assert result.discovered_at


@pytest.mark.asyncio
async def test_discovery_restricts_search_to_the_destinations_official_domains(
    read_one_page,
) -> None:
    discovery, search, _chat = _fakes()

    await discovery.discover("JP", origin_country="BD")

    # The destination's own domains, plus the mission in the applicant's country — that is
    # the page which states what a Bangladeshi applicant can actually apply for.
    domains = search.domains or []
    assert "isa.go.jp" in domains
    assert "bd.emb-japan.go.jp" in domains


@pytest.mark.asyncio
async def test_discovery_reads_shallowly_enough_to_fit_a_modest_token_allowance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Its own budget, not the requirement scraper's — a route list sits near the top."""
    seen: dict[str, object] = {}

    async def record(urls, **kwargs):
        seen["urls"] = list(urls)
        seen.update(kwargs)
        return [{"url": url, "text": "Statuses of residence."} for url in urls]

    monkeypatch.setattr(scope_discovery, "scrape_pages", record)
    hits = [_hit(f"{ISA_PAGE}?p={i}") for i in range(10)]

    await _discovery(hits=hits).discover("JP")

    assert len(seen["urls"]) == DISCOVERY_MAX_PAGES  # type: ignore[arg-type]
    assert seen["page_chars"] == DISCOVERY_PAGE_CHARS


@pytest.mark.asyncio
async def test_nothing_found_is_an_empty_result_not_a_failure() -> None:
    discovery = _discovery(hits=[])

    result = await discovery.discover("XX")

    assert result.visa_categories == []
    assert result.case_actions == []
    assert result.source_pages == []
    assert result.discovered_at


@pytest.mark.asyncio
async def test_unreadable_pages_yield_no_routes(monkeypatch: pytest.MonkeyPatch) -> None:
    async def nothing_readable(_urls, **_kwargs):
        return []

    monkeypatch.setattr(scope_discovery, "scrape_pages", nothing_readable)

    result = await _discovery().discover("JP")

    assert result.visa_categories == []
    assert result.source_pages == []


@pytest.mark.asyncio
async def test_an_unparseable_model_reply_keeps_the_pages_it_read(read_one_page) -> None:
    """The pages are still worth reporting: they say where the admin can look by hand."""
    result = await _discovery(reply="I could not do that.").discover("JP")

    assert result.visa_categories == []
    assert [page["url"] for page in result.source_pages] == [ISA_PAGE]


@pytest.mark.asyncio
async def test_the_prompt_names_the_pages_a_citation_must_use(read_one_page) -> None:
    discovery, _search, chat = _fakes()

    await discovery.discover("JP")

    prompt = chat.calls[0]["user"]
    assert ISA_PAGE in prompt
    assert "a citation must use one of these" in prompt
    assert "Japan" in prompt
