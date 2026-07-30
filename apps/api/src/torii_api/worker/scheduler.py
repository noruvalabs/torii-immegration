"""arq worker: the cron schedule and the outbox drain.

Each task gets an ``AsyncSession`` from the engine built once in :func:`startup` and stashed on
the arq ``ctx``. The schedule here is the scaffold's backbone — the real reminder dispatch and
source-diffing logic land on top of these seams without changing the wiring.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from arq import cron
from arq.connections import RedisSettings
from sqlalchemy import select

from torii_api.config import get_settings
from torii_api.db.engine import create_engine, create_session_factory
from torii_api.db.models import Case, OutboxEvent
from torii_api.logging import configure_logging

log = structlog.get_logger()


async def poll_outbox(ctx: dict[str, Any]) -> int:
    """Drain unprocessed outbox events (at-least-once), stamping ``processed_at``.

    The scaffold logs each event and marks it done; real handlers (embed source, notify,
    escalate) dispatch off ``topic`` here. Returns the number handled — useful in tests.
    """
    session_factory = ctx["session_factory"]
    handled = 0
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
        for event in pending:
            log.info("outbox.handle", topic=event.topic, event_id=event.id)
            event.processed_at = datetime.now(UTC)
            handled += 1
        await session.commit()
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
        # Drain the outbox every 10 seconds (the sub-minute cadence the outbox needs).
        cron(poll_outbox, second={0, 10, 20, 30, 40, 50}, run_at_startup=True),
        # Renewal reminders once a day at 08:00 (server time).
        cron(send_renewal_reminders, hour=8, minute=0),
        # AI-powered immigration source scraping — daily at 02:00 (server time).
        cron(scrape_immigration_sources, hour=2, minute=0),
        # Government-change monitor, hourly on the hour (delegates to scrape_immigration_sources).
        cron(monitor_official_sources, minute=0),
    ]
