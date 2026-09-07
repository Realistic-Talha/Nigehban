"""LLM narration only — cannot change locked verdict or confidence."""

from __future__ import annotations

import logging
from typing import Any

from app.engines.base import LockedVerdict
from app.services.llm import llm_service

logger = logging.getLogger(__name__)

_NARRATE_PROMPT = """\
You are Nigehban's explanation writer for Pakistan users.
You receive a LOCKED verdict from calibrated detection engines. You MUST NOT change
the verdict label or the confidence number. Only explain the evidence in clear English
and natural Urdu.

Rules:
- Do NOT invent facts. Only cite engine ids, scores, and evidence signals provided.
- A perceptual-hash / near-duplicate match is NOT proof the image is authentic or from a
  trusted source — it only means a similar file was seen before (could be the same AI image).
  Never invent phrases like "known authentic reference" for phash matches.
- Media uses three-axis fusion: P_ai (AI generation), P_edit (classical forensics),
  S_cam (camera EXIF prior). Confidence is calibrated from axis agreement — NEVER treat a
  single engine probability as the locked confidence.
- If verdict is likely_authentic: write like a forensic authenticity report — Human / Authentic,
  cite camera EXIF (make/model/datetime) when present, and state that ELA, residual noise, edge,
  and CFA maps look consistent with a real camera capture. Do not invent camera models or scenes.
- If verdict is likely_edited: clearly say HUMAN-CAPTURED BUT EDITED — not AI-generated. Cite
  editor software (Lightroom/Photoshop) and/or forensic edit signals. Distinguish editing from AI.
- If verdict is likely_manipulated: explain AI-generated / Not authentic using AIGC and/or watermark,
  and note weak/absent camera EXIF when relevant. Do not call AI images merely "edited".
- If verdict is inconclusive / conflict: explain that camera EXIF and AIGC disagree (or soft band),
  and that the system abstained rather than overclaiming. Do not sound 90% sure.
- If the aigc engine is unavailable / abstaining, say AI-generation detection was not available.
- A LOW aigc score alone is NOT enough for "authentic" unless the locked verdict is likely_authentic.
- Media checks do not run the deepfake engine; rely on metadata + forensics + aigc.
- Do not overclaim. Match tone to the locked verdict (especially inconclusive).
- Fact-check path: if locked verdict is false or misleading, write a CONCLUSIVE statement —
  e.g. the viral claim is false / misleading — and cite the fact-check source titles provided
  in evidence (falsely claims, does not show, Fact check, etc.). Do NOT say "unverified" or
  "abstained" when the locked verdict is false/misleading/true.
- Fact-check true: state the claim is supported by the cited sources.
- Fact-check unverified only: say evidence was insufficient for a true/false call.

Return ONLY JSON:
{
  "explanation_en": "3-5 forensic-style sentences citing evidence signals",
  "explanation_ur": "2-4 sentences Urdu"
}
"""


async def narrate_locked_verdict(locked: LockedVerdict, original_text: str = "") -> LockedVerdict:
    payload = {
        "verdict": locked.verdict,
        "confidence": locked.confidence,
        "abstain": locked.abstain,
        "evidence": locked.evidence[:12],
        "sources": (getattr(locked, "sources", None) or [])[:8],
        "engines": [
            {"id": e.get("id"), "p": e.get("p"), "note": e.get("note")}
            for e in locked.engines
        ],
        "domain_shift_warning": locked.domain_shift_warning,
        "input_preview": (original_text or "")[:400],
    }
    try:
        result = await llm_service.call_haiku(
            _NARRATE_PROMPT,
            [{"role": "user", "content": str(payload)}],
            max_tokens=800,
        )
        parsed = result.get("json") if isinstance(result, dict) else None
        if parsed and isinstance(parsed, dict):
            locked.explanation_en = str(parsed.get("explanation_en") or locked.explanation_en)
            locked.explanation_ur = str(parsed.get("explanation_ur") or locked.explanation_ur)
    except Exception:
        logger.warning("Narration LLM failed — using template", exc_info=True)

    if not locked.explanation_en:
        titles = []
        for s in (getattr(locked, "sources", None) or [])[:4]:
            if isinstance(s, dict) and s.get("title"):
                titles.append(str(s["title"])[:80])
        src_bit = ("; ".join(titles)) if titles else (
            ", ".join(e.get("signal", "") for e in locked.evidence[:5]) or "limited signals"
        )
        v = locked.verdict
        if v == "false":
            locked.explanation_en = (
                f"This claim is false (confidence {locked.confidence:.0f}%). "
                f"Cited sources: {src_bit}."
            )
        elif v == "true":
            locked.explanation_en = (
                f"This claim is true (confidence {locked.confidence:.0f}%). "
                f"Cited sources: {src_bit}."
            )
        elif v == "misleading":
            locked.explanation_en = (
                f"This claim is misleading (confidence {locked.confidence:.0f}%). "
                f"Cited sources: {src_bit}."
            )
        else:
            locked.explanation_en = (
                f"Could not verify this claim conclusively (confidence {locked.confidence:.0f}%). "
                f"Evidence reviewed: {src_bit}."
            )
        if locked.domain_shift_warning:
            locked.explanation_en += " Social-media recompression may reduce media-model reliability."
    if not locked.explanation_ur:
        locked.explanation_ur = (
            f"حتمی نتیجہ: {locked.verdict} (اعتماد {locked.confidence:.0f})۔ "
            "تفصیل انگریزی وضاحت میں موجود ہے۔"
        )
    return locked
