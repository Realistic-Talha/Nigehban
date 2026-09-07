"""Media provenance — Hamming pHash near-dupe + optional FactCheck imageSearch."""

from __future__ import annotations

import logging
from typing import Any

import httpx
from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.engines.base import EngineResult, Evidence
from app.models.media_fingerprint import MediaFingerprint
from app.services.media_fingerprint import compute_image_fingerprint

logger = logging.getLogger(__name__)


def _hamming(a: str, b: str) -> int:
    if not a or not b or len(a) != len(b):
        return 64
    return sum(ch1 != ch2 for ch1, ch2 in zip(a, b))


async def _factcheck_image(image_uri: str) -> list[dict[str, Any]]:
    key = getattr(settings, "GOOGLE_FACTCHECK_API_KEY", "") or ""
    if not key or not image_uri.startswith("http"):
        return []
    url = "https://factchecktools.googleapis.com/v1alpha1/claims:imageSearch"
    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            resp = await client.get(url, params={"imageUri": image_uri, "key": key})
            if resp.status_code != 200:
                return []
            return (resp.json().get("claims") or [])
    except Exception:
        logger.warning("FactCheck imageSearch failed", exc_info=True)
        return []


async def run_provenance_engine(media_url: str) -> EngineResult:
    if not media_url:
        return EngineResult(engine_id="provenance", probability=0.0, abstain=True, note="No media")

    fp = await compute_image_fingerprint(media_url)
    if not fp or not fp.get("phash"):
        return EngineResult(
            engine_id="provenance",
            probability=0.0,
            abstain=True,
            note="Fingerprint failed",
        )

    phash = fp["phash"]
    matches: list[dict[str, Any]] = []
    evidence: list[Evidence] = []
    try:
        async with AsyncSessionLocal() as session:
            rows = (await session.execute(select(MediaFingerprint).limit(500))).scalars().all()
            for row in rows:
                if not row.phash:
                    continue
                dist = _hamming(phash, row.phash)
                if dist <= 10:
                    matches.append({
                        "media_check_id": str(row.media_check_id),
                        "hamming": dist,
                        "phash": row.phash,
                    })
                    evidence.append(
                        Evidence(
                            type="phash",
                            value=str(row.media_check_id),
                            signal="near_duplicate",
                            detail=f"hamming={dist}",
                        )
                    )
    except Exception:
        logger.exception("Provenance DB scan failed")

    # Public HTTP(S) URLs only for FactCheck image API
    if media_url.startswith("http://") or media_url.startswith("https://"):
        if "uploads" not in media_url:  # skip local relative paths
            for c in await _factcheck_image(media_url):
                evidence.append(
                    Evidence(
                        type="claimreview_image",
                        value=c.get("text") or "",
                        signal="factcheck_image",
                    )
                )

    if matches:
        # Prior sighting ≠ authenticity (could be same AI image re-uploaded). Mild uncertainty only.
        p = 0.45
        return EngineResult(
            engine_id="provenance",
            probability=p,
            evidence=evidence,
            features={"match_found": True, "matches": matches, "phash": phash, "file_hash": fp.get("file_hash")},
            note="Near-duplicate of a prior upload — not proof of authenticity or manipulation",
        )

    return EngineResult(
        engine_id="provenance",
        probability=0.2,
        abstain=True,
        evidence=evidence,
        features={"match_found": False, "matches": [], "phash": phash, "file_hash": fp.get("file_hash")},
        note="No near-dupe in corpus",
    )
