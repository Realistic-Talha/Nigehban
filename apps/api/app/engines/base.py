"""Shared types for the Detection Kernel."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Evidence:
    type: str
    value: str
    signal: str
    detail: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "value": self.value,
            "signal": self.signal,
            "detail": self.detail,
        }


@dataclass
class EngineResult:
    """Calibrated output from one detection engine."""

    engine_id: str
    probability: float  # P(threat / fake / false) in [0, 1]
    available: bool = True
    abstain: bool = False
    evidence: list[Evidence] = field(default_factory=list)
    features: dict[str, Any] = field(default_factory=dict)
    note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.engine_id,
            "p": round(float(self.probability), 4),
            "available": self.available,
            "abstain": self.abstain,
            "evidence": [e.to_dict() for e in self.evidence],
            "features": self.features,
            "note": self.note,
        }


@dataclass
class LockedVerdict:
    verdict: str
    confidence: float  # 0–100 for API compatibility
    abstain: bool
    engines: list[dict[str, Any]]
    evidence: list[dict[str, Any]]
    ece_bucket: str
    domain_shift_warning: bool = False
    path: str = "scamcheck"
    explanation_en: str = ""
    explanation_ur: str = ""
    red_flags: list[Any] | None = None
    sources: list[Any] | None = None
    signals: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict,
            "confidence": self.confidence,
            "abstain": self.abstain,
            "ece_bucket": self.ece_bucket,
            "engines": self.engines,
            "evidence": self.evidence,
            "domain_shift_warning": self.domain_shift_warning,
            "explanation_en": self.explanation_en,
            "explanation_ur": self.explanation_ur,
            "red_flags": self.red_flags,
            "sources": self.sources,
            "signals": self.signals,
            "calibration": {
                "authority": "meta_learner",
                "llm_may_change_verdict": False,
            },
        }
