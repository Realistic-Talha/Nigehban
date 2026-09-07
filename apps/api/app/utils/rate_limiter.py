"""Per-IP rate limiter — Redis-backed for multi-instance safety."""

import time

from fastapi import HTTPException, Request, status

from app.core.redis import redis_pool


class RateLimiter:
    """Sliding-window rate limiter using Redis."""

    def __init__(self, max_requests: int = 10, window_seconds: int = 60) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    async def __call__(self, request: Request) -> None:
        client_ip = request.client.host if request.client else "unknown"
        key = f"rate:{client_ip}:{self.max_requests}"
        now = int(time.time())
        window_start = now - self.window_seconds

        try:
            client = redis_pool.client
            pipe = client.pipeline()
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zadd(key, {str(now): now})
            pipe.zcard(key)
            pipe.expire(key, self.window_seconds)
            results = await pipe.execute()
            count = results[2]
            if count > self.max_requests:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded. Please try again later.",
                )
        except HTTPException:
            raise
        except Exception:
            # Fail open if Redis unavailable
            return
