"""SSE (Server-Sent Events) utilities for real-time streaming."""

import asyncio
import json
import logging
from typing import AsyncGenerator

from starlette.responses import StreamingResponse

from app.core.redis import redis_pool

logger = logging.getLogger(__name__)


async def sse_generator(channel: str, timeout: float = 60.0) -> AsyncGenerator[str, None]:
    """Subscribe to Redis Pub/Sub and yield SSE events.

    Each message is expected to be a JSON payload.  The generator terminates
    when:
      - the *judge* agent emits a ``complete`` or ``error`` status, OR
      - the *timeout* (seconds) elapses.

    A heartbeat comment (``: heartbeat\\n\\n``) is sent every idle iteration
    to keep the connection alive behind reverse-proxies.
    """
    try:
        client = redis_pool.client
    except RuntimeError:
        # Redis not connected — yield a single error event and return
        yield f"data: {json.dumps({'error': 'streaming unavailable'})}\n\n"
        return

    pubsub = client.pubsub()
    try:
        await pubsub.subscribe(channel)
    except Exception:
        logger.warning("Failed to subscribe to %s", channel, exc_info=True)
        yield f"data: {json.dumps({'error': 'streaming unavailable'})}\n\n"
        await pubsub.aclose()
        return

    try:
        loop = asyncio.get_event_loop()
        end_time = loop.time() + timeout

        while loop.time() < end_time:
            try:
                message = await pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=1.0,
                )
            except Exception:
                # Connection lost or timeout — send heartbeat and continue
                yield ": heartbeat\n\n"
                await asyncio.sleep(1)
                continue

            if message and message["type"] == "message":
                data = message["data"]
                if isinstance(data, bytes):
                    data = data.decode("utf-8")
                yield f"data: {data}\n\n"

                # Terminal event — judge complete or error
                try:
                    parsed = json.loads(data)
                    agent = parsed.get("agent_name") or parsed.get("agent")
                    status_val = parsed.get("status", "")
                    if agent == "judge" and status_val in ("complete", "error"):
                        break
                    if status_val == "pipeline_complete":
                        break
                except (json.JSONDecodeError, TypeError):
                    pass
            else:
                yield ": heartbeat\n\n"
                await asyncio.sleep(1)
    finally:
        try:
            await pubsub.unsubscribe(channel)
        except Exception:
            pass
        await pubsub.aclose()


def create_sse_response(channel: str, timeout: float = 60.0) -> StreamingResponse:
    """Create an SSE ``StreamingResponse`` for a given Redis channel."""
    return StreamingResponse(
        sse_generator(channel, timeout),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
