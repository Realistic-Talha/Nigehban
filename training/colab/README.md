# Colab-first training

Heavy datasets and GPU training live on **Google Drive + Colab**. The API laptop only receives slim artifacts under `apps/api/models/artifacts/`.

See [DATASETS.md](DATASETS.md) for real corpus registry (Zenodo, IMC25, PhiUSIIL, FEVER, DeepfakeBench, UnivFD).

## Drive layout

```
MyDrive/Nigehban/
  datasets/
    pk_scam/
      sources/           # per-corpus cleaned CSVs
      messages.csv       # merged train (real sources only)
    phiusiil/            # UCI PhiUSIIL CSV
    fever/               # FEVER / HF cache
    factcheck_insights/  # after registration
    deepfake/            # DeepfakeBench / FF++ / DFDC
    aigc/                # UnivFD train/test
    golden/              # held-out never-train sets
      text_scam_holdout.csv
    meta/
      scam_engine_outcomes.csv
  artifacts/             # exported ONNX + joblib + metrics + sha256
  notebooks/
```

## How to run

1. Open Google Colab → GPU when training NLI/media
2. Mount Drive
3. Run scripts in order (or paste cells)
4. Set `DRIVE_ROOT = "/content/drive/MyDrive/Nigehban"`
5. Copy `artifacts/*` into local `apps/api/models/artifacts/`
6. Update `manifest.json` sha256 fields

## Scripts

| File | Produces |
|------|----------|
| `06_ingest_real_text.py` | `pk_scam/messages.csv` + `golden/text_scam_holdout.csv` |
| `01_url_lightgbm.py` | `url_lgbm.joblib` (PhiUSIIL) |
| `02_text_scam.py` | `text_scam_tfidf.joblib` on **real** merged CSV |
| `07_meta_from_real.py` | `meta_scam.joblib` from scored real texts |
| `03_fact_nli.py` | FEVER fine-tune → `artifacts/fact_nli/model` |
| `04_media_export.md` / `08_media_export_onnx.py` | DeepfakeBench / UnivFD ONNX |
| `05_production_train_all.py` | legacy bundle — prefer phased scripts above |

**Do not** use synthetic PK templates as the primary text training corpus.
