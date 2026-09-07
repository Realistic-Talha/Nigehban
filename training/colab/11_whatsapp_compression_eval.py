# %% [markdown]
# 11 — WhatsApp / social compression stress (Colab)
# Measures score drop on JPEG recompress + downscale; documents domain_shift honesty.

# %%
from __future__ import annotations

import io
import json
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

DRIVE_ROOT = "/content/drive/MyDrive/Nigehban"
try:
    from google.colab import drive  # type: ignore

    drive.mount("/content/drive")
except Exception:
    pass

ROOT = Path(DRIVE_ROOT) if Path(DRIVE_ROOT).exists() else Path(__file__).resolve().parents[2]
ART = ROOT / "artifacts"
OUT = ROOT / "datasets" / "deepfake" / "compression_eval.json"

# Prefer local Drive faces if present; else synthetic proxy (Wikimedia often 403 from Colab).
local_faces = list((ROOT / "datasets" / "deepfake" / "samples").glob("*.jpg")) + list(
    (ROOT / "datasets" / "deepfake" / "samples").glob("*.png")
)
urls = [
    "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1b/Adele_2016.jpg/320px-Adele_2016.jpg",
]


def load_rgb(url: str) -> Image.Image:
    data = urllib.request.urlopen(url, timeout=60).read()
    return Image.open(io.BytesIO(data)).convert("RGB")


def synthetic_face() -> Image.Image:
    rng = np.random.default_rng(0)
    base = Image.fromarray((rng.random((320, 320, 3)) * 180 + 40).astype(np.uint8))
    d = ImageDraw.Draw(base)
    d.ellipse((80, 60, 240, 260), fill=(210, 170, 140))
    return base.convert("RGB")


def recompress(img: Image.Image, max_side: int = 720, quality: int = 40) -> Image.Image:
    w, h = img.size
    scale = max_side / max(w, h)
    if scale < 1:
        img = img.resize((int(w * scale), int(h * scale)))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=quality)
    buf.seek(0)
    return Image.open(buf).convert("RGB")


onnx = ART / "deepfake_xception.onnx"
results = {"onnx_present": onnx.exists(), "samples": []}
if onnx.exists():
    import onnxruntime as ort

    sess = ort.InferenceSession(str(onnx), providers=["CPUExecutionProvider"])

    def score(img: Image.Image) -> float:
        img = img.resize((256, 256))
        x = np.asarray(img, dtype=np.float32) / 255.0
        x = np.transpose(x, (2, 0, 1))[None, ...]
        x = (x - 0.5) / 0.5
        name = sess.get_inputs()[0].name
        return float(np.asarray(sess.run(None, {name: x})[0]).ravel()[0])

    images: list[tuple[str, Image.Image]] = []
    for p in local_faces[:5]:
        images.append((str(p), Image.open(p).convert("RGB")))
    if not images:
        for u in urls:
            try:
                images.append((u, load_rgb(u)))
            except Exception as e:
                results["samples"].append({"url": u, "error": str(e)})
        if not images:
            images.append(("synthetic_face_proxy", synthetic_face()))
            results["method"] = "synthetic_face_proxy_plus_jpeg40_max720"

    for label, raw in images:
        wa = recompress(raw)
        p0, p1 = score(raw), score(wa)
        results["samples"].append({"source": label, "p_raw": p0, "p_whatsappish": p1, "delta": p1 - p0})

results["note"] = (
    "API already sets domain_shift_warning for small dims / missing EXIF. "
    "Expect score drift under heavy JPEG; do not claim DFDC-grade robustness on WhatsApp."
)
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(results, indent=2))
print(json.dumps(results, indent=2))
