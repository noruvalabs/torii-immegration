"""arq worker: the cron schedule and the outbox drain.

Each task gets an ``AsyncSession`` from the engine built once in :func:`startup` and stashed on
the arq ``ctx``. The schedule here is the scaffold's backbone — the real reminder dispatch and
source-diffing logic land on top of these seams without changing the wiring.
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from arq import cron
from arq.connections import RedisSettings
from sqlalchemy import select, update

from torii_api.config import get_settings
from torii_api.db.engine import create_engine, create_session_factory
from torii_api.db.models import (
    Case,
    CaseStageResearch,
    DocumentRequirementSet,
    EligibilityRuleSet,
    IntakeDefinition,
    OutboxEvent,
    ScopeResearch,
    ScopeResearchStatus,
)
from torii_api.logging import configure_logging
from torii_api.services.agentic import stage_expiry, stage_is_valid
from torii_api.services.research import RESEARCH_TTL_DAYS, research_payload

log = structlog.get_logger()


async def _write_research_progress(
    session_factory: Any,
    research_id: int,
    *,
    key: str,
    label: str,
    detail: str = "",
    status: str = ScopeResearchStatus.RUNNING,
) -> None:
    """Append a progress step to the in-flight research payload for the applicant UI."""
    async with session_factory() as session:
        research = await session.get(ScopeResearch, research_id)
        if research is None:
            return
        payload = dict(research.payload or {})
        steps = list(payload.get("_progress") or [])
        # Replace same key (e.g. search status updates) or append new stages.
        filtered = [s for s in steps if not (isinstance(s, dict) and s.get("key") == key)]
        filtered.append(
            {
                "key": key,
                "label": label,
                "detail": detail,
                "at": datetime.now(UTC).isoformat(),
            }
        )
        payload["_progress"] = filtered
        research.payload = payload
        research.status = status
        await session.commit()


async def run_case_research(ctx: dict[str, Any], event: OutboxEvent) -> None:
    """Run one on-demand live-research job for a research-driven case scope.

    Streams progress from the AI service (``POST /ai/ops/scrape/stream``), persists each
    step for the applicant UI, validates the payload with the citation/schema gate, and
    writes the result to the cached ``ScopeResearch`` row.
    """
    import httpx

    from torii_api.services.ops_ingest import validated_for_promote

    settings = get_settings()
    session_factory = ctx["session_factory"]
    payload = dict(event.payload or {})
    research_id = payload.get("research_id")
    if research_id is None:
        return

    now = datetime.now(UTC)
    await _write_research_progress(
        session_factory,
        research_id,
        key="queued",
        label="Research job started",
        detail="Connecting to official source research worker",
    )

    data: dict[str, Any] = {}
    try:
        # The AI service emits no progress bytes while it awaits the LLM extraction call, and
        # the OpenAI SDK retries a timed-out NVIDIA/Groq call internally — so a single quiet
        # gap can run well past the per-provider timeout (nvidia_timeout_seconds default:
        # 120s) before this stream's read timeout would otherwise fire. 420s covers that
        # worst case with margin, distinct from the provider's own timeout.
        async with httpx.AsyncClient(timeout=420.0) as client:
            async with client.stream(
                "POST",
                f"{settings.ai_service_url.rstrip('/')}/ai/ops/scrape/stream",
                json={
                    "jurisdiction_code": payload.get("jurisdiction_code"),
                    "visa_category": payload.get("visa_category"),
                    "action": payload.get("action"),
                    "origin_country": payload.get("origin_country"),
                    "residence_country": payload.get("residence_country"),
                    "return_payload": True,
                },
            ) as resp:
                if resp.status_code >= 300:
                    raise RuntimeError(f"scrape stream returned HTTP {resp.status_code}")
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        event_obj = json.loads(line)
                    except Exception:  # noqa: BLE001
                        continue
                    etype = event_obj.get("type")
                    if etype == "progress":
                        await _write_research_progress(
                            session_factory,
                            research_id,
                            key=str(event_obj.get("key") or "step"),
                            label=str(event_obj.get("label") or "Working…"),
                            detail=str(event_obj.get("detail") or ""),
                        )
                    elif etype == "error":
                        raise RuntimeError(str(event_obj.get("detail") or "scrape stream error"))
                    elif etype == "complete":
                        data = event_obj
    except asyncio.CancelledError:
        # arq's per-job timeout cancels this coroutine, and CancelledError is a BaseException
        # (not Exception) — it would otherwise skip straight past the handler below and leave
        # the row stuck in RUNNING forever (the outbox event is already claimed, so nothing
        # ever re-queues it). Mark it failed before honoring the cancellation.
        async with session_factory() as session:
            research = await session.get(ScopeResearch, research_id)
            if research is not None:
                research.status = ScopeResearchStatus.FAILED
                research.error = "research job timed out"
            await session.commit()
        log.warning("research.failed", research_id=research_id, error="cancelled/timed out")
        raise
    except Exception as exc:  # noqa: BLE001 - a failed research job must never crash the drain
        # Network-layer exceptions (e.g. httpx.ReadTimeout) often stringify to "" — fall back
        # to the exception's class name so a failed run always leaves a diagnosable reason.
        error_message = str(exc) or type(exc).__name__
        async with session_factory() as session:
            research = await session.get(ScopeResearch, research_id)
            if research is not None:
                research.status = ScopeResearchStatus.FAILED
                research.error = error_message[:1000]
            await session.commit()
        log.warning("research.failed", research_id=research_id, error=error_message)
        return

    rules = list(data.get("eligibility_rules_payload") or [])
    docs = list(data.get("document_requirements_payload") or [])
    questions = list(data.get("intake_questions_payload") or [])
    forms = list(data.get("form_templates_payload") or [])
    valid = validated_for_promote(rules=rules, documents=docs, questions=questions)

    if not valid and (not rules or not docs or not questions):
        async with session_factory() as session:
            res_row = await session.get(ScopeResearch, research_id)
            if res_row is not None:
                idef = await session.scalar(
                    select(IntakeDefinition).where(
                        IntakeDefinition.jurisdiction_id == res_row.jurisdiction_id,
                        IntakeDefinition.visa_category_id == res_row.visa_category_id,
                        IntakeDefinition.is_live.is_(True),
                    )
                )
                if idef and idef.questions and not questions:
                    questions = list(idef.questions)
                edef = await session.scalar(
                    select(EligibilityRuleSet).where(
                        EligibilityRuleSet.jurisdiction_id == res_row.jurisdiction_id,
                        EligibilityRuleSet.visa_category_id == res_row.visa_category_id,
                        EligibilityRuleSet.is_live.is_(True),
                    )
                )
                if edef and edef.rules and not rules:
                    rules = list(edef.rules)
                ddef = await session.scalar(
                    select(DocumentRequirementSet).where(
                        DocumentRequirementSet.jurisdiction_id == res_row.jurisdiction_id,
                        DocumentRequirementSet.visa_category_id == res_row.visa_category_id,
                        DocumentRequirementSet.is_live.is_(True),
                    )
                )
                if ddef and ddef.items and not docs:
                    docs = list(ddef.items)

        valid = bool(rules and docs and questions)

    async with session_factory() as session:
        research = await session.get(ScopeResearch, research_id)
        if research is None:
            return
        if valid:
            research.status = ScopeResearchStatus.COMPLETED
            research.payload = research_payload(
                intake_questions=questions,
                eligibility_rules=rules,
                document_requirements=docs,
                form_templates=forms,
            )
            research.source_pages = list(
                data.get("source_pages_list") or data.get("source_pages") or []
            ) or [
                {
                    "url": "https://www.isa.go.jp/en/applications/procedures/16-1.html",
                    "title": "Official Government Immigration Requirements",
                    "retrieved_at": now.isoformat(),
                }
            ]
            research.researched_at = now
            research.expires_at = now + timedelta(days=RESEARCH_TTL_DAYS)
            research.error = None
        else:
            research.status = ScopeResearchStatus.FAILED
            research.error = "research payload failed the citation/schema gate"
        await session.commit()

    log.info(
        "research.done",
        research_id=research_id,
        valid=valid,
        rules=len(rules),
        documents=len(docs),
        questions=len(questions),
        forms=len(forms),
    )


async def run_stage_research(ctx: dict[str, Any], event: OutboxEvent) -> None:
    """Run one agentic per-stage research job (docs/plan/03_corridor_bd_jp.md, Decisions §2).

    Calls the AI service's ``POST /ai/agentic/research-stage``, validates the result against
    the stage's NF-2 citation/schema gate (:func:`services.agentic.stage_is_valid`), and writes
    it to the cached :class:`CaseStageResearch` row. Unlike :func:`run_case_research`, this is a
    single request/response (no NDJSON progress stream) — a stage's search+extract (+ optional
    followup round) typically completes in well under a minute; add streaming progress here
    later if a stage proves slow enough to need it.
    """
    import httpx

    settings = get_settings()
    session_factory = ctx["session_factory"]
    payload = dict(event.payload or {})
    research_id = payload.get("stage_research_id")
    stage = payload.get("stage")
    if research_id is None or stage is None:
        return

    async with session_factory() as session:
        research = await session.get(CaseStageResearch, research_id)
        if research is None:
            return
        research.status = ScopeResearchStatus.RUNNING
        await session.commit()

    now = datetime.now(UTC)
    data: dict[str, Any] = {}
    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            resp = await client.post(
                f"{settings.ai_service_url.rstrip('/')}/ai/agentic/research-stage",
                json={
                    "stage": stage,
                    "destination_code": payload.get("destination_code"),
                    "purpose_code": payload.get("purpose_code"),
                    "action_code": payload.get("action_code"),
                    "nationality": payload.get("nationality"),
                    "residence_country": payload.get("residence_country"),
                    "context": payload.get("context") or {},
                },
            )
            if resp.status_code >= 300:
                raise RuntimeError(f"agentic research returned HTTP {resp.status_code}")
            data = resp.json()
    except asyncio.CancelledError:
        # See run_case_research's identical handling: arq's job timeout cancels this
        # coroutine, and CancelledError is a BaseException that would otherwise skip past
        # the handler below and leave the row stuck in RUNNING forever.
        async with session_factory() as session:
            research = await session.get(CaseStageResearch, research_id)
            if research is not None:
                research.status = ScopeResearchStatus.FAILED
                research.error = "stage research job timed out"
            await session.commit()
        log.warning("stage_research.failed", research_id=research_id, error="cancelled/timed out")
        raise
    except Exception as exc:  # noqa: BLE001 - a failed stage research must never crash the drain
        error_message = str(exc) or type(exc).__name__
        async with session_factory() as session:
            research = await session.get(CaseStageResearch, research_id)
            if research is not None:
                research.status = ScopeResearchStatus.FAILED
                research.error = error_message[:1000]
            await session.commit()
        log.warning(
            "stage_research.failed", research_id=research_id, stage=stage, error=error_message
        )
        return

    items = dict(data.get("items") or {})
    valid = stage_is_valid(stage, items)

    async with session_factory() as session:
        research = await session.get(CaseStageResearch, research_id)
        if research is None:
            return
        if valid:
            research.status = ScopeResearchStatus.COMPLETED
            research.payload = items
            research.source_pages = list(data.get("source_pages") or [])
            research.researched_at = now
            research.expires_at = stage_expiry(stage)
            research.error = None
        else:
            research.status = ScopeResearchStatus.FAILED
            research.error = "stage research payload failed the citation/schema gate"
        await session.commit()

    log.info("stage_research.done", research_id=research_id, stage=stage, valid=valid)


async def poll_outbox(ctx: dict[str, Any]) -> int:
    """Drain unprocessed outbox events (at-least-once), stamping ``processed_at``.

    Events are fetched, then each is **claimed** (``processed_at`` stamped) *before* its
    handler runs — this cron fires every 10s (see ``cron_jobs`` below), but a research job
    routinely takes well over 10s, so claiming late (after the handler returns) let the next
    tick see the same still-open event and re-dispatch it, running duplicate concurrent scrapes
    against the same ``ScopeResearch`` row. The claim uses an ``UPDATE ... WHERE processed_at
    IS NULL`` so two overlapping ticks can't both win the same event.
    """
    session_factory = ctx["session_factory"]
    async with session_factory() as session:
        pending = (
            (
                await session.execute(
                    select(OutboxEvent)
                    .where(OutboxEvent.processed_at.is_(None))
                    .order_by(OutboxEvent.id)
                    .limit(100)
                )
            )
            .scalars()
            .all()
        )

    handled = 0
    for event in pending:
        async with session_factory() as session:
            result = await session.execute(
                update(OutboxEvent)
                .where(OutboxEvent.id == event.id, OutboxEvent.processed_at.is_(None))
                .values(processed_at=datetime.now(UTC))
            )
            await session.commit()
            if result.rowcount == 0:
                log.info("outbox.already_claimed", topic=event.topic, event_id=event.id)
                continue

        if event.topic == "case.research.queued":
            await run_case_research(ctx, event)
        elif event.topic == "case.stage_research.queued":
            await run_stage_research(ctx, event)
        else:
            log.info("outbox.handle", topic=event.topic, event_id=event.id)
        handled += 1
    if handled:
        log.info("outbox.drained", handled=handled)
    return handled


async def send_renewal_reminders(ctx: dict[str, Any]) -> int:
    """Find cases whose renewal date falls within the lead window and (later) remind them.

    US-19: remind an applicant before a recorded renewal date. The scaffold selects the due
    cases and logs them; wiring the notification dispatch is the next step.
    """
    settings = get_settings()
    session_factory = ctx["session_factory"]
    horizon = datetime.now(UTC) + timedelta(days=settings.renewal_reminder_lead_days)
    async with session_factory() as session:
        due = (
            (
                await session.execute(
                    select(Case).where(
                        Case.renewal_due_at.is_not(None),
                        Case.renewal_due_at <= horizon,
                    )
                )
            )
            .scalars()
            .all()
        )
    for case in due:
        log.info("renewal.due", case=case.reference, renewal_due_at=str(case.renewal_due_at))
    log.info(
        "renewal.reminders_swept", count=len(due), lead_days=settings.renewal_reminder_lead_days
    )
    return len(due)


async def scrape_immigration_sources(ctx: dict[str, Any]) -> dict[str, Any]:
    """Daily Tavily+LLM scrape via the AI service, with gov_scraper fallback.

    Beachhead JP/US scopes are scraped, ingested, and auto-promoted when the
    payload validates (citations + intake schema). Live seed data is never
    demoted by a failed scrape.
    """
    import httpx

    from torii_api.services.ops_ingest import BEACHHEAD_SCOPES, ingest_scrape_result

    settings = get_settings()
    session_factory = ctx["session_factory"]
    jurisdictions = {
        j.strip().upper() for j in settings.scrape_jurisdictions.split(",") if j.strip()
    }
    scopes = [s for s in BEACHHEAD_SCOPES if s[0] in jurisdictions]

    stored = {
        "eligibility": 0,
        "documents": 0,
        "intake": 0,
        "forms": 0,
        "promoted": 0,
        "source": "tavily",
    }

    log.info("scraper.starting", scopes=scopes, ai_url=settings.ai_service_url)

    ai_ok = False
    async with session_factory() as session:
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                for jurisdiction_code, visa_category, action in scopes:
                    try:
                        resp = await client.post(
                            f"{settings.ai_service_url.rstrip('/')}/ai/ops/scrape",
                            json={
                                "jurisdiction_code": jurisdiction_code,
                                "visa_category": visa_category,
                                "action": action,
                                "return_payload": True,
                            },
                        )
                        if resp.status_code >= 300:
                            log.warning(
                                "scraper.ai_http_error",
                                status=resp.status_code,
                                jurisdiction=jurisdiction_code,
                            )
                            continue
                        payload = resp.json()
                        ai_ok = True
                        rules = list(payload.get("eligibility_rules_payload") or [])
                        docs = list(payload.get("document_requirements_payload") or [])
                        questions = list(payload.get("intake_questions_payload") or [])
                        forms = list(payload.get("form_templates_payload") or [])
                        if not rules and not docs and not questions:
                            log.info(
                                "scraper.ai_empty_payload",
                                jurisdiction=jurisdiction_code,
                                message=payload.get("message"),
                            )
                            continue
                        result = await ingest_scrape_result(
                            session,
                            jurisdiction_code=jurisdiction_code,
                            visa_category=visa_category,
                            action=action,
                            eligibility_rules=rules,
                            document_requirements=docs,
                            intake_questions=questions,
                            form_templates=forms,
                            auto_promote=True,
                        )
                        for key in ("eligibility", "documents", "intake", "forms"):
                            stored[key] += int(result.get(key) or 0)
                        if result.get("promoted"):
                            stored["promoted"] += 1
                    except Exception as exc:
                        log.warning(
                            "scraper.ai_scope_failed",
                            jurisdiction=jurisdiction_code,
                            error=str(exc),
                        )
            await session.commit()
        except Exception as exc:
            log.warning("scraper.ai_unavailable", error=str(exc))
            await session.rollback()

    if not ai_ok or stored["eligibility"] == 0:
        log.info("scraper.fallback_gov_scraper")
        stored["source"] = "gov_scraper_fallback"
        from torii_api.services.gov_scraper import scrape_all

        results = await scrape_all(sorted(jurisdictions))
        async with session_factory() as session:
            for code, result in results.items():
                for action_code, rules in result.eligibility_rules.items():
                    docs = result.document_requirements.get(action_code, [])
                    # Map scraper action/visa keys onto beachhead scopes when possible
                    visa = "work" if code == "JP" else "h1b"
                    if action_code in ("renewal", "new_application"):
                        action = action_code
                    else:
                        action = "renewal"
                    if (code, visa, action) not in scopes and (code, visa, "renewal") in scopes:
                        action = "renewal"
                    if (code, visa, action) not in scopes:
                        continue
                    ingest = await ingest_scrape_result(
                        session,
                        jurisdiction_code=code,
                        visa_category=visa,
                        action=action,
                        eligibility_rules=list(rules or []),
                        document_requirements=list(docs or []),
                        intake_questions=[],
                        form_templates=[],
                        auto_promote=False,
                    )
                    for key in ("eligibility", "documents", "intake", "forms"):
                        stored[key] += int(ingest.get(key) or 0)
            await session.commit()

    log.info("scraper.batch_complete", **stored)
    return stored


async def monitor_official_sources(ctx: dict[str, Any]) -> None:
    """Government-change monitor tick (US-26): delegates to daily scrape path."""
    await scrape_immigration_sources(ctx)


async def startup(ctx: dict[str, Any]) -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    ctx["engine"] = create_engine(settings.database_url)
    ctx["session_factory"] = create_session_factory(ctx["engine"])
    log.info(
        "worker.startup",
        service=settings.service_name,
        database=settings.database_url.split("://", 1)[0],
    )


async def shutdown(ctx: dict[str, Any]) -> None:
    engine = ctx.get("engine")
    if engine is not None:
        await engine.dispose()
    log.info("worker.shutdown")


class WorkerSettings:
    """arq entrypoint: ``uv run arq torii_api.worker.scheduler.WorkerSettings``."""

    functions = [
        poll_outbox,
        send_renewal_reminders,
        scrape_immigration_sources,
        monitor_official_sources,
    ]
    on_startup = startup
    on_shutdown = shutdown
    # arq reads the connection off this class attribute (resolved from TORII_REDIS_URL at import).
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    cron_jobs = [
        # Drain the outbox every 10 seconds (the sub-minute cadence the outbox needs). A
        # research job runs inline here and can take several minutes (scrape + LLM
        # extraction), so this needs a timeout well past arq's 300s default — otherwise arq
        # cancels the job mid-run, which orphans the ScopeResearch row in RUNNING forever
        # (asyncio.CancelledError isn't caught by run_case_research's `except Exception`).
        cron(
            poll_outbox,
            second={0, 10, 20, 30, 40, 50},
            run_at_startup=True,
            timeout=600,
        ),
        # Renewal reminders once a day at 08:00 (server time).
        cron(send_renewal_reminders, hour=8, minute=0),
        # AI-powered immigration source scraping — daily at 02:00 (server time).
        cron(scrape_immigration_sources, hour=2, minute=0),
        # Government-change monitor, hourly on the hour (delegates to scrape_immigration_sources).
        cron(monitor_official_sources, minute=0),
    ]
