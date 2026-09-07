"""Visual media engines — ELA forensics + optional deepfake/AIGC ONNX."""

from __future__ import annotations

import asyncio
import io
import logging
from typing import Any

import numpy as np
from PIL import Image

from app.engines.artifacts import load_onnx_session
from app.engines.base import EngineResult, Evidence
from app.services.storage import storage

logger = logging.getLogger(__name__)

try:
    import cv2

    _HAS_CV2 = True
except ImportError:
    _HAS_CV2 = False


def _load_image(data: bytes) -> Image.Image:
    return Image.open(io.BytesIO(data)).convert("RGB")


def _png_bytes(arr_u8: np.ndarray) -> bytes:
    buf = io.BytesIO()
    Image.fromarray(arr_u8).save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def _percentile_norm(gray: np.ndarray, lo: float = 2.0, hi: float = 98.0) -> np.ndarray:
    """Robust [0,1] stretch — avoids one hot pixel washing out the whole map."""
    g = np.asarray(gray, dtype=np.float32)
    p_lo, p_hi = np.percentile(g, [lo, hi])
    if p_hi <= p_lo + 1e-6:
        return np.zeros_like(g, dtype=np.float32)
    return np.clip((g - p_lo) / (p_hi - p_lo), 0.0, 1.0)


def _turbo_rgb(gray_f: np.ndarray) -> np.ndarray:
    """Approx Turbo / forensic heat colormap (dark→cyan→yellow→red→white)."""
    g = np.clip(gray_f, 0.0, 1.0)
    r = np.clip(1.6 * g - 0.15, 0, 1)
    gg = np.clip(1.4 - abs(g - 0.45) * 2.4, 0, 1) * (0.35 + 0.65 * (1 - g))
    # Boost mid greens for readability
    gg = np.clip(gg + 0.25 * np.sin(np.pi * g), 0, 1)
    b = np.clip(1.15 - 1.35 * g, 0, 1)
    # Hot tip
    r = np.clip(r + np.maximum(g - 0.85, 0) * 2.0, 0, 1)
    rgb = np.stack([r, gg, b], axis=-1)
    return (rgb * 255).astype(np.uint8)


def _blend_heatmap_on_gray(base_rgb: np.ndarray, heat_f: np.ndarray, alpha: float = 0.55) -> np.ndarray:
    """Blend forensic heat onto a desaturated original for spatial context."""
    base = base_rgb.astype(np.float32)
    gray = (0.299 * base[:, :, 0] + 0.587 * base[:, :, 1] + 0.114 * base[:, :, 2])[:, :, None]
    gray3 = np.repeat(gray, 3, axis=2) * 0.55
    heat = _turbo_rgb(heat_f).astype(np.float32)
    # Only tint where heat is meaningful
    w = np.clip(heat_f[..., None] * alpha * 1.4, 0, alpha)
    out = gray3 * (1 - w) + heat * w
    return np.clip(out, 0, 255).astype(np.uint8)


def _ela_map(work: Image.Image, quality: int = 95, amplify: float = 18.0) -> tuple[np.ndarray, float, float, list[str]]:
    """FotoForensics-style ELA: re-JPEG @ quality, abs diff, amplify, percentile display."""
    notes: list[str] = []
    buf = io.BytesIO()
    work.save(buf, "JPEG", quality=quality, optimize=False)
    buf.seek(0)
    resaved = Image.open(buf).convert("RGB")
    orig = np.asarray(work, dtype=np.float32)
    re_ = np.asarray(resaved, dtype=np.float32)
    diff = np.abs(orig - re_)
    # Classic RGB amplify (clipped) — matches FotoForensics look
    ela_rgb = np.clip(diff * amplify, 0, 255).astype(np.uint8)
    # Magnitude for scoring + heatmap variant
    mag = diff.mean(axis=2)
    ela_mean, ela_std = float(mag.mean()), float(mag.std())
    ela_p = min(0.95, (ela_std / 8.0) * 0.45 + (ela_mean / 12.0) * 0.55)
    if ela_std > 6.0:
        notes.append(f"Elevated ELA variance ({ela_std:.1f})")
    if ela_mean > 5.0:
        notes.append(f"Elevated ELA mean residual ({ela_mean:.1f})")
    if float(mag.max()) <= 1.0:
        notes.append("ELA flat — uniform compression history")
        ela_p = min(ela_p, 0.15)
    # Prefer heatmap-on-context for UI clarity
    heat = _percentile_norm(mag, 5, 99.5)
    display = _blend_heatmap_on_gray(orig.astype(np.uint8), heat, alpha=0.65)
    # Mix a touch of classic amplified ELA so bright patches remain visible
    display = np.clip(0.55 * display.astype(np.float32) + 0.45 * ela_rgb.astype(np.float32), 0, 255).astype(np.uint8)
    return display, float(ela_p), float(ela_std), notes


def _noise_map(arr: np.ndarray) -> tuple[np.ndarray, float, list[str]]:
    """High-pass residual + local noise inconsistency map."""
    notes: list[str] = []
    if not _HAS_CV2:
        return np.zeros_like(arr), 0.2, ["OpenCV unavailable — noise map limited"]

    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY).astype(np.float32)
    # Mild denoise estimate; residual = sensor/process noise
    blur = cv2.GaussianBlur(gray, (0, 0), 1.4)
    residual = gray - blur
    res_std = float(residual.std())

    k = 9
    mu = cv2.blur(residual, (k, k))
    mu2 = cv2.blur(residual * residual, (k, k))
    local_std = np.sqrt(np.maximum(mu2 - mu * mu, 0))
    # Coefficient of variation patch map highlights inconsistent regions
    local_n = _percentile_norm(local_std, 5, 99)

    noise_p = 0.15
    if res_std < 1.5:
        notes.append("Very low residual noise — possible heavy smoothing / generative clean-up")
        noise_p = 0.55
    elif res_std > 18:
        notes.append("High residual noise — possible heavy compression")
        noise_p = 0.35
    patch_cv = float(local_std.std() / (local_std.mean() + 1e-6))
    if patch_cv > 1.8:
        notes.append("Inconsistent residual-noise patches")
        noise_p = max(noise_p, 0.48)

    display = _blend_heatmap_on_gray(arr, local_n, alpha=0.62)
    return display, float(noise_p), notes


def _edge_anomaly_map(arr: np.ndarray) -> tuple[np.ndarray, float, list[str]]:
    """Edge energy anomaly: local Laplacian z-score vs neighborhood (not raw edges)."""
    notes: list[str] = []
    if not _HAS_CV2:
        return np.zeros_like(arr), 0.2, ["OpenCV unavailable — edge map limited"]

    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY).astype(np.float32)
    lap = cv2.Laplacian(gray, cv2.CV_32F, ksize=3)
    energy = np.abs(lap)
    # Local mean/std of energy — anomalies are patches that don't match neighbors
    k = 15
    mu = cv2.blur(energy, (k, k))
    mu2 = cv2.blur(energy * energy, (k, k))
    local_std = np.sqrt(np.maximum(mu2 - mu * mu, 0))
    z = np.abs(energy - mu) / (local_std + 1e-3)
    z_n = _percentile_norm(z, 5, 99)

    lap_var = float(lap.var())
    edge_p = 0.15
    if lap_var < 12:
        notes.append("Extremely low edge variance — possible heavy smoothing / GAN blur")
        edge_p = 0.50
    elif lap_var < 25:
        notes.append("Low edge variance — soft optics or mild smoothing")
        edge_p = 0.28
    elif lap_var > 8000:
        notes.append("Extreme edge variance — possible compression / sharpening artifacts")
        edge_p = 0.40

    channel_vars = [float(np.var(arr[:, :, c].astype(np.float32))) for c in range(3)]
    ratio = max(channel_vars) / (min(channel_vars) + 1e-6)
    if ratio > 3.5:
        notes.append("Inconsistent color-channel noise")
        edge_p = max(edge_p, 0.45)

    # High anomaly mass → bump edit likelihood slightly
    if float(z_n.mean()) > 0.35:
        edge_p = max(edge_p, 0.38)

    display = _blend_heatmap_on_gray(arr, z_n, alpha=0.60)
    return display, float(edge_p), notes


def _cfa_map(arr: np.ndarray) -> tuple[np.ndarray, float, list[str]]:
    """Period-2 Bayer lattice energy — cameras leave 2×2 demosaic structure; AI/heavy edits often don't."""
    notes: list[str] = []
    if not _HAS_CV2:
        return np.zeros_like(arr), 0.2, ["OpenCV unavailable — CFA map limited"]

    # Green channel carries strongest CFA periodicity on Bayer sensors
    g = arr[:, :, 1].astype(np.float32)
    # Period-2 horizontal + vertical difference (classic CFA fingerprint cue)
    dh = np.abs(g[:, 1:] - g[:, :-1])
    dv = np.abs(g[1:, :] - g[:-1, :])
    # Pad back to full size
    dh_full = np.zeros_like(g)
    dv_full = np.zeros_like(g)
    dh_full[:, 1:] = dh
    dh_full[:, 0] = dh[:, 0] if dh.shape[1] else 0
    dv_full[1:, :] = dv
    dv_full[0, :] = dv[0, :] if dv.shape[0] else 0

    g_blur = cv2.GaussianBlur(g, (3, 3), 0)
    cfa_res = np.abs(g - g_blur)
    # Period-2 lattice energy + demosaic residual
    lattice = dh_full + dv_full
    lattice = cv2.GaussianBlur(lattice, (3, 3), 0)
    combo = 0.55 * _percentile_norm(cfa_res, 5, 99) + 0.45 * _percentile_norm(lattice, 5, 99)

    cfa_std = float(cfa_res.std())
    cfa_p = 0.18
    if cfa_std < 0.6:
        notes.append("Near-zero CFA/demosaic residual — possible non-camera / over-smoothed pipeline")
        cfa_p = 0.48
    elif cfa_std < 1.0:
        notes.append("Mildly weak CFA residual structure")
        cfa_p = 0.28
    else:
        notes.append("CFA residual energy consistent with demosaiced camera capture")
        cfa_p = 0.15

    display = _blend_heatmap_on_gray(arr, combo, alpha=0.58)
    return display, float(cfa_p), notes


def build_forensic_overlays(image: Image.Image, max_side: int = 1024) -> dict[str, Any]:
    """Compute ELA / residual noise / edge anomaly / CFA maps + scores.

    Overlays use robust percentile heatmaps blended on the original for spatial context.
    """
    w, h = image.size
    scale = min(1.0, max_side / max(w, h))
    work = image.convert("RGB")
    if scale < 1:
        work = work.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.Resampling.LANCZOS)
    arr = np.asarray(work, dtype=np.uint8)
    notes: list[str] = []

    ela_img, ela_p, _ela_std, ela_notes = _ela_map(work, quality=95, amplify=18.0)
    notes.extend(ela_notes)

    if _HAS_CV2:
        noise_img, noise_p, n_notes = _noise_map(arr)
        edge_img, edge_p, e_notes = _edge_anomaly_map(arr)
        cfa_img, cfa_p, c_notes = _cfa_map(arr)
        notes.extend(n_notes)
        notes.extend(e_notes)
        notes.extend(c_notes)
        overlays = {
            "ela": _png_bytes(ela_img),
            "residual_noise": _png_bytes(noise_img),
            "edge_anomaly": _png_bytes(edge_img),
            "cfa": _png_bytes(cfa_img),
        }
        overlay_guides = {
            "ela": "Bright / warm patches = different JPEG compression history (possible paste/edit). Uniform mid tones are normal.",
            "residual_noise": "Warm islands = noise statistics that don't match neighbors (splice / heavy retouch).",
            "edge_anomaly": "Warm = edge sharpness inconsistent with local context (not merely 'all edges').",
            "cfa": "Warm structure = Bayer/demosaic period-2 energy. Flat/dark can mean over-smoothing or non-camera pipeline.",
        }
    else:
        noise_p, edge_p, cfa_p = 0.2, 0.2, 0.2
        overlays = {"ela": _png_bytes(ela_img)}
        overlay_guides = {
            "ela": "Bright / warm patches = different JPEG compression history (possible paste/edit).",
        }
        notes.append("OpenCV unavailable — limited forensic maps")

    # ELA + residual noise dominate for compression; explicit edit notes / edge channel
    # inconsistency must still raise aggregate P_edit (do not bury under soft*0.5).
    p = max(float(ela_p), float(noise_p))
    soft = 0.5 * float(edge_p) + 0.5 * float(cfa_p)
    if any("inconsistent color-channel" in n.lower() for n in notes):
        p = max(p, 0.52)
    if soft >= 0.45 and p < 0.25:
        p = max(p, 0.40)
    elif soft >= 0.35:
        p = max(p, min(0.48, soft * 0.85))
    else:
        p = max(p, soft * 0.5)
    return {
        "ela_p": float(ela_p),
        "noise_p": float(noise_p),
        "edge_p": float(edge_p),
        "cfa_p": float(cfa_p),
        "p": float(p),
        "notes": notes,
        "overlays": overlays,
        "overlay_guides": overlay_guides,
        "overlay_params": {
            "ela_quality": 95,
            "ela_amplify": 18,
            "analysis_max_side": max_side,
            "colormap": "turbo_blend_on_original",
        },
        "size": list(image.size),
        "analysis_size": list(work.size),
    }


async def run_forensics_engine(media_url: str, has_exif: bool | None = None) -> EngineResult:
    if not media_url:
        return EngineResult(engine_id="forensics_ela", probability=0.0, abstain=True)
    try:
        data = await storage.download_file(media_url)
        image = _load_image(data)
    except Exception as exc:
        return EngineResult(
            engine_id="forensics_ela",
            probability=0.0,
            available=False,
            note=str(exc),
        )

    bundle = await asyncio.to_thread(build_forensic_overlays, image)
    overlay_urls: dict[str, str] = {}
    for name, png in (bundle.get("overlays") or {}).items():
        try:
            url = await storage.upload_file(png, f"forensic_{name}.png", "image/png")
            overlay_urls[name] = url
        except Exception:
            logger.warning("Failed to store forensic overlay %s", name, exc_info=True)

    evidence = [
        Evidence(type="forensics", value=n, signal="ela_or_noise")
        for n in bundle["notes"]
    ]
    shift = detect_domain_shift(image, has_exif)
    tools = ["ELA image", "Residual noise maps", "Edge anomaly heat map", "CFA pattern analysis"]
    return EngineResult(
        engine_id="forensics_ela",
        probability=float(bundle["p"]),
        evidence=evidence,
        features={
            "ela_p": bundle["ela_p"],
            "noise_p": bundle["noise_p"],
            "edge_p": bundle["edge_p"],
            "cfa_p": bundle["cfa_p"],
            "notes": list(bundle["notes"]),
            "domain_shift_warning": shift,
            "size": bundle["size"],
            "analysis_size": bundle["analysis_size"],
            "overlays": overlay_urls,
            "overlay_guides": bundle.get("overlay_guides") or {},
            "overlay_params": bundle.get("overlay_params") or {},
            "tools": tools,
        },
        note="ELA + residual noise + edge anomaly + CFA",
        abstain=not evidence,
    )


# Keep legacy helpers for any imports / tests
def error_level_analysis(image: Image.Image, quality: int = 90) -> tuple[float, list[str]]:
    bundle = build_forensic_overlays(image)
    return float(bundle["ela_p"]), list(bundle["notes"])


def edge_noise_score(image: Image.Image) -> tuple[float, list[str]]:
    bundle = build_forensic_overlays(image)
    return float(max(bundle["edge_p"], bundle["noise_p"])), list(bundle["notes"])


def detect_domain_shift(image: Image.Image, has_exif: bool | None = None) -> bool:
    """WhatsApp/social recompression proxy: small dims or missing EXIF."""
    w, h = image.size
    if has_exif is False:
        return True
    if max(w, h) <= 1280 and min(w, h) <= 720:
        return True
    return False


def detect_ai_sparkle_watermark(image: Image.Image) -> dict[str, Any]:
    """High-precision Gemini/Imagen sparkle mark (almost always bottom-right).

    Tuned to avoid false positives on real camera photos (specular highlights,
    UI chrome, fabric texture). Prefer template+geometry over loose bright blobs.
    """
    empty: dict[str, Any] = {"hit": False, "score": 0.0, "corner": None}
    if not _HAS_CV2:
        return empty
    arr = np.asarray(image.convert("RGB"))
    h, w = arr.shape[:2]
    if h < 96 or w < 96:
        return empty

    # Gemini sparkle sits in the outer BR margin — do NOT scan other corners
    # (TR/TL false-fire on real photos with sky/UI chrome).
    mh, mw = max(56, h // 10), max(56, w // 10)
    gray_full = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    crop = gray_full[h - mh : h, w - mw : w]
    ch, cw = crop.shape
    med = float(np.median(crop))

    # Multi-scale 4-point sparkle templates
    best = dict(empty)
    for tw in (15, 21, 29):
        if min(ch, cw) < tw + 4:
            continue
        tmpl = np.zeros((tw, tw), dtype=np.float32)
        c = tw // 2
        thickness = max(1, tw // 15)
        for t in range(tw):
            tmpl[max(0, c - thickness) : c + thickness + 1, t] = 1.0
            tmpl[t, max(0, c - thickness) : c + thickness + 1] = 1.0
        for t in range(tw):
            if abs(t - c) <= c:
                tmpl[t, t] = max(tmpl[t, t], 0.9)
                tmpl[t, tw - 1 - t] = max(tmpl[t, tw - 1 - t], 0.9)
        tmpl = cv2.GaussianBlur(tmpl, (3, 3), 0)
        tmpl_u8 = (tmpl / (tmpl.max() + 1e-6) * 255).astype(np.uint8)
        res = cv2.matchTemplate(crop, tmpl_u8, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)
        mx, my = max_loc
        patch = crop[my : my + tw, mx : mx + tw]
        if patch.size == 0:
            continue
        peak = float(patch.max())
        local_med = float(np.median(patch))
        contrast = peak - med
        # Must be near the outer BR of the *full* image (within ~7% of edges)
        abs_x = (w - mw) + mx + tw / 2
        abs_y = (h - mh) + my + tw / 2
        near_right = abs_x >= w * 0.90
        near_bottom = abs_y >= h * 0.90
        if not (near_right and near_bottom):
            continue
        # Strict gates — real cameras often have bright corner noise
        if max_val < 0.48 or contrast < 30 or (peak - local_med) < 15:
            continue
        # Reject large bright patches (not a tiny icon)
        thr = max(med + 40.0, peak * 0.75)
        _, bw = cv2.threshold(patch, thr, 255, cv2.THRESH_BINARY)
        area = int(np.count_nonzero(bw))
        if area < 8 or area > int(0.45 * tw * tw):
            continue
        tscore = float(0.55 * max_val + 0.45 * min(1.0, contrast / 90.0))
        if tscore > float(best["score"]):
            best = {
                "hit": True,
                "score": min(0.99, tscore),
                "corner": "br",
                "area": area,
                "method": "template",
                "tmpl_val": float(max_val),
                "contrast": float(contrast),
            }

    # Template-only detection. Tip-blob heuristics false-fire on real camera photos.
    return best


def _fuse_aigc_with_watermark(p: float, wm: dict[str, Any]) -> tuple[float, list[Evidence]]:
    """Soft watermark boost — never hard-max to 0.88+ (conflict fusion owns the lock)."""
    from app.engines.media_fusion import soft_watermark_boost

    evidence: list[Evidence] = []
    out, hit, score = soft_watermark_boost(float(p), wm)
    if hit:
        evidence.append(
            Evidence(
                type="forensic",
                value=f"ai_sparkle_watermark corner={wm.get('corner')} score={score:.2f} method={wm.get('method')}",
                signal="ai_platform_watermark",
            )
        )
    return max(0.0, min(0.99, out)), evidence


def _largest_face_crop(image: Image.Image) -> tuple[Image.Image, bool]:
    """Crop largest OpenCV Haar face; else center-square crop. Returns (crop, face_found)."""
    w, h = image.size
    side = min(w, h)
    cx, cy = w // 2, h // 2
    fallback = image.crop((cx - side // 2, cy - side // 2, cx + side // 2, cy + side // 2))
    if not _HAS_CV2 or not hasattr(cv2, "CascadeClassifier"):
        return fallback, False
    try:
        arr = np.array(image)
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        cascade = cv2.CascadeClassifier(cascade_path)
        faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(48, 48))
    except Exception:
        return fallback, False
    if faces is None or len(faces) == 0:
        return fallback, False
    x, y, fw, fh = max(faces, key=lambda f: int(f[2]) * int(f[3]))
    # Expand box slightly for DeepfakeBench-style face crops
    pad = int(0.25 * max(fw, fh))
    x0 = max(0, int(x) - pad)
    y0 = max(0, int(y) - pad)
    x1 = min(w, int(x) + int(fw) + pad)
    y1 = min(h, int(y) + int(fh) + pad)
    return image.crop((x0, y0, x1, y1)), True


def _onnx_p_fake(
    session: Any,
    image: Image.Image,
    size: int = 64,
    *,
    face_crop: bool = False,
) -> tuple[float, dict[str, Any]]:
    """Run NCHW ONNX head.

    - size == 256 (DeepfakeBench Xception): mean/std 0.5; optional face crop
    - size >= 224 (ImageNet-style contracts): ImageNet mean/std
    - smaller (legacy interim nets): plain RGB [0,1]
    """
    meta: dict[str, Any] = {"face_found": False}
    img = image
    if face_crop and size >= 224:
        img, found = _largest_face_crop(image)
        meta["face_found"] = found
    img = img.resize((size, size))
    arr = np.asarray(img, dtype=np.float32) / 255.0
    x = np.transpose(arr, (2, 0, 1))[None, ...]
    if size == 256:
        mean = np.array([0.5, 0.5, 0.5], dtype=np.float32).reshape(1, 3, 1, 1)
        std = np.array([0.5, 0.5, 0.5], dtype=np.float32).reshape(1, 3, 1, 1)
        x = (x - mean) / std
    elif size >= 224:
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32).reshape(1, 3, 1, 1)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32).reshape(1, 3, 1, 1)
        x = (x - mean) / std
    name = session.get_inputs()[0].name
    outs = session.run(None, {name: x})
    return float(np.asarray(outs[0]).ravel()[0]), meta


_clip_bundle: tuple[Any, Any, Any] | None = None  # unused on laptop (Colab-only)


def _clip_vit_l14_feat(image: Image.Image) -> np.ndarray | None:
    """Laptop must NOT load CLIP ViT-L/14 (~900MB). AIGC/UnivFD runs on Colab only.

    See training/colab/12_aigc_univfd_colab.py. Returns None always on API hosts
    unless NIGEHBAN_ALLOW_LOCAL_CLIP=1 is explicitly set (not recommended).
    """
    import os

    if os.environ.get("NIGEHBAN_ALLOW_LOCAL_CLIP", "").strip() not in {"1", "true", "yes"}:
        return None

    global _clip_bundle
    try:
        import open_clip  # type: ignore
        import torch

        if _clip_bundle is None:
            logger.warning("NIGEHBAN_ALLOW_LOCAL_CLIP set — loading ViT-L-14 (heavy)")
            model, _, preprocess = open_clip.create_model_and_transforms(
                "ViT-L-14", pretrained="openai"
            )
            model.eval()
            _clip_bundle = (model, preprocess, "cpu")
        model, preprocess, _device = _clip_bundle
        with torch.no_grad():
            t = preprocess(image).unsqueeze(0)
            feat = model.encode_image(t)
            feat = feat / feat.norm(dim=-1, keepdim=True)
            return feat.cpu().numpy().astype(np.float32)
    except Exception:
        logger.warning("local CLIP load failed", exc_info=True)
        return None


def _run_aigc_sync(image: Image.Image) -> EngineResult:
    """CPU-bound AIGC path — laptop uses slim ONNX only; no CLIP download."""
    # Prefer a full-image ONNX if Colab exported one (rare / large).
    full = load_onnx_session("aigc_univfd.onnx")
    head = load_onnx_session("aigc_univfd_head.onnx")
    if full is not None:
        shape = full.get_inputs()[0].shape
        size = int(shape[-1]) if isinstance(shape[-1], int) and shape[-1] > 0 else 224
        # Full ONNX that expects raw image (not CLIP feats)
        if len(shape) == 4 and (shape[1] == 3 or shape[-1] == 3 or shape[1] == 768):
            if shape[1] == 768 or (len(shape) == 2):
                pass  # feature-input ONNX — needs CLIP; fall through
            else:
                p, _meta = _onnx_p_fake(full, image, size=size, face_crop=False)
                return EngineResult(
                    engine_id="aigc",
                    probability=max(0.0, min(1.0, p)),
                    evidence=[Evidence(type="model", value=f"p_aigc={p:.3f}", signal="onnx_aigc")],
                    features={"backend": "onnx_full_image", "input_size": size},
                    note="Slim full-image AIGC ONNX (no local CLIP)",
                )

    if head is not None:
        feat = _clip_vit_l14_feat(image)
        if feat is None:
            # Still use platform watermark if CLIP blocked on laptop
            wm = detect_ai_sparkle_watermark(image)
            p_wm, wm_ev = _fuse_aigc_with_watermark(0.0, wm)
            if wm.get("hit"):
                return EngineResult(
                    engine_id="aigc",
                    probability=p_wm,
                    evidence=wm_ev,
                    features={"backend": "watermark_only", "watermark": wm},
                    note="Platform AI watermark detected (CLIP not loaded on laptop)",
                )
            return EngineResult(
                engine_id="aigc",
                probability=0.0,
                available=False,
                abstain=True,
                note=(
                    "AIGC/UnivFD requires CLIP ViT-L/14 — runs on Colab only "
                    "(training/colab/15_aigc_strong_remote.py). Laptop will not download huge models. "
                    "Deepfake + ELA still apply; verdict stays inconclusive without AIGC."
                ),
            )
        name = head.get_inputs()[0].name
        p = float(np.asarray(head.run(None, {name: feat})[0]).ravel()[0])
        wm = detect_ai_sparkle_watermark(image)
        p, wm_ev = _fuse_aigc_with_watermark(p, wm)
        return EngineResult(
            engine_id="aigc",
            probability=max(0.0, min(1.0, p)),
            evidence=[
                Evidence(type="model", value=f"p_aigc={p:.3f}", signal="univfd_clip_head"),
                *wm_ev,
            ],
            features={"backend": "univfd_clip_head", "feat_dim": int(feat.shape[-1]), "watermark": wm},
            note="UnivFD linear head on CLIP ViT-L/14 features"
            + (" + platform watermark" if wm.get("hit") else ""),
        )

    return EngineResult(
        engine_id="aigc",
        probability=0.0,
        available=False,
        abstain=True,
        note="engine_offline — no AIGC ONNX; score AI images on Colab (12_aigc_univfd_colab.py)",
    )


def _run_deepfake_sync(image: Image.Image) -> EngineResult:
    session = load_onnx_session("deepfake_xception.onnx")
    if session is None:
        return EngineResult(
            engine_id="deepfake",
            probability=0.0,
            available=False,
            abstain=True,
            note="engine_offline — deepfake_xception.onnx not installed (train/export on Colab)",
        )
    shape = session.get_inputs()[0].shape
    size = int(shape[-1]) if isinstance(shape[-1], int) and shape[-1] > 0 else 256
    use_face = size >= 224
    p, crop_meta = _onnx_p_fake(session, image, size=size, face_crop=use_face)
    return EngineResult(
        engine_id="deepfake",
        probability=max(0.0, min(1.0, p)),
        evidence=[Evidence(type="model", value=f"p_fake={p:.3f}", signal="onnx_deepfake")],
        features={
            "backend": "onnx",
            "input_size": size,
            "preprocess": "deepfakebench_0.5" if size == 256 else "auto",
            "face_crop": use_face,
            "face_found": crop_meta.get("face_found", False),
        },
        note=(
            "DeepfakeBench Xception ONNX — literature DFDC AUC ~0.71; "
            "not a perfect deepfake detector"
        ),
    )


async def run_deepfake_engine(media_url: str) -> EngineResult:
    """ONNX deepfake/manipulation head when artifact present; else offline."""
    if load_onnx_session("deepfake_xception.onnx") is None:
        return EngineResult(
            engine_id="deepfake",
            probability=0.0,
            available=False,
            abstain=True,
            note="engine_offline — deepfake_xception.onnx not installed (train/export on Colab)",
        )
    if not media_url:
        return EngineResult(engine_id="deepfake", probability=0.0, abstain=True, available=False)
    try:
        data = await storage.download_file(media_url)
        image = _load_image(data)
        return await asyncio.to_thread(_run_deepfake_sync, image)
    except Exception as exc:
        return EngineResult(
            engine_id="deepfake",
            probability=0.0,
            available=False,
            abstain=True,
            note=f"deepfake onnx failed: {exc}",
        )


def _fuse_remote_aigc_scores(
    p_remote: float,
    p_zeroshot: float | None,
    p_univfd: float | None,
) -> float:
    """Blend Colab scores without letting CLIP zero-shot alone flag real photos.

    Zero-shot often scores studio camera portraits ~0.7 (false positive). UnivFD
    alone is weak on Gemini. Policy:
    - zs very high (>=0.88) → trust zs
    - zs mid-high AND univfd agrees (>=0.42) → blend
    - otherwise conservative blend capped so zs-only mid scores stay inconclusive
    """
    zs = float(p_zeroshot) if p_zeroshot is not None else None
    univ = float(p_univfd) if p_univfd is not None else None
    if zs is not None and univ is not None:
        if zs >= 0.88:
            return max(0.0, min(0.99, zs))
        if zs >= 0.70 and univ >= 0.42:
            return max(0.0, min(0.99, 0.55 * zs + 0.45 * univ))
        blended = 0.35 * zs + 0.65 * univ
        # Camera FP zone: zs mid, univfd low → keep below lock threshold
        if zs < 0.88 and univ < 0.40:
            blended = min(blended, 0.48)
        return max(0.0, min(0.99, blended))
    if zs is not None:
        return max(0.0, min(0.99, zs * 0.65))
    if univ is not None:
        return max(0.0, min(0.99, univ))
    return max(0.0, min(0.99, float(p_remote)))


async def run_aigc_engine(media_url: str) -> EngineResult:
    """AIGC score via Colab remote (+ laptop watermark). Never load CLIP on laptop."""
    import os

    from app.core.config import settings

    if not media_url:
        return EngineResult(engine_id="aigc", probability=0.0, abstain=True, available=False)

    # Prefer live env (uvicorn --reload children) over stale settings singleton
    remote = (os.environ.get("AIGC_REMOTE_URL") or settings.AIGC_REMOTE_URL or "").strip().rstrip("/")
    data: bytes | None = None
    try:
        data = await storage.download_file(media_url)
    except Exception as exc:
        return EngineResult(
            engine_id="aigc",
            probability=0.0,
            available=False,
            abstain=True,
            note=f"media download failed: {exc}",
        )

    image = _load_image(data)
    wm = detect_ai_sparkle_watermark(image)

    if remote:
        try:
            import httpx

            timeout = float(os.environ.get("AIGC_REMOTE_TIMEOUT") or settings.AIGC_REMOTE_TIMEOUT or 60.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(
                    f"{remote}/score",
                    files={"file": ("image.jpg", data, "application/octet-stream")},
                )
            if resp.status_code != 200:
                # Watermark alone can still lock manipulated
                p_wm, wm_ev = _fuse_aigc_with_watermark(0.0, wm)
                if wm.get("hit"):
                    return EngineResult(
                        engine_id="aigc",
                        probability=p_wm,
                        evidence=wm_ev,
                        features={"backend": "watermark_only", "watermark": wm, "remote_error": resp.status_code},
                        note=f"Platform watermark hit (remote HTTP {resp.status_code})",
                    )
                return EngineResult(
                    engine_id="aigc",
                    probability=0.0,
                    available=False,
                    abstain=True,
                    note=f"AIGC remote HTTP {resp.status_code}: {resp.text[:200]}",
                )
            body = resp.json()
            zs_raw = body.get("p_zeroshot", body.get("p_aidetect"))
            univ_raw = body.get("p_univfd")
            zs = float(zs_raw) if zs_raw is not None else None
            univ = float(univ_raw) if univ_raw is not None else None
            p = _fuse_remote_aigc_scores(float(body.get("p_aigc") or 0.0), zs, univ)
            p_pre_wm = p
            remote_wm = body.get("watermark") if isinstance(body.get("watermark"), dict) else {}
            if remote_wm.get("hit"):
                wm = remote_wm
            p, wm_ev = _fuse_aigc_with_watermark(p, wm)
            feats = {
                "backend": body.get("backend") or "colab_remote",
                "remote": remote,
                "watermark": wm,
                "p_model": p_pre_wm,
                "p_fused_pre_wm": p_pre_wm,
                "p_after_wm": p,
            }
            if zs is not None:
                feats["p_zeroshot"] = zs
                feats["p_aidetect"] = zs
            if univ is not None:
                feats["p_univfd"] = univ
            note_bits = ["Colab CLIP zero-shot + UnivFD (conservative fuse)"]
            if zs is not None:
                note_bits.append(f"zeroshot={zs:.2f}")
            if univ is not None:
                note_bits.append(f"univfd={univ:.2f}")
            note_bits.append(f"fused={p_pre_wm:.2f}")
            note_bits.append(f"p_ai={p:.2f}")
            if wm.get("hit") and float(wm.get("score") or 0) >= 0.55:
                note_bits.append("platform watermark soft-boost")
            return EngineResult(
                engine_id="aigc",
                probability=max(0.0, min(1.0, p)),
                evidence=[
                    Evidence(type="model", value=f"p_aigc={p:.3f}", signal="aigc_ensemble_remote"),
                    *wm_ev,
                ],
                features=feats,
                note=" — ".join(note_bits) + " (not 100% of every generator)",
            )
        except Exception as exc:
            p_wm, wm_ev = _fuse_aigc_with_watermark(0.0, wm)
            if wm.get("hit"):
                return EngineResult(
                    engine_id="aigc",
                    probability=p_wm,
                    evidence=wm_ev,
                    features={"backend": "watermark_only", "watermark": wm, "remote_error": str(exc)[:200]},
                    note="Platform watermark hit (AIGC remote unavailable)",
                )
            return EngineResult(
                engine_id="aigc",
                probability=0.0,
                available=False,
                abstain=True,
                note=f"AIGC remote failed: {exc}",
            )

    # No remote configured — watermark only on laptop (never load CLIP)
    p_wm, wm_ev = _fuse_aigc_with_watermark(0.0, wm)
    if wm.get("hit"):
        return EngineResult(
            engine_id="aigc",
            probability=p_wm,
            evidence=wm_ev,
            features={"backend": "watermark_only", "watermark": wm},
            note="Platform AI watermark detected — set AIGC_REMOTE_URL for full Colab ensemble",
        )
    return EngineResult(
        engine_id="aigc",
        probability=0.0,
        available=False,
        abstain=True,
        note=(
            "engine_offline — set AIGC_REMOTE_URL to Colab tunnel "
            "(training/colab/15_aigc_strong_remote.py). Laptop will not load CLIP."
        ),
    )
