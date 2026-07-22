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


async def monitor_official_sources(ctx: dict[str, Any]) -> None:
    """Government-change monitor tick (US-26): crawl official sources, diff, flag for review.

    Placeholder loop — it never mutates a live rule or form (NF-9). Detected changes will be
    written as outbox events / review-queue flags for a human to approve.
    """
    log.info("monitor.tick")


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

    functions = [poll_outbox, send_renewal_reminders, monitor_official_sources]
    on_startup = startup
    on_shutdown = shutdown
    # arq reads the connection off this class attribute (resolved from TORII_REDIS_URL at import).
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    cron_jobs = [
        # Drain the outbox every 10 seconds (the sub-minute cadence the outbox needs).
        cron(poll_outbox, second={0, 10, 20, 30, 40, 50}, run_at_startup=True),
        # Renewal reminders once a day at 08:00 (server time).
        cron(send_renewal_reminders, hour=8, minute=0),
        # Government-change monitor, hourly on the hour.
        cron(monitor_official_sources, minute=0),
    ]
