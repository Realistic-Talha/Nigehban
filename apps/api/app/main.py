"""Nigehban API — FastAPI application entry point."""

import asyncio
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import settings
from app.core.database import engine
from app.core.redis import redis_pool
from app.api.v1.router import api_router
from app.api.webhooks.whatsapp import router as whatsapp_webhook_router


async def _inline_worker_loop() -> None:
    from app.workers.redis_queue import dequeue_pipeline
    from app.workers.tasks import run_pipeline_task

    while True:
        try:
            job = await dequeue_pipeline(timeout=2)
            if job:
                try:
                    await asyncio.wait_for(
                        run_pipeline_task(
                            job["check_id"],
                            job["check_type"],
                            job["input_data"],
                        ),
                        timeout=180.0,
                    )
                except asyncio.TimeoutError:
                    import logging

                    logging.getLogger(__name__).error(
                        "Pipeline job timed out after 180s | check_id=%s type=%s",
                        job.get("check_id"),
                        job.get("check_type"),
                    )
        except asyncio.CancelledError:
            break
        except Exception:
            await asyncio.sleep(1)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup/shutdown lifecycle for DB and Redis connections."""
    await redis_pool.connect()
    worker_task: asyncio.Task | None = None
    if settings.WORKER_INLINE:
        worker_task = asyncio.create_task(_inline_worker_loop())
    yield
    if worker_task:
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass
    await redis_pool.disconnect()
    await engine.dispose()


app = FastAPI(
    title="Nigehban API",
    description="Pakistan's AI-Powered Fact-Check, Scam-Detection & Deepfake-Verification API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if settings.ENVIRONMENT == "prod" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")
app.include_router(whatsapp_webhook_router)


@app.get("/health", tags=["system"])
async def health_check() -> dict:
    """Return service health with dependency checks."""
    status: dict = {"status": "ok", "version": "0.1.0"}

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        status["db"] = "ok"
    except Exception as exc:
        status["db"] = f"error: {exc}"
        status["status"] = "degraded"

    try:
        client = redis_pool.client
        await client.ping()
        status["redis"] = "ok"
    except Exception as exc:
        status["redis"] = f"error: {exc}"
        status["status"] = "degraded"

    if settings.LLM_PROVIDER == "ollama":
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/tags")
                status["ollama"] = "ok" if resp.status_code == 200 else "error"
        except Exception as exc:
            status["ollama"] = f"error: {exc}"

    status["llm_provider"] = settings.LLM_PROVIDER
    status["search_provider"] = settings.SEARCH_PROVIDER
    return status
