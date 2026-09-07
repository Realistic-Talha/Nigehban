"""Redis-backed pipeline job queue."""

import json
import logging
from typing import Any

from app.core.redis import redis_pool

logger = logging.getLogger(__name__)

QUEUE_KEY = "pipeline:jobs"


async def enqueue_pipeline(check_id: str, check_type: str, input_data: dict[str, Any]) -> None:
    payload = json.dumps({
        "check_id": check_id,
        "check_type": check_type,
        "input_data": input_data,
    })
    client = redis_pool.client
    await client.lpush(QUEUE_KEY, payload)
    logger.info("Enqueued pipeline job %s (%s)", check_id, check_type)


async def dequeue_pipeline(timeout: int = 5) -> dict[str, Any] | None:
    client = redis_pool.client
    result = await client.brpop(QUEUE_KEY, timeout=timeout)
    if not result:
        return None
    _, raw = result
    return json.loads(raw)
