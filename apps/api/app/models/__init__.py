"""Re-export all models for convenient importing."""

from app.models.claim import Claim
from app.models.scam_report import ScamReport
from app.models.media_check import MediaCheck
from app.models.agent_log import AgentLog
from app.models.trend_snapshot import TrendSnapshot
from app.models.user import User
from app.models.scam_pattern import ScamPattern
from app.models.curated_reference import CuratedReference
from app.models.media_fingerprint import MediaFingerprint

__all__ = [
    "Claim",
    "ScamReport",
    "MediaCheck",
    "AgentLog",
    "TrendSnapshot",
    "User",
    "ScamPattern",
    "CuratedReference",
    "MediaFingerprint",
]
