"""OPS worker API — trigger scraping jobs and receive scraped data (US-25, US-26).

Endpoints:
- POST /ai/ops/scrape — trigger a scrape job for a jurisdiction
- POST /ai/ops/discover-scopes — list the visa routes a destination publishes (US-29)
- POST /ai/ops/ingest — receive scraped data and forward to the system-of-record API
- GET  /ai/ops/status — check worker status and last scrape time
"""

from __future__ import annotations

from typing import Any

import httpx
import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from torii_ai.config import Settings, get_settings
from torii_ai.llm.groq import FakeChatClient, GroqChatClient
from torii_ai.llm.nvidia import NvidiaChatClient
from torii_ai.services.ops_scraper import OpsScraper
from torii_ai.services.scope_discovery import ScopeDiscovery
from torii_ai.tools.tavily import FakeSearchClient, TavilyClient

log = structlog.get_logger()

router = APIRouter(prefix="/ai/ops", tags=["ops"])

# In-memory status tracking (process-local, like sessions)
_last_scrape: dict[str, Any] = {}

# A discovery reply is a list of routes and procedures, each a handful of short fields, so it
# reserves a fraction of what requirement extraction needs. This matters beyond cost: Groq
# counts the reserved output against the tokens-per-minute allowance, so a budget sized to
# the reply is the difference between an answer and a 413. A floor under the configured
# budget: a deployment that allows less gets less.
DISCOVERY_MAX_TOKENS = 4000


class ScrapeRequest(BaseModel):
    jurisdiction_code: str = Field(min_length=2, max_length=8, examples=["JP"])
    visa_category: str = Field(default="work", max_length=32)
    action: str = Field(default="renewal", max_length=32)
    origin_country: str | None = Field(default=None, max_length=8)
    residence_country: str | None = Field(default=None, max_length=8)
    return_payload: bool = False


class ScrapeResponse(BaseModel):
    status: str
    jurisdiction_code: str
    eligibility_rules: int
    document_requirements: int
    intake_questions: int
    form_templates: int
    source_pages: int
    message: str
    eligibility_rules_payload: list[dict[str, Any]] = Field(default_factory=list)
    document_requirements_payload: list[dict[str, Any]] = Field(default_factory=list)
    intake_questions_payload: list[dict[str, Any]] = Field(default_factory=list)
    form_templates_payload: list[dict[str, Any]] = Field(default_factory=list)
    scraped_at: str = ""
    visa_category: str = ""
    action: str = ""


class IngestRequest(BaseModel):
    jurisdiction_code: str
    visa_category: str
    action: str
    eligibility_rules: list[dict[str, Any]] = Field(default_factory=list)
    document_requirements: list[dict[str, Any]] = Field(default_factory=list)
    intake_questions: list[dict[str, Any]] = Field(default_factory=list)
    form_templates: list[dict[str, Any]] = Field(default_factory=list)
    source_pages: list[dict[str, Any]] = Field(default_factory=list)
    scraped_at: str = ""


class DiscoverScopesRequest(BaseModel):
    jurisdiction_code: str = Field(min_length=2, max_length=8, examples=["CA"])
    # The applicant nationality a mission-in-origin-country page would be published for;
    # widens the search to that embassy's domain when the destination has one.
    origin_country: str | None = Field(default=None, max_length=8)


class DiscoveredScope(BaseModel):
    code: str
    name: str
    description: str = ""
    citation: dict[str, Any] = Field(default_factory=dict)


class DiscoverScopesResponse(BaseModel):
    jurisdiction_code: str
    visa_categories: list[DiscoveredScope] = Field(default_factory=list)
    case_actions: list[DiscoveredScope] = Field(default_factory=list)
    source_pages: list[dict[str, Any]] = Field(default_factory=list)
    discovered_at: str = ""


class StatusResponse(BaseModel):
    running: bool
    last_scrape: dict[str, Any]
    tavily_configured: bool
    nvidia_configured: bool


def _build_scraper(settings: Settings) -> OpsScraper:
    """Build an OpsScraper with real or fake clients based on config."""
    search = TavilyClient(settings) if settings.tavily_api_key else FakeSearchClient()
    # Prefer Groq (high speed, sub-second latency) when configured, then NVIDIA NIM, then fake.
    if settings.groq_api_key:
        chat = GroqChatClient(settings)
        extract_chat = (
            GroqChatClient(settings, model=settings.groq_extract_model)
            if settings.groq_extract_model
            else GroqChatClient(settings)
        )
    elif settings.nvidia_api_key:
        chat = NvidiaChatClient(settings)
        extract_chat = NvidiaChatClient(settings)
    else:
        chat = FakeChatClient()
        extract_chat = None
    return OpsScraper(search=search, chat=chat, settings=settings, extract_chat=extract_chat)


def _build_discovery(settings: Settings) -> ScopeDiscovery:
    """Build a ScopeDiscovery with real or fake clients based on config.

    Extraction here is a plain list, not reasoning, so it takes the same non-reasoning model
    preference ``_build_scraper`` applies to its structured pass — and its own, much smaller
    output budget, because the reply is a few dozen short objects rather than a full set of
    requirements. See :data:`DISCOVERY_MAX_TOKENS`.
    """
    search = TavilyClient(settings) if settings.tavily_api_key else FakeSearchClient()
    if settings.groq_api_key:
        chat = GroqChatClient(
            settings,
            model=settings.groq_extract_model or None,
            max_tokens=min(DISCOVERY_MAX_TOKENS, settings.groq_max_tokens),
        )
    elif settings.nvidia_api_key:
        chat = NvidiaChatClient(settings)
    else:
        chat = FakeChatClient()
    return ScopeDiscovery(search=search, chat=chat, settings=settings)


@router.post("/scrape", response_model=ScrapeResponse)
async def trigger_scrape(payload: ScrapeRequest) -> ScrapeResponse:
    """Trigger an AI-powered scrape job for a jurisdiction.

    Uses Tavily to discover official government pages, scrapes their content,
    and uses the LLM to extract structured immigration data.
    """
    global _last_scrape

    settings = get_settings()
    scraper = _build_scraper(settings)

    log.info("ops.scrape.start", jurisdiction=payload.jurisdiction_code)

    try:
        result = await scraper.scrape_jurisdiction(
            jurisdiction_code=payload.jurisdiction_code,
            visa_category=payload.visa_category,
            action=payload.action,
            origin_country=payload.origin_country,
            residence_country=payload.residence_country,
        )
    except Exception as exc:
        log.error("ops.scrape.failed", error=str(exc))
        raise HTTPException(status_code=500, detail=f"Scrape failed: {exc}") from exc

    _last_scrape = {
        "jurisdiction": payload.jurisdiction_code,
        "at": result.scraped_at,
        "rules": len(result.eligibility_rules),
        "docs": len(result.document_requirements),
        "questions": len(result.intake_questions),
        "forms": len(result.form_templates),
    }

    return ScrapeResponse(
        status="completed",
        jurisdiction_code=result.jurisdiction_code,
        eligibility_rules=len(result.eligibility_rules),
        document_requirements=len(result.document_requirements),
        intake_questions=len(result.intake_questions),
        form_templates=len(result.form_templates),
        source_pages=len(result.source_pages),
        message=f"Scraped {len(result.source_pages)} pages, extracted structured data.",
        eligibility_rules_payload=result.eligibility_rules if payload.return_payload else [],
        document_requirements_payload=(
            result.document_requirements if payload.return_payload else []
        ),
        intake_questions_payload=result.intake_questions if payload.return_payload else [],
        form_templates_payload=result.form_templates if payload.return_payload else [],
        scraped_at=result.scraped_at,
        visa_category=result.visa_category,
        action=result.action,
    )


@router.post("/scrape/stream")
async def trigger_scrape_stream(payload: ScrapeRequest):
    """Stream NDJSON progress events while scraping, then a final complete payload.

    Each line is a JSON object: ``{"type":"progress",...}`` or
    ``{"type":"complete","scrape":{...ScrapeResponse fields...}}``.
    """
    import json

    from fastapi.responses import StreamingResponse

    settings = get_settings()
    scraper = _build_scraper(settings)

    async def generate():
        global _last_scrape
        try:
            async for event in scraper.iter_scrape(
                jurisdiction_code=payload.jurisdiction_code,
                visa_category=payload.visa_category,
                action=payload.action,
                origin_country=payload.origin_country,
                residence_country=payload.residence_country,
            ):
                if event.get("type") == "progress":
                    yield (
                        json.dumps(
                            {
                                "type": "progress",
                                "key": event.get("key"),
                                "label": event.get("label"),
                                "detail": event.get("detail") or "",
                            }
                        )
                        + "\n"
                    )
                elif event.get("type") == "complete":
                    from torii_ai.services.ops_scraper import ScrapeResult

                    result = event.get("result")
                    if not isinstance(result, ScrapeResult):
                        continue
                    _last_scrape = {
                        "jurisdiction": payload.jurisdiction_code,
                        "at": result.scraped_at,
                        "rules": len(result.eligibility_rules),
                        "docs": len(result.document_requirements),
                        "questions": len(result.intake_questions),
                        "forms": len(result.form_templates),
                    }
                    complete = {
                        "type": "complete",
                        "status": "completed",
                        "jurisdiction_code": result.jurisdiction_code,
                        "eligibility_rules": len(result.eligibility_rules),
                        "document_requirements": len(result.document_requirements),
                        "intake_questions": len(result.intake_questions),
                        "form_templates": len(result.form_templates),
                        "source_pages": len(result.source_pages),
                        "message": (
                            f"Scraped {len(result.source_pages)} pages, extracted structured data."
                        ),
                        "eligibility_rules_payload": (
                            result.eligibility_rules if payload.return_payload else []
                        ),
                        "document_requirements_payload": (
                            result.document_requirements if payload.return_payload else []
                        ),
                        "intake_questions_payload": (
                            result.intake_questions if payload.return_payload else []
                        ),
                        "form_templates_payload": (
                            result.form_templates if payload.return_payload else []
                        ),
                        "source_pages_list": result.source_pages,
                        "scraped_at": result.scraped_at,
                        "visa_category": result.visa_category,
                        "action": result.action,
                    }
                    yield json.dumps(complete) + "\n"
        except Exception as exc:
            log.error("ops.scrape.stream_failed", error=str(exc))
            yield json.dumps({"type": "error", "detail": str(exc)}) + "\n"

    return StreamingResponse(generate(), media_type="application/x-ndjson")


@router.post("/ingest")
async def ingest_scraped_data(payload: IngestRequest) -> dict[str, str]:
    """Receive scraped data and forward to the system-of-record API.

    This endpoint is called by the worker after a successful scrape to store
    the extracted data in the API's knowledge base, eligibility rules,
    document requirements, and form templates.
    """
    settings = get_settings()

    if not settings.api_base_url:
        raise HTTPException(status_code=500, detail="API base URL not configured")

    # Forward to the API's management endpoints
    headers = {"Content-Type": "application/json"}
    if settings.service_token:
        headers["Authorization"] = f"Bearer {settings.service_token}"

    results: list[str] = []

    # Ingest eligibility rules
    if payload.eligibility_rules:
        try:
            async with httpx.AsyncClient(timeout=settings.api_timeout_seconds) as client:
                resp = await client.post(
                    f"{settings.api_base_url}/v1/admin/ops/eligibility-rules",
                    headers=headers,
                    json={
                        "jurisdiction_code": payload.jurisdiction_code,
                        "visa_category": payload.visa_category,
                        "action": payload.action,
                        "rules": payload.eligibility_rules,
                    },
                )
                if resp.status_code < 300:
                    results.append(f"eligibility_rules: {len(payload.eligibility_rules)} rules")
                else:
                    log.warning("ops.ingest.eligibility_failed", status=resp.status_code)
        except Exception as exc:
            log.warning("ops.ingest.eligibility_error", error=str(exc))

    # Ingest document requirements
    if payload.document_requirements:
        try:
            async with httpx.AsyncClient(timeout=settings.api_timeout_seconds) as client:
                resp = await client.post(
                    f"{settings.api_base_url}/v1/admin/ops/document-requirements",
                    headers=headers,
                    json={
                        "jurisdiction_code": payload.jurisdiction_code,
                        "visa_category": payload.visa_category,
                        "action": payload.action,
                        "items": payload.document_requirements,
                    },
                )
                if resp.status_code < 300:
                    results.append(
                        f"document_requirements: {len(payload.document_requirements)} items"
                    )
                else:
                    log.warning("ops.ingest.checklist_failed", status=resp.status_code)
        except Exception as exc:
            log.warning("ops.ingest.checklist_error", error=str(exc))

    # Ingest intake questions
    if payload.intake_questions:
        try:
            async with httpx.AsyncClient(timeout=settings.api_timeout_seconds) as client:
                resp = await client.post(
                    f"{settings.api_base_url}/v1/admin/ops/intake-definitions",
                    headers=headers,
                    json={
                        "jurisdiction_code": payload.jurisdiction_code,
                        "visa_category": payload.visa_category,
                        "action": payload.action,
                        "questions": payload.intake_questions,
                    },
                )
                if resp.status_code < 300:
                    results.append(f"intake_questions: {len(payload.intake_questions)} questions")
                else:
                    log.warning("ops.ingest.intake_failed", status=resp.status_code)
        except Exception as exc:
            log.warning("ops.ingest.intake_error", error=str(exc))

    # Ingest form templates
    for form in payload.form_templates:
        try:
            async with httpx.AsyncClient(timeout=settings.api_timeout_seconds) as client:
                resp = await client.post(
                    f"{settings.api_base_url}/v1/admin/ops/form-templates",
                    headers=headers,
                    json={
                        "jurisdiction_code": payload.jurisdiction_code,
                        "visa_category": payload.visa_category,
                        "action": payload.action,
                        **form,
                    },
                )
                if resp.status_code < 300:
                    results.append(f"form_template: {form.get('code', 'unknown')}")
                else:
                    log.warning(
                        "ops.ingest.form_failed",
                        form=form.get("code"),
                        status=resp.status_code,
                    )
        except Exception as exc:
            log.warning("ops.ingest.form_error", form=form.get("code"), error=str(exc))

    log.info("ops.ingest.done", results=results)

    return {
        "status": "completed",
        "ingested": ", ".join(results) if results else "no data to ingest",
    }


@router.get("/status", response_model=StatusResponse)
async def get_status() -> StatusResponse:
    """Check worker status and configuration."""
    settings = get_settings()
    return StatusResponse(
        running=True,
        last_scrape=_last_scrape,
        tavily_configured=bool(settings.tavily_api_key),
        nvidia_configured=bool(settings.nvidia_api_key),
    )


@router.post("/discover-scopes", response_model=DiscoverScopesResponse)
async def discover_scopes(payload: DiscoverScopesRequest) -> DiscoverScopesResponse:
    """List the visa routes and application procedures a destination publishes.

    Called when an admin adds a country, so the panel can offer that country's real routes
    to switch on instead of a hardcoded guess. Every returned route carries the official
    page it was read off; ones that could not be cited are not returned (NF-2).
    """
    settings = get_settings()
    discovery = _build_discovery(settings)

    log.info("ops.discover.start", jurisdiction=payload.jurisdiction_code)
    try:
        result = await discovery.discover(
            jurisdiction_code=payload.jurisdiction_code,
            origin_country=payload.origin_country,
        )
    except Exception as exc:
        log.error("ops.discover.failed", error=str(exc))
        raise HTTPException(status_code=500, detail=f"Discovery failed: {exc}") from exc

    log.info(
        "ops.discover.done",
        jurisdiction=result.jurisdiction_code,
        categories=len(result.visa_categories),
        actions=len(result.case_actions),
    )
    return DiscoverScopesResponse(
        jurisdiction_code=result.jurisdiction_code,
        visa_categories=[DiscoveredScope(**c) for c in result.visa_categories],
        case_actions=[DiscoveredScope(**a) for a in result.case_actions],
        source_pages=result.source_pages,
        discovered_at=result.discovered_at,
    )
