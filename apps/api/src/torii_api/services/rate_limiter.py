"""Rate limiting and abuse protection service (T-10).

Provides sliding-window rate limiting for authenticated users and unauthenticated IP addresses,
route-specific throttling for sensitive/expensive endpoints, monthly research budget tracking,
and Redis/in-memory storage backends with graceful fallback.
"""

from __future__ import annotations

import asyncio
import math
import time
from collections import defaultdict, deque
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import structlog
from fastapi import HTTPException, Request, status

from torii_api.auth.security import decode_access_token
from torii_api.config import Settings, get_settings

log = structlog.get_logger()


class RateLimitResult:
    """Outcome of a rate-limit check."""

    def __init__(
        self,
        allowed: bool,
        limit: int,
        remaining: int,
        reset_epoch: int,
        retry_after: int,
    ) -> None:
        self.allowed = allowed
        self.limit = limit
        self.remaining = remaining
        self.reset_epoch = reset_epoch
        self.retry_after = retry_after

    def to_headers(self) -> dict[str, str]:
        headers = {
            "X-RateLimit-Limit": str(self.limit),
            "X-RateLimit-Remaining": str(max(0, self.remaining)),
            "X-RateLimit-Reset": str(self.reset_epoch),
        }
        if not self.allowed:
            headers["Retry-After"] = str(max(1, self.retry_after))
        return headers


class RateLimitExceeded(HTTPException):
    """HTTP 429 Too Many Requests exception with rate-limit headers."""

    def __init__(self, result: RateLimitResult, detail: str | None = None) -> None:
        msg = detail or f"Rate limit exceeded. Please retry in {max(1, result.retry_after)} seconds."
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=msg,
            headers=result.to_headers(),
        )
        self.result = result


def get_client_ip(request: Request) -> str:
    """Extract real client IP, respecting proxy headers if present."""
    # 1. Cloudflare header
    cf_ip = request.headers.get("cf-connecting-ip")
    if cf_ip and cf_ip.strip():
        return cf_ip.strip().split(",")[0].strip()

    # 2. Standard X-Forwarded-For header (first hop is the original client)
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded and forwarded.strip():
        return forwarded.strip().split(",")[0].strip()

    # 3. Nginx / reverse-proxy X-Real-IP header
    real_ip = request.headers.get("x-real-ip")
    if real_ip and real_ip.strip():
        return real_ip.strip()

    # 4. Direct socket client host
    if request.client and request.client.host:
        return request.client.host

    return "127.0.0.1"


def get_client_identity(request: Request, settings: Settings) -> tuple[str, str]:
    """Resolve (identity_type, identity_key) for the incoming request.

    Returns:
        ("user", "<user_id>") if request carries a valid Bearer JWT.
        ("ip", "<client_ip>") otherwise.
    """
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ", 1)[1].strip()
        try:
            payload = decode_access_token(token, settings)
            user_id = str(payload.get("sub", "")).strip()
            if user_id:
                return "user", user_id
        except Exception:
            # Malformed or expired token falls back to IP limiting for the request
            pass

    return "ip", get_client_ip(request)


class InMemoryRateLimitBackend:
    """Thread-safe & asyncio-safe in-memory sliding-window counter."""

    def __init__(self) -> None:
        self._records: dict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()
        self._last_cleanup = time.monotonic()

    async def check_and_increment(
        self,
        key: str,
        limit: int,
        window_seconds: int,
    ) -> RateLimitResult:
        now = time.time()
        window_start = now - window_seconds

        async with self._lock:
            # Periodic cleanup of completely expired keys
            mono_now = time.monotonic()
            if mono_now - self._last_cleanup > 30.0:
                self._cleanup(now)
                self._last_cleanup = mono_now

            deq = self._records[key]

            # Drop timestamps older than current window
            while deq and deq[0] <= window_start:
                deq.popleft()

            count = len(deq)
            if count >= limit:
                oldest = deq[0]
                reset_epoch = math.ceil(oldest + window_seconds)
                retry_after = max(1, math.ceil(reset_epoch - now))
                return RateLimitResult(
                    allowed=False,
                    limit=limit,
                    remaining=0,
                    reset_epoch=reset_epoch,
                    retry_after=retry_after,
                )

            # Record this request
            deq.append(now)
            remaining = limit - (count + 1)
            oldest = deq[0]
            reset_epoch = math.ceil(oldest + window_seconds)
            return RateLimitResult(
                allowed=True,
                limit=limit,
                remaining=remaining,
                reset_epoch=reset_epoch,
                retry_after=0,
            )

    def _cleanup(self, now: float) -> None:
        """Purge empty or stale entries (older than 24 hours max window)."""
        stale_keys = [
            k for k, timestamps in self._records.items()
            if not timestamps or timestamps[-1] < (now - 86400)
        ]
        for k in stale_keys:
            self._records.pop(k, None)

    async def reset(self, key_prefix: str | None = None) -> None:
        """Clear all or matching rate limit records (useful in tests)."""
        async with self._lock:
            if key_prefix is None:
                self._records.clear()
            else:
                to_delete = [k for k in self._records if k.startswith(key_prefix)]
                for k in to_delete:
                    self._records.pop(k, None)


class RedisRateLimitBackend:
    """Redis-backed distributed sliding-window counter using Redis sorted sets."""

    def __init__(self, redis_url: str) -> None:
        self.redis_url = redis_url
        self._client: Any = None
        self._disabled = False

    async def _get_client(self) -> Any:
        if self._disabled:
            return None
        if self._client is None:
            try:
                import redis.asyncio as aioredis

                self._client = aioredis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_connect_timeout=1.0,
                    socket_timeout=1.0,
                )
            except Exception as exc:
                log.warning("rate_limiter.redis_init_failed", error=str(exc))
                self._disabled = True
                return None
        return self._client

    async def check_and_increment(
        self,
        key: str,
        limit: int,
        window_seconds: int,
    ) -> RateLimitResult | None:
        client = await self._get_client()
        if client is None:
            return None

        now = time.time()
        window_start = now - window_seconds
        redis_key = f"torii:rl:{key}"
        now_str = f"{now:.6f}"

        try:
            pipe = client.pipeline()
            # Remove timestamps outside current window
            pipe.zremrangebyscore(redis_key, 0, window_start)
            # Get current count in window
            pipe.zcard(redis_key)
            # Retrieve oldest timestamp in window
            pipe.zrange(redis_key, 0, 0, withscores=True)
            # Set TTL on key
            pipe.expire(redis_key, window_seconds + 5)
            _, count, oldest_items, _ = await pipe.execute()

            if count >= limit:
                oldest_ts = oldest_items[0][1] if oldest_items else now
                reset_epoch = math.ceil(oldest_ts + window_seconds)
                retry_after = max(1, math.ceil(reset_epoch - now))
                return RateLimitResult(
                    allowed=False,
                    limit=limit,
                    remaining=0,
                    reset_epoch=reset_epoch,
                    retry_after=retry_after,
                )

            # Record request
            add_pipe = client.pipeline()
            add_pipe.zadd(redis_key, {now_str: now})
            add_pipe.expire(redis_key, window_seconds + 5)
            await add_pipe.execute()

            oldest_ts = oldest_items[0][1] if oldest_items else now
            reset_epoch = math.ceil(oldest_ts + window_seconds)
            return RateLimitResult(
                allowed=True,
                limit=limit,
                remaining=limit - (count + 1),
                reset_epoch=reset_epoch,
                retry_after=0,
            )
        except Exception as exc:
            log.warning("rate_limiter.redis_check_failed_fallback_in_memory", error=str(exc))
            self._disabled = True
            return None


class RateLimiter:
    """Process-wide rate limiter singleton managing in-memory & Redis backends."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.memory_backend = InMemoryRateLimitBackend()
        self.redis_backend: RedisRateLimitBackend | None = None
        if self.settings.redis_url:
            self.redis_backend = RedisRateLimitBackend(self.settings.redis_url)

    async def check(
        self,
        key: str,
        limit: int,
        window_seconds: int = 60,
    ) -> RateLimitResult:
        """Check and increment the sliding window counter for ``key``."""
        if not self.settings.rate_limit_enabled:
            # Rate limiting disabled (e.g. in specific test suites or via env)
            return RateLimitResult(
                allowed=True,
                limit=limit,
                remaining=limit,
                reset_epoch=math.ceil(time.time() + window_seconds),
                retry_after=0,
            )

        # Try Redis first if available; fall back to in-memory if Redis returns None or errors
        if self.redis_backend is not None:
            try:
                res = await self.redis_backend.check_and_increment(key, limit, window_seconds)
                if res is not None:
                    return res
            except Exception:
                pass

        return await self.memory_backend.check_and_increment(key, limit, window_seconds)

    async def reset(self, prefix: str | None = None) -> None:
        """Reset rate limiter records."""
        await self.memory_backend.reset(prefix)


# Process singleton
_limiter_instance: RateLimiter | None = None


def get_rate_limiter(settings: Settings | None = None) -> RateLimiter:
    global _limiter_instance
    if _limiter_instance is None:
        _limiter_instance = RateLimiter(settings)
    return _limiter_instance


async def check_rate_limit(
    request: Request,
    limit: int,
    window_seconds: int = 60,
    key_prefix: str = "route",
    key_suffix: str | None = None,
    detail: str | None = None,
    settings: Settings | None = None,
) -> RateLimitResult:
    """Enforce a rate limit on the current request, raising RateLimitExceeded if over quota."""
    settings = settings or get_settings()
    if not settings.rate_limit_enabled:
        return RateLimitResult(
            allowed=True,
            limit=limit,
            remaining=limit,
            reset_epoch=math.ceil(time.time() + window_seconds),
            retry_after=0,
        )

    limiter = get_rate_limiter(settings)

    # Resolve identifier
    if key_suffix:
        key = f"{key_prefix}:{key_suffix}"
    else:
        ident_type, ident_val = get_client_identity(request, settings)
        key = f"{key_prefix}:{ident_type}:{ident_val}"

    result = await limiter.check(key=key, limit=limit, window_seconds=window_seconds)
    if not result.allowed:
        raise RateLimitExceeded(result, detail=detail)

    return result


class ResearchBudgetTracker:
    """Tracks and enforces monthly research limits per user (T-10)."""

    def __init__(self, limiter: RateLimiter | None = None) -> None:
        self.limiter = limiter or get_rate_limiter()

    async def check_budget(self, user_id: int | str, settings: Settings | None = None) -> RateLimitResult:
        settings = settings or get_settings()
        if not settings.rate_limit_enabled:
            return RateLimitResult(
                allowed=True,
                limit=settings.rate_limit_monthly_research_budget,
                remaining=settings.rate_limit_monthly_research_budget,
                reset_epoch=0,
                retry_after=0,
            )

        now = datetime.now(UTC)
        current_month = now.strftime("%Y-%m")
        # Calendar month window in seconds (approx 31 days)
        month_window = 31 * 86400
        key = f"research_budget:{user_id}:{current_month}"

        limit = settings.rate_limit_monthly_research_budget
        result = await self.limiter.check(key=key, limit=limit, window_seconds=month_window)

        if not result.allowed:
            raise RateLimitExceeded(
                result,
                detail=f"Monthly research budget exceeded ({limit} requests allowed per month).",
            )
        return result


def require_rate_limit(
    limit: int | Callable[[Settings], int],
    window_seconds: int = 60,
    key_prefix: str = "route",
    key_func: Callable[[Request], str] | None = None,
    detail: str | None = None,
):
    """FastAPI dependency factory to enforce a route-level rate limit.

    Example:
        @router.post("/login", dependencies=[Depends(require_rate_limit(10, 60, "auth:login"))])
    """

    async def _rate_limit_dep(request: Request) -> RateLimitResult:
        settings = get_settings()
        effective_limit = limit(settings) if callable(limit) else limit
        key_suffix = key_func(request) if key_func is not None else None
        return await check_rate_limit(
            request=request,
            limit=effective_limit,
            window_seconds=window_seconds,
            key_prefix=key_prefix,
            key_suffix=key_suffix,
            detail=detail,
            settings=settings,
        )

    return _rate_limit_dep
