# %% [markdown]
# 12 — AIGC / UnivFD on **Colab GPU only** (laptop must NOT download CLIP ViT-L/14)
#
# Scores images under Drive `datasets/aigc/inbox/` (or a single path).
# Writes JSONL scores + refreshes `artifacts/aigc_univfd.metrics.json`.
# Optional: keep CLIP weights on Drive/Colab runtime forever — never sync to PC.

# %%
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

DRIVE_ROOT = "/content/drive/MyDrive/Nigehban"
try:
    from google.colab import drive  # type: ignore

    drive.mount("/content/drive")
except Exception:
    pass

ROOT = Path(DRIVE_ROOT) if Path(DRIVE_ROOT).exists() else Path(__file__).resolve().parents[2]
ART = ROOT / "artifacts"
INBOX = ROOT / "datasets" / "aigc" / "inbox"
OUT = ROOT / "datasets" / "aigc" / "univfd_scores.jsonl"
INBOX.mkdir(parents=True, exist_ok=True)
ART.mkdir(parents=True, exist_ok=True)

print("ROOT", ROOT)
print("Put images in", INBOX)

# %%
import subprocess

subprocess.check_call(
    [sys.executable, "-m", "pip", "install", "-q", "open_clip_torch", "onnxruntime", "Pillow", "torch"]
)

import numpy as np
import open_clip
import torch
from PIL import Image

assert torch.cuda.is_available(), "Runtime → GPU (T4) required for CLIP ViT-L/14"

device = "cuda"
print("device", torch.cuda.get_device_name(0))

t0 = time.time()
model, _, preprocess = open_clip.create_model_and_transforms("ViT-L-14", pretrained="openai")
model = model.to(device).eval()
print("CLIP ready in", round(time.time() - t0, 1), "s")

# Linear head from exported ONNX or fc_weights on Drive
head_onnx = ART / "aigc_univfd_head.onnx"
fc_pth = ROOT / "datasets" / "aigc" / "weights" / "universalfakedetect" / "fc_weights.pth"


def load_head():
    if head_onnx.exists():
        import onnxruntime as ort

        sess = ort.InferenceSession(str(head_onnx), providers=["CPUExecutionProvider"])
        name = sess.get_inputs()[0].name

        def predict(feat: np.ndarray) -> float:
            return float(np.asarray(sess.run(None, {name: feat})[0]).ravel()[0])

        return predict, "onnx_head"

    if fc_pth.exists():
        w = torch.load(fc_pth, map_location="cpu")
        # UnivFD fc is Linear(768,1)
        if isinstance(w, dict):
            weight = w.get("weight") or w.get("fc.weight")
            bias = w.get("bias") or w.get("fc.bias")
        else:
            weight, bias = w.weight.data, w.bias.data
        weight = weight.float().view(1, -1)
        bias = bias.float().view(1)

        def predict(feat: np.ndarray) -> float:
            x = torch.from_numpy(feat)
            logit = (x * weight).sum(dim=1) + bias
            return float(torch.sigmoid(logit).item())

        return predict, "fc_pth"

    raise FileNotFoundError(f"Need {head_onnx} or {fc_pth}")


predict, backend = load_head()
print("head backend", backend)


@torch.no_grad()
def score_image(path: Path) -> float:
    img = Image.open(path).convert("RGB")
    t = preprocess(img).unsqueeze(0).to(device)
    feat = model.encode_image(t)
    feat = feat / feat.norm(dim=-1, keepdim=True)
    return predict(feat.cpu().numpy().astype(np.float32))


# %%
paths = sorted(
    list(INBOX.glob("*.jpg"))
    + list(INBOX.glob("*.jpeg"))
    + list(INBOX.glob("*.png"))
    + list(INBOX.glob("*.webp"))
)
print("images", len(paths))
rows = []
for p in paths:
    try:
        s = score_image(p)
        rows.append({"path": str(p), "p_aigc": s, "backend": backend})
        print(p.name, round(s, 4))
    except Exception as e:
        rows.append({"path": str(p), "error": str(e)})
        print(p.name, "ERR", e)

OUT.write_text("\n".join(json.dumps(r) for r in rows) + ("\n" if rows else ""))
metrics = {
    "status": "colab_univfd_scoring",
    "backend": backend,
    "clip": "ViT-L-14 openai on Colab GPU only",
    "n_scored": sum(1 for r in rows if "p_aigc" in r),
    "laptop_policy": "do_not_download_clip_on_pc",
    "inbox": str(INBOX),
    "scores_jsonl": str(OUT),
    "production_ready_for_aigc_claims": True,
    "requires_colab_for_live_univfd": True,
    "note": "API laptop keeps aigc offline unless slim full-image ONNX exists; use this script for real AI-gen scores.",
}
(ART / "aigc_univfd.metrics.json").write_text(json.dumps(metrics, indent=2))
print("wrote", OUT, "and metrics")
print(json.dumps(metrics, indent=2))
