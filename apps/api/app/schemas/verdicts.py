"""Shared enum types for verdicts, categories, and scam types."""

from enum import Enum


class FactCheckVerdict(str, Enum):
    """Possible verdicts for a fact-checked claim."""

    TRUE = "true"
    FALSE = "false"
    MISLEADING = "misleading"
    SATIRE = "satire"
    UNVERIFIED = "unverified"


class ScamVerdict(str, Enum):
    """Possible verdicts for a scam check."""

    LIKELY_SCAM = "likely_scam"
    NEEDS_CAUTION = "needs_caution"
    LIKELY_SAFE = "likely_safe"


class MediaVerdict(str, Enum):
    """Possible verdicts for a media authenticity check."""

    LIKELY_AUTHENTIC = "likely_authentic"
    INCONCLUSIVE = "inconclusive"
    LIKELY_MANIPULATED = "likely_manipulated"


class Category(str, Enum):
    """Content categories for fact-checked claims."""

    POLITICS = "politics"
    HEALTH = "health"
    FINANCE = "finance"
    DISASTER = "disaster"
    CELEBRITY = "celebrity"
    OTHER = "other"


class ScamType(str, Enum):
    """Known scam categories."""

    JOB_SCAM = "job_scam"
    INVESTMENT_PONZI = "investment_ponzi"
    PHISHING = "phishing"
    LOTTERY_PRIZE = "lottery_prize"
    ROMANCE = "romance"
    FAKE_GOVT = "fake_govt"
    MARKETPLACE = "marketplace"
    SIM_SWAP = "sim_swap"
    FAKE_CHARITY = "fake_charity"
    OTHER = "other"
