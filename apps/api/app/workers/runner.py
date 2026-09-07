"""Background worker — processes pipeline jobs from Redis queue."""

import asyncio
import logging

from app.core.redis import redis_pool
from app.workers.ingestion import RSSIngestionWorker
from app.workers.redis_queue import dequeue_pipeline
from app.workers.tasks import run_pipeline_task
from app.workers.trend_snapshot import run_trend_snapshot_job
from app.core.config import settings

logger = logging.getLogger(__name__)


async def _worker_loop() -> None:
    await redis_pool.connect()
    logger.info("Pipeline worker started")
    trend_interval = settings.TREND_SNAPSHOT_INTERVAL_MINUTES * 60
    last_trend = 0.0
    ingestion = RSSIngestionWorker()

    while True:
        try:
            now = asyncio.get_event_loop().time()
            if now - last_trend >= trend_interval:
                await run_trend_snapshot_job()
                if settings.RSS_FEED_URLS:
                    await ingestion.ingest_rss_feeds(settings.RSS_FEED_URLS)
                last_trend = now

            job = await dequeue_pipeline(timeout=2)
            if job:
                await run_pipeline_task(
                    job["check_id"],
                    job["check_type"],
                    job["input_data"],
                )
        except Exception:
            logger.exception("Worker loop error")
            await asyncio.sleep(1)


def main() -> None:
    asyncio.run(_worker_loop())


if __name__ == "__main__":
    main()
