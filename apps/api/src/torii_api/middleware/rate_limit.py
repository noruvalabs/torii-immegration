"""Global rate-limiting middleware for Torii API.

Enforces per-user limits for authenticated callers and per-IP limits for unauthenticated callers.
Attaches standard rate limit headers (X-RateLimit-*) to all responses.
"""

from __future__ import annotations

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from torii_api.config import Settings, get_settings
from torii_api.services.rate_limiter import get_client_identity, get_rate_limiter

log = structlog.get_logger()

# Endpoints exempt from global rate limiting (health probes, docs, static specs)
EXEMPT_EXACT_PATHS = {
    "/health",
    "/healthz",
    "/favicon.ico",
    "/openapi.json",
    "/docs",
}

EXEMPT_PREFIXES = (
    "/docs/",
    "/scalar/",
)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware enforcing global request quotas per user and per IP."""

    def __init__(self, app, settings: Settings | None = None) -> None:
        super().__init__(app)
        self.settings = settings or get_settings()
        self.limiter = get_rate_limiter(self.settings)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Check if rate limiting is enabled
        settings = getattr(request.app.state, "settings", self.settings)
        if not settings.rate_limit_enabled:
            return await call_next(request)

        path = request.url.path
        if path in EXEMPT_EXACT_PATHS or any(path.startswith(prefix) for prefix in EXEMPT_PREFIXES):
            return await call_next(request)

        # Skip OPTIONS preflight requests (handled by CORS)
        if request.method.upper() == "OPTIONS":
            return await call_next(request)

        ident_type, ident_val = get_client_identity(request, settings)
        if ident_type == "user":
            limit = settings.rate_limit_user_per_minute
            key = f"global:user:{ident_val}"
        else:
            limit = settings.rate_limit_ip_per_minute
            key = f"global:ip:{ident_val}"

        result = await self.limiter.check(key=key, limit=limit, window_seconds=60)

        if not result.allowed:
            log.warning(
                "rate_limit.exceeded",
                identity_type=ident_type,
                identity_value=ident_val,
                path=path,
                retry_after=result.retry_after,
            )
            headers = result.to_headers()
            return JSONResponse(
                status_code=429,
                content={
                    "detail": f"Rate limit exceeded. Please retry in {max(1, result.retry_after)} seconds."
                },
                headers=headers,
            )

        response = await call_next(request)

        # Attach rate limit quota headers to the response
        for header_name, header_val in result.to_headers().items():
            response.headers[header_name] = header_val

        return response
