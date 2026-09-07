"""Image metadata extractor — EXIF / IPTC / ICC / C2PA presence."""

from __future__ import annotations

import io
import logging
import re
from typing import Any

from PIL import Image

from app.engines.base import EngineResult, Evidence
from app.services.storage import storage

logger = logging.getLogger(__name__)

try:
    import exifread

    _HAS_EXIFREAD = True
except ImportError:
    _HAS_EXIFREAD = False

_EDIT_APPS = (
    "photoshop",
    "gimp",
    "lightroom",
    "snapseed",
    "picsart",
    "canva",
    "affinity",
    "capture one",
    "darktable",
)
_GEN_APPS = (
    "midjourney",
    "stable diffusion",
    "dall",
    "gemini",
    "firefly",
    "imagen",
    "leonardo",
    "ideogram",
)


def _tag_str(tags: dict, *keys: str) -> str | None:
    for k in keys:
        if k in tags:
            return str(tags[k]).strip() or None
    return None


def extract_metadata_sync(data: bytes) -> dict[str, Any]:
    """Parse metadata from raw image bytes (CPU-bound)."""
    suspicious: list[str] = []
    exif: dict[str, Any] = {}
    iptc: dict[str, Any] = {}
    icc: dict[str, Any] = {}
    c2pa: dict[str, Any] = {"present": False}

    # C2PA / JUMBF markers (presence only — no crypto verify without c2pa-python)
    lower = data[: min(len(data), 2_000_000)]
    if b"c2pa" in lower.lower() or b"jumb" in lower.lower() or b"c2ma" in lower.lower():
        c2pa = {"present": True, "note": "C2PA/JUMBF box detected (not cryptographically verified)"}

    if _HAS_EXIFREAD:
        try:
            tags = exifread.process_file(io.BytesIO(data), details=True)
            if tags:
                make = _tag_str(tags, "Image Make")
                model = _tag_str(tags, "Image Model")
                soft = _tag_str(tags, "Image Software")
                dto = _tag_str(tags, "EXIF DateTimeOriginal", "Image DateTime")
                lens = _tag_str(tags, "EXIF LensModel")
                focal = _tag_str(tags, "EXIF FocalLength")
                fnum = _tag_str(tags, "EXIF FNumber")
                iso = _tag_str(tags, "EXIF ISOSpeedRatings", "EXIF PhotographicSensitivity")
                flash = _tag_str(tags, "EXIF Flash")
                orient = _tag_str(tags, "Image Orientation")
                exif = {
                    k: v
                    for k, v in {
                        "make": make,
                        "model": model,
                        "software": soft,
                        "datetime_original": dto,
                        "lens": lens,
                        "focal_length": focal,
                        "f_number": fnum,
                        "iso": iso,
                        "flash": flash,
                        "orientation": orient,
                    }.items()
                    if v
                }
                if "GPS GPSLatitude" in tags:
                    exif["gps"] = {
                        "latitude": str(tags.get("GPS GPSLatitude")),
                        "longitude": str(tags.get("GPS GPSLongitude")),
                    }
                # Lightweight IPTC-ish from common tags if present
                for label, keys in {
                    "artist": ("Image Artist",),
                    "copyright": ("Image Copyright",),
                    "description": ("Image ImageDescription",),
                }.items():
                    val = _tag_str(tags, *keys)
                    if val:
                        iptc[label] = val
            else:
                suspicious.append("EXIF data missing or stripped")
        except Exception as exc:
            logger.warning("exifread failed: %s", exc)
            suspicious.append(f"EXIF parse error: {exc}")
    else:
        suspicious.append("exifread not installed")

    try:
        img = Image.open(io.BytesIO(data))
        if getattr(img, "info", None):
            if img.info.get("icc_profile"):
                icc = {
                    "present": True,
                    "bytes": len(img.info["icc_profile"]),
                    "note": "ICC color profile embedded",
                }
            else:
                icc = {"present": False}
            # XMP / IPTC sometimes in info
            for key in ("xml", "xmp", "iptc"):
                if key in img.info and img.info[key]:
                    iptc[key] = "present"
            soft = exif.get("software") or img.info.get("software")
            if soft:
                soft_l = str(soft).lower()
                if any(s in soft_l for s in _GEN_APPS):
                    suspicious.append(f"Generative AI software tag in metadata: {soft}")
                elif any(s in soft_l for s in _EDIT_APPS):
                    suspicious.append(f"Post-capture editor in metadata: {soft}")
                    exif.setdefault("software", soft)
    except Exception as exc:
        suspicious.append(f"Pillow open failed: {exc}")

    has_camera = bool(exif.get("make") or exif.get("model"))
    has_dto = bool(exif.get("datetime_original"))
    soft_l = str(exif.get("software") or "").lower()
    edit_software = any(s in soft_l for s in _EDIT_APPS) or any(
        "post-capture editor" in str(s).lower() for s in suspicious
    )
    gen_software = any(s in soft_l for s in _GEN_APPS) or any(
        "generative ai software" in str(s).lower() for s in suspicious
    )

    # Integrity: camera hardware EXIF; editors lower integrity slightly; generative tanks it
    if gen_software:
        integrity = 25.0
    elif has_camera and has_dto:
        integrity = 78.0 if edit_software else 88.0
    elif exif:
        integrity = 55.0 if edit_software else 62.0
    else:
        integrity = 35.0
        if "EXIF data missing or stripped" not in suspicious:
            suspicious.append("No camera EXIF — common for AI exports and social recompression")

    from app.engines.media_fusion import compute_s_cam_and_threat

    base_feat = {
        "exif": exif,
        "suspicious": suspicious,
        "integrity_score": integrity,
        "edit_software": edit_software,
        "generative_software": gen_software,
    }
    s_cam, p_threat, camera_capture_likely = compute_s_cam_and_threat(base_feat)

    # Editing software raises metadata threat toward "edited", not AI
    if edit_software and not gen_software:
        p_threat = max(float(p_threat), 0.42)

    return {
        "has_exif": bool(exif),
        "exif": exif,
        "iptc": iptc,
        "icc": icc,
        "c2pa": c2pa,
        "suspicious": suspicious,
        "integrity_score": integrity,
        "s_cam": s_cam,
        "p_threat": p_threat,
        "camera_capture_likely": camera_capture_likely,
        "edit_software": edit_software,
        "generative_software": gen_software,
    }


async def run_metadata_engine(media_url: str) -> EngineResult:
    if not media_url:
        return EngineResult(engine_id="metadata", probability=0.0, abstain=True, available=False)
    try:
        data = await storage.download_file(media_url)
        meta = extract_metadata_sync(data)
    except Exception as exc:
        return EngineResult(
            engine_id="metadata",
            probability=0.0,
            available=False,
            abstain=True,
            note=str(exc),
        )

    evidence: list[Evidence] = []
    if meta["exif"].get("make") or meta["exif"].get("model"):
        cam = " ".join(filter(None, [meta["exif"].get("make"), meta["exif"].get("model")]))
        evidence.append(Evidence(type="metadata", value=cam, signal="camera_model"))
    if meta["exif"].get("datetime_original"):
        evidence.append(
            Evidence(type="metadata", value=str(meta["exif"]["datetime_original"]), signal="datetime_original")
        )
    for s in meta["suspicious"][:4]:
        evidence.append(Evidence(type="metadata", value=s, signal="suspicious_metadata"))
    if meta["c2pa"].get("present"):
        evidence.append(Evidence(type="metadata", value="C2PA box present", signal="c2pa_present"))

    note_parts = []
    if meta["camera_capture_likely"]:
        note_parts.append(
            f"Camera EXIF consistent with hardware capture (S_cam={float(meta['s_cam']):.2f})"
        )
    elif not meta["has_exif"]:
        note_parts.append("No EXIF — AI exports / social apps often strip metadata")
    else:
        note_parts.append(f"Partial camera prior (S_cam={float(meta['s_cam']):.2f})")
    if meta["c2pa"].get("present"):
        note_parts.append("C2PA present (unverified)")

    return EngineResult(
        engine_id="metadata",
        probability=float(meta["p_threat"]),
        evidence=evidence,
        features=meta,
        note=" — ".join(note_parts),
        abstain=False,
    )
