# %% [markdown]
# 15 — Strong live AIGC remote (Colab GPU)
# Ensemble: Gemini/AI sparkle watermark + CLIP zero-shot prompts + UnivFD head
# Honest limit: still not 100% of every future generator.
# POST /score → {p_aigc, p_zeroshot, p_univfd, watermark, backend}

# %%
from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

from google.colab import drive

drive.mount("/content/drive", force_remount=False)
ROOT = Path("/content/drive/MyDrive/Nigehban")
ART = ROOT / "artifacts"
URL_FILE = ART / "aigc_remote_url.txt"
ART.mkdir(parents=True, exist_ok=True)

subprocess.check_call(
    [sys.executable, "-m", "pip", "install", "-q", "flask", "open_clip_torch", "onnxruntime", "Pillow", "opencv-python-headless"]
)

import cv2
import numpy as np
import open_clip
import torch
from flask import Flask, jsonify, request
from PIL import Image
import onnxruntime as ort

assert torch.cuda.is_available(), "Need Colab GPU"
device = "cuda"
print("GPU:", torch.cuda.get_device_name(0))

print("Loading CLIP ViT-L/14 …")
clip_model, _, preprocess = open_clip.create_model_and_transforms("ViT-L-14", pretrained="openai")
clip_model = clip_model.to(device).eval()
tokenizer = open_clip.get_tokenizer("ViT-L-14")

AI_PROMPTS = [
    "an AI-generated image",
    "a synthetic computer-generated photo",
    "an image created by an AI image generator like Midjourney Stable Diffusion DALL-E Imagen Gemini",
    "a deepfake or digitally fabricated photograph",
    "CGI render of a person that looks photorealistic but is artificial",
]
REAL_PROMPTS = [
    "a real photograph taken with a camera",
    "an authentic unedited photo of a real person",
    "a genuine camera capture from the real world",
    "a documentary photograph with natural sensor noise",
]

with torch.no_grad():
    ai_tok = tokenizer(AI_PROMPTS).to(device)
    real_tok = tokenizer(REAL_PROMPTS).to(device)
    ai_txt = clip_model.encode_text(ai_tok)
    real_txt = clip_model.encode_text(real_tok)
    ai_txt = ai_txt / ai_txt.norm(dim=-1, keepdim=True)
    real_txt = real_txt / real_txt.norm(dim=-1, keepdim=True)

univfd_path = ART / "aigc_univfd_head.onnx"
sess = None
IN_NAME = None
if univfd_path.exists():
    sess = ort.InferenceSession(str(univfd_path), providers=["CPUExecutionProvider"])
    IN_NAME = sess.get_inputs()[0].name
    print("UnivFD head loaded")
else:
    print("WARN: no UnivFD ONNX — zero-shot + watermark only")

print("CLIP ready")


def detect_ai_sparkle_watermark(img: Image.Image) -> dict:
    """Detect Gemini/Imagen-style 4-point sparkle watermark (usually bottom-right)."""
    arr = np.asarray(img.convert("RGB"))
    h, w = arr.shape[:2]
    # Check all four corners; Gemini usually BR
    corners = {
        "br": arr[h - max(40, h // 10) : h, w - max(40, w // 10) : w],
        "bl": arr[h - max(40, h // 10) : h, 0 : max(40, w // 10)],
        "tr": arr[0 : max(40, h // 10), w - max(40, w // 10) : w],
        "tl": arr[0 : max(40, h // 10), 0 : max(40, w // 10)],
    }
    best = {"hit": False, "score": 0.0, "corner": None}
    for name, crop in corners.items():
        gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
        # Bright icon on darker backdrop
        thr = max(180, int(np.percentile(gray, 92)))
        _, bw = cv2.threshold(gray, thr, 255, cv2.THRESH_BINARY)
        bw = cv2.morphologyEx(bw, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
        n, labels, stats, cents = cv2.connectedComponentsWithStats(bw)
        ch, cw = gray.shape
        for i in range(1, n):
            x, y, ww, hh, area = stats[i]
            if area < 12 or area > (ch * cw) * 0.15:
                continue
            aspect = ww / max(hh, 1)
            if aspect < 0.45 or aspect > 2.2:
                continue
            # Compact star-like: not a long line
            if max(ww, hh) > min(ch, cw) * 0.55:
                continue
            roi = gray[y : y + hh, x : x + ww]
            if roi.size == 0:
                continue
            contrast = float(roi.max() - np.median(gray))
            # Cross / sparkle energy: bright center vs mid-ring
            cy, cx = hh // 2, ww // 2
            pad = max(1, min(ww, hh) // 4)
            center = float(roi[max(0, cy - pad) : cy + pad + 1, max(0, cx - pad) : cx + pad + 1].mean())
            ring = float(roi.mean())
            sparkle = (center - ring) / 255.0
            score = min(1.0, 0.35 * (contrast / 80.0) + 0.65 * max(0.0, sparkle * 4.0))
            if score > best["score"] and contrast > 35 and sparkle > 0.02:
                best = {"hit": True, "score": float(score), "corner": name, "area": int(area)}
    return best


@torch.no_grad()
def score_zeroshot(img: Image.Image) -> float:
    t = preprocess(img).unsqueeze(0).to(device)
    feat = clip_model.encode_image(t)
    feat = feat / feat.norm(dim=-1, keepdim=True)
    ai_sim = (feat @ ai_txt.T).squeeze(0)
    real_sim = (feat @ real_txt.T).squeeze(0)
    # Temperature softmax over mean AI vs mean real
    ai_m = ai_sim.mean()
    real_m = real_sim.mean()
    logits = torch.stack([real_m, ai_m]) * 40.0
    p_ai = float(torch.softmax(logits, dim=0)[1].item())
    return p_ai


@torch.no_grad()
def score_univfd(img: Image.Image) -> float | None:
    if sess is None:
        return None
    t = preprocess(img).unsqueeze(0).to(device)
    feat = clip_model.encode_image(t)
    feat = feat / feat.norm(dim=-1, keepdim=True)
    x = feat.cpu().numpy().astype(np.float32)
    return float(np.asarray(sess.run(None, {IN_NAME: x})[0]).ravel()[0])


def fuse(p_zs: float, p_univ: float | None, wm: dict) -> float:
    parts = [p_zs]
    if p_univ is not None:
        parts.append(p_univ)
    # Soft max bias toward strongest detector (CLIP ZS often beats UnivFD on Gemini)
    base = max(parts)
    # If both agree moderately, nudge up
    if p_univ is not None and min(p_zs, p_univ) >= 0.45:
        base = max(base, 0.5 * (p_zs + p_univ) + 0.15)
    if wm.get("hit") and float(wm.get("score", 0)) >= 0.25:
        base = max(base, 0.93 + 0.05 * float(wm["score"]))
    return float(max(0.0, min(0.99, base)))


def score_bytes(data: bytes) -> dict:
    img = Image.open(io.BytesIO(data)).convert("RGB")
    # Cap huge uploads
    if max(img.size) > 2048:
        img.thumbnail((2048, 2048), Image.Resampling.LANCZOS)
    wm = detect_ai_sparkle_watermark(img)
    p_zs = score_zeroshot(img)
    p_univ = score_univfd(img)
    p = fuse(p_zs, p_univ, wm)
    return {
        "p_aigc": p,
        "p_aidetect": p_zs,
        "p_zeroshot": p_zs,
        "p_univfd": p_univ,
        "watermark": wm,
        "backend": "colab_strong_v2",
    }


app = Flask(__name__)


@app.get("/health")
def health():
    return jsonify(
        {
            "status": "ok",
            "engine": "watermark+clip_zeroshot+univfd",
            "device": torch.cuda.get_device_name(0),
            "honesty": "Cannot guarantee all AI images / future models",
        }
    )


@app.post("/score")
def score():
    f = request.files.get("file") or request.files.get("image")
    if f is None:
        return jsonify({"error": "missing file"}), 400
    return jsonify(score_bytes(f.read()))


def run_flask():
    app.run(host="0.0.0.0", port=8765, threaded=True)


# Kill any previous flask on 8765 if possible
threading.Thread(target=run_flask, daemon=True).start()
time.sleep(2)

# Self-test with a tiny blank (no watermark) just to ensure route works
_blank = Image.new("RGB", (64, 64), (120, 120, 120))
_buf = io.BytesIO()
_blank.save(_buf, format="PNG")
print("selftest_blank", {k: score_bytes(_buf.getvalue()).get(k) for k in ("p_aigc", "p_zeroshot", "p_univfd", "watermark")})

cf = Path("/tmp/cloudflared")
if not cf.exists():
    subprocess.check_call(
        [
            "wget",
            "-q",
            "-O",
            str(cf),
            "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64",
        ]
    )
    cf.chmod(0o755)

# Prefer fresh tunnel
proc = subprocess.Popen(
    [str(cf), "tunnel", "--url", "http://127.0.0.1:8765", "--no-autoupdate"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
)
public = None
deadline = time.time() + 90
while time.time() < deadline:
    line = proc.stdout.readline()
    if not line:
        time.sleep(0.2)
        continue
    print(line.rstrip())
    if "trycloudflare.com" in line:
        for part in line.split():
            if part.startswith("https://") and "trycloudflare.com" in part:
                public = part.rstrip("/").rstrip(".")
                break
    if public:
        break

if not public:
    raise RuntimeError("cloudflared did not print a public URL")

URL_FILE.write_text(public + "\n")
print("AIGC_REMOTE_URL=" + public)
print("Wrote", URL_FILE)
print("Keep this Colab runtime alive while testing media on the laptop.")
