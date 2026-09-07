# Nigehban Detection Methodology

## What we are

A **calibrated multi-engine detector** for Pakistan-facing scam, fact, and media checks.  
Verdict authority is the **meta-learner**, not an LLM. Groq/Ollama only write bilingual explanations of locked evidence.

## Engines

| Engine | Method | Artifact |
|--------|--------|----------|
| `url_lgbm` | Lexical URL features + LightGBM on [PhiUSIIL](https://archive.ics.uci.edu/dataset/967/phiusiil+phishing+url+dataset) | `url_lgbm.joblib` |
| `text_scam` | PK rules + TF-IDF/LR on Zenodo + UCI; IMC25 unlabeled reports are **train-only** (excluded from holdout) | `text_scam_tfidf.joblib` |
| `rules_pk` | Deterministic EN/Urdu/Roman Urdu red flags | code |
| `fact_nli` | DeBERTa NLI; MNLI-packed pairs + capped FEVER NEI (no claim=ev for SUP/REF); NEI when retrieval empty | Drive `fact_nli/model` or HF auto-download |
| `forensics_ela` | ELA + noise heuristics | code |
| `deepfake` | [DeepfakeBench](https://github.com/SCLBD/DeepfakeBench) Xception ONNX; OpenCV face-crop before 256 | `deepfake_xception.onnx` (256, mean/std 0.5) |
| `forensics_ela` | ELA + residual noise + edge anomaly + CFA maps (overlay PNGs) | code + stored overlays |
| `metadata` | EXIF / IPTC / ICC / C2PA presence | `exifread` + Pillow |
| `aigc` | Colab ensemble: CLIP zero-shot + UnivFD + **soft** platform watermark boost (`AIGC_REMOTE_URL`). Laptop never loads CLIP. | `15_aigc_strong_remote.py` |
| `provenance` | pHash Hamming near-dupe | DB |
| `media_fusion` | Three-axis lock: `P_ai`, `P_edit`, `S_cam` — conflict → inconclusive | `app/engines/media_fusion.py` |

## Media fusion (three-axis)

Mediacheck **does not** take `max(engine)` or hard-lock on watermark alone.

| Axis | Meaning |
|------|---------|
| `P_ai` | AI-generation likelihood (conservative CLIP zs + UnivFD fuse; watermark adds `0.18 × score`, never `max(p, 0.88)`) |
| `P_edit` | Classical forensics (ELA / residual noise / edge / CFA) |
| `S_cam` | Camera authenticity prior from hardware EXIF (make+model+datetime) |

**Decision (priority order):**

1. `S_cam ≥ 0.70` and (`P_ai ≥ 0.55` or watermark) → **`inconclusive`** (conflict escalate; confidence &lt; 55)
2. `S_cam ≥ 0.55`, `P_ai ≤ 0.45`, `P_edit ≥ 0.48` → **`likely_edited`** (human capture + post-edit; **not AI**)
3. `S_cam ≥ 0.70`, `P_edit < 0.42`, `P_ai ≤ 0.45` (or AIGC offline) → **`likely_authentic`**
4. `P_ai ≥ 0.70` and `S_cam < 0.45` → **`likely_manipulated`** (AI-generated)
5. Watermark + `S_cam < 0.45` → **`likely_manipulated`**
6. Else soft band → **`inconclusive`**

`P_edit` is raised by EXIF editor tags (Lightroom/Photoshop/…) and forensic edit notes (e.g. inconsistent color-channel noise) — not crushed by low ELA alone. Editor tags must **not** be labeled “generative” (that previously falsely zeroed `S_cam`).

Display confidence is calibrated from axis agreement, not a raw model probability. UI shows axes, decision rule, confidence breakdown, and overlays.

**Research basis:** Fontani et al. Dempster–Shafer forensic fusion (IEEE TIFS); AIFo / AgentFoX / FRAME multi-path evidence; “Don’t Guess, Escalate” uncertainty-aware abstention; EXIF integrity as authenticity prior; separate **editing** vs **synthesis** hypotheses.

Unit tests: `apps/api/tests/test_media_fusion.py`.

## Data citations (text)

- Zenodo Roman Urdu smishing: [10.5281/zenodo.21810885](https://zenodo.org/records/21810885)
- IMC 2025 Smishing: [reportsmishing/Smishing-Dataset-IMC25](https://github.com/reportsmishing/Smishing-Dataset-IMC25)
- UCI SMS Spam Collection (EN auxiliary)
- Meta-learner: isotonic LR on **real engine score vectors** (not Gaussian synthetics)

## Honesty limits

- DeepfakeBench Naive Xception **cross-domain DFDC AUC ≈ 0.71** (literature table). We do not advertise “detects all deepfakes.”
- UnivFD alone is weak on some modern gens (e.g. Gemini/Imagen). Live AIGC uses a **Colab ensemble** (CLIP zero-shot AI prompts + UnivFD + soft Gemini-style sparkle watermark) via `AIGC_REMOTE_URL`. Watermark is a **soft boost** into `P_ai`; strong camera EXIF conflicting with high AIGC locks **inconclusive**, not 90%+ manipulated. **No detector can guarantee every future AI image.** Keep Colab runtime alive while testing.
- IMC25 Smishing CSV has **no label column** — treated as unlabeled phishing reports for train only; holdout is Zenodo+UCI labeled rows.
- Full FEVER wiki-pages zip is too large for a single Colab session; production NLI uses **real MNLI premise–hypothesis** plus capped FEVER NEI — never `evidence = claim` for SUPPORTS/REFUTES.
- Fact-Check Insights mix-in ready (`training/colab/10_factcheck_insights_finetune.py`) — waits on CSV under Drive `datasets/factcheck_insights/`.
- Mendeley financial-scam corpus is **out of scope** (Bangladesh bKash/Nagad, not PK).
- Fact-check fusion: ClaimReview ratings **or** web fact-check headline consensus
  (`falsely claims`, `does not show`, `debunked`, …) → conclusive **`false` / `misleading` / `true`**.
  Abstain **`unverified`** only when both ClaimReview and web dispute are inconclusive (NLI NEI).
  Scam `meta_scam.joblib` is **not** applied on the factcheck path.
- WhatsApp recompression triggers `domain_shift_warning`; see compression eval script `11_whatsapp_compression_eval.py`.

## Training

Heavy work: Google Colab + Drive (`training/colab/`).  
Laptop: copy slim artifacts → `apps/api/models/artifacts/` → ONNX Runtime / joblib inference.

## Metrics & gates

Colab writes `*.metrics.json` (`synthetic_templates` / `synthetic_scores` must be false for text/meta).  
Local CI: `pytest apps/api/evals/test_gates.py`.

### Bundle status (2026-08-29 quality gaps)

| Artifact | Status | Notes |
|----------|--------|-------|
| `url_lgbm.joblib` | Real | PhiUSIIL |
| `text_scam_tfidf.joblib` | Real | macro-F1≈0.947, AUC≈0.989; IMC unlabeled excluded from holdout; sklearn 1.6.1 |
| `meta_scam.joblib` | Real | AUC≈0.999; `synthetic_scores: false`; sklearn 1.6.1 |
| `fact_nli/model` | MNLI-packed + FEVER NEI on Drive | eval macro-F1≈0.89; HF fallback on laptop until full model copy |
| `deepfake_xception.onnx` | DeepfakeBench Xception | face-crop in API; DFDC AUC lit. 0.7077 |
| `aigc_univfd_head.onnx` | UnivFD head only | CLIP on **Colab**; laptop AIGC offline by policy |
