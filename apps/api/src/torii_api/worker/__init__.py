"""Background work — the arq worker (cron schedule + task queue).

Run it alongside the API:

    uv run arq torii_api.worker.scheduler.WorkerSettings

It drains the transactional outbox, sends renewal reminders (US-19), and runs the
government-change monitor (US-26). The API enqueues ad-hoc jobs through
:mod:`torii_api.worker.queue`; both share the Redis configured by ``TORII_REDIS_URL``.
"""

from torii_api.worker.scheduler import WorkerSettings

__all__ = ["WorkerSettings"]
