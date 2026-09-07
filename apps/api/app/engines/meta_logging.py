"""Append-only JSONL of engine vectors for future meta retrain (Phase A5)."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.engines.base import EngineResult, LockedVerdict

logger = logging.getLogger(__name__)

ENGINE_IDS = [
    "url_lgbm",
    "text_scam",
    "rules_pk",
    "fact_nli",
    "deepfake",
    "aigc",
    "provenance",
]

# Repo-local log (gitignored via artifacts/logs if needed); also safe under models/
_DEFAULT_LOG = (
    Path(__file__).resolve().parents[2] / "models" / "artifacts" / "meta_engine_outcomes.jsonl"
)


def engine_vector(results: list[EngineResult]) -> list[float]:
    by_id = {r.engine_id: r for r in results}
    vec: list[float] = []
    for eid in ENGINE_IDS:
        r = by_id.get(eid)
        vec.append(float(r.probability) if r and r.available else 0.0)
        vec.append(0.0 if (not r or r.abstain or not r.available) else 1.0)
    return vec


def log_engine_outcome(
    *,
    check_id: str,
    path: str,
    results: list[EngineResult],
    locked: LockedVerdict,
    text_preview: str = "",
    log_path: Path | None = None,
) -> None:
    """Best-effort append; never raises into the request path."""
    try:
        path_out = log_path or _DEFAULT_LOG
        path_out.parent.mkdir(parents=True, exist_ok=True)
        row: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "check_id": check_id,
            "path": path,
            "verdict": locked.verdict,
            "confidence": locked.confidence,
            "abstain": locked.abstain,
            "vector": engine_vector(results),
            "engine_ids": ENGINE_IDS,
            "text_preview": (text_preview or "")[:240],
            "label": None,  # filled later by human review / delayed labels
        }
        with path_out.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception:
        logger.debug("meta outcome log failed", exc_info=True)
