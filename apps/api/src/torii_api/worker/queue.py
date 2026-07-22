"""Enqueue side of the task queue — used by the API to hand work to the arq worker.

The API must never fail a request because Redis is down. :func:`build_pool` returns ``None``
when it cannot connect, and :func:`enqueue` logs and no-ops in that case. Durable work that
must not be lost goes through the transactional **outbox** table instead (drained by the
worker's ``poll_outbox``); the queue is for best-effort, low-latency dispatch.
"""

from __future__ import annotations

from typing import Any

import structlog
from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

log = structlog.get_logger()


async def build_pool(redis_url: str) -> ArqRedis | None:
    """Create an arq Redis pool, or ``None`` if Redis is unreachable (best-effort).

    Connection retries are clamped low so a missing Redis fails fast (~1s) instead of blocking
    startup through arq's default multi-retry backoff — the API must come up without Redis.
    """
    settings = RedisSettings.from_dsn(redis_url)
    settings.conn_retries = 0
    settings.conn_timeout = 1
    try:
        return await create_pool(settings)
    except Exception as exc:  # noqa: BLE001 - any connection failure degrades to no queue
        log.warning("queue.unavailable", error=str(exc), redis_url=redis_url.split("@")[-1])
        return None


async def enqueue(pool: ArqRedis | None, function: str, *args: Any, **kwargs: Any) -> None:
    """Enqueue a job by name; no-op (logged) when no pool is available."""
    if pool is None:
        log.warning("queue.enqueue_skipped", function=function)
        return
    await pool.enqueue_job(function, *args, **kwargs)
