"""OPS worker API — trigger scraping jobs and receive scraped data (US-25, US-26).

Endpoints:
- POST /ai/ops/scrape — trigger a scrape job for a jurisdiction
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
from torii_ai.llm.groq import FakeChatClient, GroqClient
from torii_ai.services.ops_scraper import OpsScraper, ScrapeResult
from torii_ai.tools.tavily import FakeSearchClient, TavilyClient

log = structlog.get_logger()

router = APIRouter(prefix="/ai/ops", tags=["ops"])

# In-memory status tracking (process-local, like sessions)
_last_scrape: dict[str, Any] = {}


class ScrapeRequest(BaseModel):
    jurisdiction_code: str = Field(min_length=2, max_length=8, examples=["JP"])
    visa_category: str = Field(default="work", max_length=32)
    action: str = Field(default="renewal", max_length=32)
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


class StatusResponse(BaseModel):
    running: bool
    last_scrape: dict[str, Any]
    tavily_configured: bool
    groq_configured: bool


def _build_scraper(settings: Settings) -> OpsScraper:
    """Build an OpsScraper with real or fake clients based on config."""
    search = TavilyClient(settings) if settings.tavily_api_key else FakeSearchClient()
    chat = GroqClient(settings) if settings.groq_api_key else FakeChatClient()
    return OpsScraper(search=search, chat=chat, settings=settings)


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
                    results.append(f"document_requirements: {len(payload.document_requirements)} items")
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
                    log.warning("ops.ingest.form_failed", form=form.get("code"), status=resp.status_code)
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
        groq_configured=bool(settings.groq_api_key),
    )
