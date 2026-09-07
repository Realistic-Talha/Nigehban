# 04 — Media model export checklist (Colab GPU)

Companion script: `08_media_export_onnx.py`.

## Deepfake (DeepfakeBench Xception) — done path

1. Clone https://github.com/SCLBD/DeepfakeBench on Colab.
2. Download `xception_best.pth` from [releases/v1.0.1](https://github.com/SCLBD/DeepfakeBench/releases/tag/v1.0.1).
3. Export ONNX with DeepfakeBench native preprocess (from `xception.yaml`):
   - face crop **256×256**
   - mean/std **0.5** (not ImageNet)
   - NCHW float32
   - output: `P(fake)` = softmax class 1
4. Save `artifacts/deepfake_xception.onnx` + metrics with **literature DFDC AUC ≈ 0.7077**.
5. API (`media_forensics.py`) applies mean/std 0.5 when ONNX spatial size is 256.

## AIGC (UnivFD)

1. Download UnivFD `fc_weights.pth` (e.g. HF `siddharthksah/deepsafe-weights`).
2. Export **linear head only** → `aigc_univfd_head.onnx` (768 → P(aigc)).
3. Runtime needs CLIP ViT-L/14 (`open_clip_torch` or `transformers`) — full CLIP is too large to embed in laptop ONNX.
4. Do **not** replace with a synthetic texture CNN.

## Honesty

- Cross-domain DFDC AUC for Naive Xception is ~**0.71** — never claim perfect deepfake detection.
- ELA/provenance remain always-on; WhatsApp compression → `domain_shift_warning`.
