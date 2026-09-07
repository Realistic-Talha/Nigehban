# %% [markdown]
# 13 — Live AIGC remote server on Colab (CLIP stays on GPU; laptop API calls this URL)
# Exposes POST /score (multipart file=image) → {"p_aigc": float}
# Prints a public Cloudflare quick-tunnel URL — set as AIGC_REMOTE_URL on the laptop.

# %%
from __future__ import annotations

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

subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "flask", "open_clip_torch", "onnxruntime", "Pillow"])

import numpy as np
import open_clip
import torch
from flask import Flask, jsonify, request
from PIL import Image
import onnxruntime as ort
import io

assert torch.cuda.is_available(), "Need Colab GPU"
device = "cuda"
print("Loading CLIP on", torch.cuda.get_device_name(0))
model, _, preprocess = open_clip.create_model_and_transforms("ViT-L-14", pretrained="openai")
model = model.to(device).eval()
sess = ort.InferenceSession(str(ART / "aigc_univfd_head.onnx"), providers=["CPUExecutionProvider"])
IN_NAME = sess.get_inputs()[0].name
print("CLIP + UnivFD head ready")

app = Flask(__name__)


@torch.no_grad()
def score_bytes(data: bytes) -> float:
    img = Image.open(io.BytesIO(data)).convert("RGB")
    t = preprocess(img).unsqueeze(0).to(device)
    feat = model.encode_image(t)
    feat = feat / feat.norm(dim=-1, keepdim=True)
    x = feat.cpu().numpy().astype(np.float32)
    return float(np.asarray(sess.run(None, {IN_NAME: x})[0]).ravel()[0])


@app.get("/health")
def health():
    return jsonify({"status": "ok", "engine": "univfd_colab", "device": torch.cuda.get_device_name(0)})


@app.post("/score")
def score():
    f = request.files.get("file") or request.files.get("image")
    if f is None:
        return jsonify({"error": "missing file"}), 400
    p = score_bytes(f.read())
    return jsonify({"p_aigc": p, "backend": "colab_univfd"})


def run_flask():
    app.run(host="0.0.0.0", port=8765, threaded=True)


threading.Thread(target=run_flask, daemon=True).start()
time.sleep(2)

# Cloudflare quick tunnel (no account)
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

proc = subprocess.Popen(
    [str(cf), "tunnel", "--url", "http://127.0.0.1:8765", "--no-autoupdate"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
)
public = None
deadline = time.time() + 60
while time.time() < deadline:
    line = proc.stdout.readline()
    if not line:
        time.sleep(0.2)
        continue
    print(line.rstrip())
    if "trycloudflare.com" in line or "https://" in line:
        for part in line.split():
            if part.startswith("https://") and "trycloudflare.com" in part:
                public = part.rstrip("/")
                break
    if public:
        break

if not public:
    raise RuntimeError("cloudflared did not print a public URL")

URL_FILE.write_text(public + "\n")
print("AIGC_REMOTE_URL=" + public)
print("Wrote", URL_FILE)
print("Keep this Colab cell/runtime alive while testing media on the laptop.")
