"""Celery application configuration with Redis broker and task queues."""

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "nigehban",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    # Queue definitions
    task_queues={
        "text-checks": {"exchange": "text-checks", "routing_key": "text"},
        "image-checks": {"exchange": "image-checks", "routing_key": "image"},
        "video-checks": {"exchange": "video-checks", "routing_key": "video"},
        "ingestion": {"exchange": "ingestion", "routing_key": "ingest"},
    },
    task_default_queue="text-checks",
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 min hard limit
    task_soft_time_limit=240,  # 4 min soft limit
    worker_prefetch_multiplier=1,
    worker_concurrency=4,
)

# Auto-discover tasks in this module
celery_app.autodiscover_tasks(["app.workers"])
