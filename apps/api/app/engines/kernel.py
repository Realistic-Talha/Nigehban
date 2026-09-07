"""Detection Kernel — fan-out engines, meta lock, narrate."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from app.engines.base import EngineResult, LockedVerdict
from app.engines.entities import extract_entities
from app.engines.fact_nli import run_fact_nli_engine
from app.engines.media_forensics import run_aigc_engine, run_forensics_engine
from app.engines.metadata import run_metadata_engine
from app.engines.meta import lock_verdict
from app.engines.meta_logging import log_engine_outcome
from app.engines.narrate import narrate_locked_verdict
from app.engines.provenance import run_provenance_engine
from app.engines.rules_pk import run_pk_rules
from app.engines.text_scam import run_text_scam_engine
from app.engines.url_reputation import run_url_engine
from app.services.ocr import ocr_service

logger = logging.getLogger(__name__)


_CAMERA_ALIASES = {
    "rne-l21": "OPPO Reno2",
    "cph1917": "OPPO Reno2",
    "z camera": "OPPO / ColorOS camera",
}


def _friendly_camera(exif: dict[str, Any] | None) -> str | None:
    if not exif:
        return None
    make = str(exif.get("make") or "").strip()
    model = str(exif.get("model") or "").strip()
    blob = f"{make} {model}".strip()
    lower = blob.lower()
    for key, label in _CAMERA_ALIASES.items():
        if key in lower:
            return label if not model or model.lower() in key else f"{label} ({model})"
    if make and model:
        return f"{make} {model}"
    return make or model or None


def _compose_authenticity_conclusion(
    locked: LockedVerdict,
    meta: EngineResult | None,
    fora: EngineResult | None,
    aigc: EngineResult | None,
    decision: dict[str, Any] | None = None,
) -> str:
    """Deterministic Hive-style conclusion; LLM narration remains on explanation_en."""
    if decision and decision.get("rule_id") == "conflict_cam_vs_aigc":
        axes = decision.get("axes") or {}
        return (
            "Authenticity is inconclusive because camera EXIF evidence conflicts with elevated "
            f"AIGC signals (S_cam={float(axes.get('s_cam') or 0):.2f}, "
            f"P_ai={float(axes.get('p_ai') or 0):.2f}, "
            f"P_edit={float(axes.get('p_edit') or 0):.2f}). "
            "Per uncertainty-aware forensic fusion, conflicting detectors trigger abstention "
            "rather than a high-confidence Authentic or Manipulated lock. "
            "Upload the original camera JPEG if this was a social/PNG re-export, or treat the "
            "file as unverified for civic decisions."
        )

    exif = (meta.features or {}).get("exif") if meta else {}
    camera = _friendly_camera(exif if isinstance(exif, dict) else None)
    dto = (exif or {}).get("datetime_original") if isinstance(exif, dict) else None
    has_exif = bool(exif)
    aigc_p = float(aigc.probability) if aigc and aigc.available and not aigc.abstain else None
    scores = []
    if fora and fora.features:
        for k in ("ela_p", "noise_p", "edge_p", "cfa_p"):
            v = fora.features.get(k)
            if v is not None:
                scores.append(f"{k.replace('_p', '')}={float(v):.2f}")

    if locked.verdict == "likely_authentic":
        if camera:
            article = "an" if camera[:1].lower() in "aeiou" else "a"
            cam_bit = f" taken with {article} {camera}"
        else:
            cam_bit = " captured by a physical camera"
        time_bit = f" (capture timestamp {dto})" if dto else ""
        meta_bit = (
            "Complete camera EXIF (make/model/settings/timestamps) is consistent with physical hardware."
            if has_exif
            else "Limited metadata was available; authenticity relies on forensic maps and AIGC."
        )
        forensic_bit = (
            "Forensic analysis across Error Level Analysis, residual noise maps, edge sharpness "
            "profiles, and CFA patterns shows uniform compression, natural sensor-noise distribution, "
            "and coherent optical structure with no strong indications of AI generation, compositing, "
            "or digital manipulation."
        )
        aigc_bit = (
            f" The AIGC ensemble score was low ({aigc_p:.2f})."
            if aigc_p is not None
            else " Remote AIGC scoring was offline; the authentic verdict rests on EXIF + classical forensics."
        )
        return (
            f"The image is an authentic, human-captured photograph{cam_bit}{time_bit}. "
            f"{meta_bit} {forensic_bit}{aigc_bit}"
        )

    if locked.verdict == "likely_edited":
        soft = (exif or {}).get("software") if isinstance(exif, dict) else None
        if camera:
            article = "an" if camera[:1].lower() in "aeiou" else "a"
            cam_bit = f" originally captured with {article} {camera}"
        else:
            cam_bit = " shows camera capture metadata"
        time_bit = f" at {dto}" if dto else ""
        edit_bit = (
            f" EXIF lists post-capture editor software ({soft}), which indicates the file was processed after capture."
            if soft
            else " Forensic / metadata signals indicate post-capture editing."
        )
        return (
            f"This is a human-captured photograph{cam_bit}{time_bit}, but it has been edited — not AI-generated. "
            f"{edit_bit} "
            f"Edit/composite likelihood is elevated while AI-generation likelihood remains low"
            f"{f' (P_ai={aigc_p:.2f})' if aigc_p is not None else ''}. "
            "Treat the image as a real scene that may have been retouched, cropped, or color-graded — "
            "not as synthetic AI media, and not as an unmodified camera original."
        )

    if locked.verdict == "likely_manipulated":
        wm = False
        if aigc:
            wm = bool((aigc.features or {}).get("watermark", {}).get("hit"))
        reasons = []
        if aigc_p is not None and aigc_p >= 0.55:
            reasons.append(f"elevated AIGC probability ({aigc_p:.2f})")
        if wm:
            reasons.append("AI-platform watermark pattern (soft boost)")
        if fora and float(fora.probability) >= 0.52:
            reasons.append("suspicious forensic residual structure")
        why = ", ".join(reasons) or "ensemble media signals"
        return (
            f"The image is classified as AI-generated or digitally manipulated based on {why}. "
            "Forensic overlays (ELA, residual noise, edge anomaly, CFA) and metadata were reviewed "
            "alongside the AIGC ensemble. Treat the file as not authentic for civic verification."
        )

    offline = not (aigc and aigc.available and not aigc.abstain)
    rule = (decision or {}).get("rule_label") if decision else None
    return (
        "Authenticity is inconclusive on the available signals. "
        + (f"Decision rule: {rule}. " if rule else "")
        + (
            "AIGC remote scoring was unavailable; "
            if offline
            else f"AIGC score was ambiguous ({aigc_p:.2f}); "
            if aigc_p is not None
            else ""
        )
        + (
            f"camera metadata {'present (' + camera + ')' if camera else 'limited'}; "
            if meta
            else ""
        )
        + (
            f"classical forensic scores: {', '.join(scores)}. "
            if scores
            else "forensic maps incomplete. "
        )
        + "Upload the original camera JPEG (not a social/PNG re-export) for a stronger authenticity call."
    )


def _extract_media_fusion(results: list[EngineResult]) -> dict[str, Any]:
    for r in results:
        blob = (r.features or {}).get("media_fusion")
        if isinstance(blob, dict):
            return blob
    return {}


def _build_authenticity_report(
    locked: LockedVerdict,
    results: list[EngineResult],
    media_url: str,
) -> dict[str, Any]:
    """Hive-style authenticity summary for media UI."""
    by_id = {r.engine_id: r for r in results}
    meta = by_id.get("metadata")
    fora = by_id.get("forensics_ela")
    aigc = by_id.get("aigc")
    fusion = _extract_media_fusion(results)
    decision = fusion.get("decision") if isinstance(fusion.get("decision"), dict) else None
    analytics = fusion.get("analytics") if isinstance(fusion.get("analytics"), dict) else {}

    if locked.verdict == "likely_authentic":
        result_label, authenticity = "Human", "Authentic"
        conf_band = "High" if locked.confidence >= 70 else "Medium"
    elif locked.verdict == "likely_edited":
        result_label, authenticity = "Human (edited)", "Edited"
        conf_band = "High" if locked.confidence >= 70 else "Medium"
    elif locked.verdict == "likely_manipulated":
        result_label, authenticity = "AI-generated", "Not authentic"
        conf_band = "High" if locked.confidence >= 70 else "Medium"
    else:
        result_label, authenticity = "Uncertain", "Inconclusive"
        conf_band = "Low" if locked.abstain or locked.confidence < 55 else "Medium"

    overlays = (fora.features or {}).get("overlays") if fora else {}
    tools = list((fora.features or {}).get("tools") or [])
    if meta:
        tools = ["Metadata Extractor", *tools]
    if aigc and aigc.available and not aigc.abstain:
        tools.append("AIGC ensemble (CLIP zero-shot + UnivFD)")

    return {
        "result": result_label,
        "confidence_band": conf_band,
        "confidence": locked.confidence,
        "authenticity": authenticity,
        "conclusion": _compose_authenticity_conclusion(locked, meta, fora, aigc, decision),
        "media_url": media_url,
        "overlays": overlays or {},
        "overlay_guides": (fora.features or {}).get("overlay_guides") if fora else {},
        "overlay_params": (fora.features or {}).get("overlay_params") if fora else {},
        "tools": tools,
        "decision": decision,
        "analytics": analytics,
        "domain_shift_warning": locked.domain_shift_warning,
        "metadata": {
            "exif": (meta.features or {}).get("exif") if meta else {},
            "iptc": (meta.features or {}).get("iptc") if meta else {},
            "icc": (meta.features or {}).get("icc") if meta else {},
            "c2pa": (meta.features or {}).get("c2pa") if meta else {},
            "other": {
                "suspicious": (meta.features or {}).get("suspicious") if meta else [],
                "integrity_score": (meta.features or {}).get("integrity_score") if meta else None,
                "s_cam": (meta.features or {}).get("s_cam") if meta else None,
                "camera_capture_likely": (meta.features or {}).get("camera_capture_likely") if meta else False,
            },
        },
        "forensic_scores": {
            "ela": (fora.features or {}).get("ela_p") if fora else None,
            "residual_noise": (fora.features or {}).get("noise_p") if fora else None,
            "edge_anomaly": (fora.features or {}).get("edge_p") if fora else None,
            "cfa": (fora.features or {}).get("cfa_p") if fora else None,
            "aigc": aigc.probability if aigc and aigc.available else None,
        },
    }


async def _normalize_text(input_data: dict[str, Any], check_type: str) -> tuple[str, dict[str, Any]]:
    """OCR when image upload present; prefer API input_type over intake guess."""
    text = (input_data.get("text") or input_data.get("submitted_text") or "").strip()
    media_url = input_data.get("media_url") or ""
    input_type = input_data.get("input_type") or ""
    trail_note: dict[str, Any] = {"ocr": None}

    need_ocr = bool(media_url) and (
        input_type == "image"
        or check_type == "media_check"
        or (not text and media_url)
    )
    # Scam screenshot path
    if need_ocr and check_type in ("scam_report", "media_check", "claim"):
        if check_type == "scam_report" or input_type == "image" or not text:
            try:
                if media_url.startswith("http://") or media_url.startswith("https://"):
                    ocr_text = await ocr_service.extract_text_from_url(media_url)
                else:
                    from app.services.storage import storage

                    data = await storage.download_file(media_url)
                    ocr_text = await ocr_service.extract_text(data)
                trail_note["ocr"] = {"extracted_chars": len(ocr_text or ""), "ok": bool(ocr_text)}
                if ocr_text:
                    text = f"{text}\n{ocr_text}".strip() if text else ocr_text
            except Exception as exc:
                logger.warning("OCR normalize failed: %s", exc)
                trail_note["ocr"] = {"ok": False, "error": str(exc)}
    return text, trail_note


class DetectionKernel:
    """Production detection entry — meta_learner is verdict authority."""

    async def process(
        self,
        input_data: dict[str, Any],
        check_id: str,
        check_type: str,
        path: str | None = None,
    ) -> dict[str, Any]:
        path = path or {
            "claim": "factcheck",
            "scam_report": "scamcheck",
            "media_check": "mediacheck",
        }.get(check_type, "factcheck")

        text, norm_meta = await _normalize_text(input_data, check_type)
        entities = extract_entities(text)
        media_url = input_data.get("media_url") or ""

        results: list[EngineResult] = []
        domain_shift = False

        if path == "scamcheck":
            url_r, text_r, rules_r = await asyncio.gather(
                asyncio.to_thread(run_url_engine, entities["urls"]),
                asyncio.to_thread(run_text_scam_engine, text),
                asyncio.to_thread(run_pk_rules, text),
            )
            results = [url_r, text_r, rules_r]

        elif path == "factcheck":
            fact_r = await run_fact_nli_engine(text)
            results = [fact_r]
            # Attach sources onto locked later
        else:
            # Media: metadata + classical forensics overlays + AIGC (no deepfake)
            meta_r, aigc = await asyncio.gather(
                run_metadata_engine(media_url),
                run_aigc_engine(media_url),
            )
            has_exif = bool((meta_r.features or {}).get("has_exif"))
            forensics, prov = await asyncio.gather(
                run_forensics_engine(media_url, has_exif=has_exif),
                run_provenance_engine(media_url),
            )
            results = [meta_r, forensics, aigc, prov]
            domain_shift = bool(forensics.features.get("domain_shift_warning")) or (
                not has_exif and not (meta_r.features or {}).get("camera_capture_likely")
            )

        locked = lock_verdict(path, results, domain_shift_warning=domain_shift)
        log_engine_outcome(
            check_id=check_id,
            path=path,
            results=results,
            locked=locked,
            text_preview=text,
        )

        if path == "factcheck":
            nli = results[0]
            locked.sources = (nli.features or {}).get("sources") or []
        if path == "scamcheck":
            locked.red_flags = [
                e.get("signal") for e in locked.evidence if e.get("type") in ("rule", "text", "url")
            ]

        locked.signals = {
            "entities": {k: entities[k] for k in ("urls", "phones", "brands", "domains")},
            "normalize": norm_meta,
        }

        locked = await narrate_locked_verdict(locked, original_text=text)
        out = locked.to_dict()
        out["id"] = check_id
        out["type"] = check_type
        out["created_at"] = datetime.now(timezone.utc).isoformat()

        if path == "mediacheck":
            out["authenticity_report"] = _build_authenticity_report(locked, results, media_url)

        out["agent_trail"] = [
            {
                "agent_name": "detection_kernel",
                "status": "complete",
                "output_summary": f"{locked.verdict} conf={locked.confidence} abstain={locked.abstain}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            *[
                {
                    "agent_name": r.engine_id,
                    "status": "complete" if r.available else "offline",
                    "output_summary": r.note or f"p={r.probability:.3f}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                for r in results
            ],
            {
                "agent_name": "meta_learner",
                "status": "complete",
                "output_summary": f"locked {locked.verdict} @ {locked.confidence}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            {
                "agent_name": "narrate",
                "status": "complete",
                "output_summary": (locked.explanation_en or "")[:160],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        ]
        return out


detection_kernel = DetectionKernel()
