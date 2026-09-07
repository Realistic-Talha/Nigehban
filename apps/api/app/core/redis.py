"""Async Redis connection pool."""

from redis.asyncio import ConnectionPool, Redis

from app.core.config import settings


class RedisPool:
    """Thin wrapper around an async Redis connection pool."""

    def __init__(self, url: str) -> None:
        self._url = url
        self._pool: ConnectionPool | None = None
        self._client: Redis | None = None

    async def connect(self) -> None:
        """Create the connection pool and client."""
        self._pool = ConnectionPool.from_url(self._url, decode_responses=True)
        self._client = Redis(connection_pool=self._pool)

    async def disconnect(self) -> None:
        """Close the connection pool."""
        if self._client:
            await self._client.aclose()
        if self._pool:
            await self._pool.aclose()

    @property
    def client(self) -> Redis:
        """Return the active Redis client."""
        if self._client is None:
            raise RuntimeError("Redis pool not connected. Call connect() first.")
        return self._client


redis_pool = RedisPool(settings.REDIS_URL)
