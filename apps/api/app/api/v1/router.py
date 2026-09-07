"""Main v1 API router — aggregates all sub-routers."""

from fastapi import APIRouter

from app.api.v1.factcheck import router as factcheck_router
from app.api.v1.scamcheck import router as scamcheck_router
from app.api.v1.mediacheck import router as mediacheck_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.checks import router as checks_router
from app.api.v1.reports import router as reports_router
from app.api.v1.media import router as media_router

api_router = APIRouter()

api_router.include_router(factcheck_router, tags=["fact-check"])
api_router.include_router(scamcheck_router, tags=["scam-check"])
api_router.include_router(mediacheck_router, tags=["media-check"])
api_router.include_router(dashboard_router, tags=["dashboard"])
api_router.include_router(checks_router, tags=["checks"])
api_router.include_router(reports_router, tags=["reports"])
api_router.include_router(media_router, tags=["media"])
