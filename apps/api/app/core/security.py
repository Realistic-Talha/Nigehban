"""Simple in-memory rate limiter middleware.

Replace with Redis-backed implementation for production multi-instance deployments.
"""

import time
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-IP sliding-window rate limiter (in-memory)."""

    def __init__(self, app, max_requests: int = 60, window_seconds: int = 60) -> None:  # noqa: ANN001
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Check rate limit before forwarding the request."""
        client_ip = request.client.host if request.client else "unknown"
        now = time.monotonic()

        # Prune old entries outside the window
        self._hits[client_ip] = [
            ts for ts in self._hits[client_ip] if now - ts < self.window_seconds
        ]

        if len(self._hits[client_ip]) >= self.max_requests:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please try again later."},
            )

        self._hits[client_ip].append(now)
        return await call_next(request)
