"""Pydantic response schemas for API output."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class AgentStep(BaseModel):
    """A single step in the AI agent audit trail."""

    agent_name: str
    status: str = Field(..., description="running | complete | error")
    output_summary: str | None = None
    timestamp: datetime


class VerdictResponse(BaseModel):
    """Generic verdict response for any check type."""

    id: uuid.UUID
    type: str = Field(..., description="claim | scam_report | media_check")
    verdict: str
    confidence_score: float | None = None
    explanation_en: str | None = None
    explanation_ur: str | None = None
    sources: list[dict] | None = None
    agent_trail: list[AgentStep] | None = None
    created_at: datetime


class FeedItem(BaseModel):
    """A single item in the fact-check feed."""

    id: uuid.UUID
    title: str
    verdict: str | None = None
    confidence: float | None = None
    explanation_en: str | None = None
    category: str | None = None
    source_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class TrendingItem(BaseModel):
    """A trending item for the public dashboard."""

    id: uuid.UUID
    entity_type: str
    title: str
    verdict: str | None = None
    spread_score: float
    report_volume: int


class PipelineEvent(BaseModel):
    """Server-sent event emitted during pipeline processing."""

    agent_name: str
    status: str = Field(..., description="running | complete | error")
    output_summary: str | None = None
    timestamp: datetime
