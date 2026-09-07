"""Pydantic request schemas for API input."""

from pydantic import BaseModel, Field


class FactCheckSubmission(BaseModel):
    """Submit a claim for fact-checking."""

    text: str = Field(..., min_length=1, max_length=5000, description="The claim or statement to verify")
    url: str | None = Field(None, description="Optional source URL for the claim")
    language: str = Field("en", description="Language of the submitted text (ISO 639-1)")


class ScamCheckSubmission(BaseModel):
    """Submit text for scam analysis."""

    text: str | None = Field(None, max_length=5000, description="Suspicious message text to analyse")
    language: str = Field("en", description="Language of the submitted text (ISO 639-1)")


class MediaCheckSubmission(BaseModel):
    """Submit media for authenticity analysis."""

    media_type: str = Field(..., description="Type of media: 'image' or 'video'")
    url: str | None = Field(None, description="URL of the media file (alternative to upload)")


class UserReport(BaseModel):
    """A user-submitted scam or misinformation report."""

    text: str = Field(..., min_length=1, max_length=5000, description="The suspicious content text")
    scam_type: str | None = Field(None, description="Suspected scam category if known")
    sender_identifier: str | None = Field(None, max_length=128, description="Phone number or sender ID")
    description: str | None = Field(None, max_length=2000, description="Additional context from the reporter")
