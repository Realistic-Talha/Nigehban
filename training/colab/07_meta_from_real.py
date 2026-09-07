# %% [markdown]
# 07 — Meta-learner from REAL engine scores (not Gaussian synthetics)
# Scores messages.csv (+ optional URL rows) through local engines and fits isotonic LR.

# %%
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, roc_auc_score
from sklearn.model_selection import train_test_split

DRIVE_ROOT = "/content/drive/MyDrive/Nigehban"
try:
    from google.colab import drive  # type: ignore

    drive.mount("/content/drive")
except Exception:
    pass

REPO = Path(__file__).resolve().parents[2]
ROOT = Path(DRIVE_ROOT) if Path(DRIVE_ROOT).exists() else REPO
DATA = ROOT / "datasets"
ART = REPO / "apps" / "api" / "models" / "artifacts"
ART.mkdir(parents=True, exist_ok=True)
(DATA / "meta").mkdir(parents=True, exist_ok=True)

# Make API importable
sys.path.insert(0, str(REPO / "apps" / "api"))

from app.engines.rules_pk import run_pk_rules  # noqa: E402
from app.engines.text_scam import run_text_scam_engine  # noqa: E402
from app.engines.url_reputation import extract_url_features, run_url_engine  # noqa: E402

ENGINE_IDS = [
    "url_lgbm",
    "text_scam",
    "rules_pk",
    "fact_nli",
    "deepfake",
    "aigc",
    "provenance",
]


def _vec_from_results(results: list, label: int) -> list:
    by_id = {r.engine_id: r for r in results}
    vec = []
    for i in ENGINE_IDS:
        r = by_id.get(i)
        vec.append(float(r.probability) if r and r.available else 0.0)
        vec.append(0.0 if (not r or r.abstain or not r.available) else 1.0)
    vec.append(int(label))
    return vec


def score_text_row(text: str, label: int) -> list:
    # Extract URLs if any
    import re

    urls = re.findall(r"https?://\S+|www\.\S+", text)
    results = [
        run_url_engine(urls if urls else []),
        run_text_scam_engine(text),
        run_pk_rules(text),
    ]
    # Offline placeholders for engines not applicable on pure text path
    from app.engines.base import EngineResult

    for eid in ("fact_nli", "deepfake", "aigc", "provenance"):
        results.append(
            EngineResult(engine_id=eid, probability=0.0, available=False, abstain=True)
        )
    return _vec_from_results(results, label)


messages = DATA / "pk_scam" / "messages.csv"
if not messages.exists():
    messages = REPO / "datasets" / "pk_scam" / "messages.csv"
if not messages.exists():
    raise SystemExit("messages.csv missing — run 06_ingest_real_text.py")

df = pd.read_csv(messages).dropna(subset=["text", "label"])
# Cap for runtime
if len(df) > 12000:
    df = df.sample(12000, random_state=42)

rows = []
for i, r in df.iterrows():
    try:
        rows.append(score_text_row(str(r["text"]), int(r["label"])))
    except Exception:
        continue
    if len(rows) % 500 == 0:
        print("scored", len(rows))

# Optional: add PhiUSIIL URL-only rows if CSV present
phi = list((DATA / "phiusiil").glob("*.csv")) or list((REPO / "datasets" / "phiusiil").glob("*.csv"))
if not phi:
    # may sit only on Drive from prior Colab download
    pass
else:
    pdf = pd.read_csv(phi[0])
    url_col = next((c for c in ("URL", "url") if c in pdf.columns), None)
    lab_col = next((c for c in ("label", "Label") if c in pdf.columns), None)
    if url_col and lab_col:
        sample = pdf.sample(min(2000, len(pdf)), random_state=42)
        # PhiUSIIL: label 1 = legitimate, 0 = phishing → Nigehban 1 = phishing
        flip = float(pdf[lab_col].mean()) > 0.55
        for _, r in sample.iterrows():
            y_raw = int(r[lab_col])
            y = (1 - y_raw) if flip else y_raw
            try:
                ur = run_url_engine([str(r[url_col])])
                from app.engines.base import EngineResult

                results = [
                    ur,
                    EngineResult(engine_id="text_scam", probability=0.0, available=False, abstain=True),
                    EngineResult(engine_id="rules_pk", probability=0.0, available=False, abstain=True),
                    EngineResult(engine_id="fact_nli", probability=0.0, available=False, abstain=True),
                    EngineResult(engine_id="deepfake", probability=0.0, available=False, abstain=True),
                    EngineResult(engine_id="aigc", probability=0.0, available=False, abstain=True),
                    EngineResult(engine_id="provenance", probability=0.0, available=False, abstain=True),
                ]
                rows.append(_vec_from_results(results, int(y)))
            except Exception:
                continue

cols = []
for eid in ENGINE_IDS:
    cols += [f"{eid}_p", f"{eid}_ok"]
cols.append("label")
outdf = pd.DataFrame(rows, columns=cols)
out_csv = DATA / "meta" / "scam_engine_outcomes.csv"
out_csv.parent.mkdir(parents=True, exist_ok=True)
outdf.to_csv(out_csv, index=False)
# mirror in repo
repo_meta = REPO / "datasets" / "meta"
repo_meta.mkdir(parents=True, exist_ok=True)
outdf.to_csv(repo_meta / "scam_engine_outcomes.csv", index=False)
print("Wrote outcomes", out_csv, outdf.shape)

Xm = outdf.drop(columns=["label"]).to_numpy(dtype=np.float64)
ym = outdf["label"].to_numpy(dtype=int)
Xtr, Xte, ytr, yte = train_test_split(Xm, ym, test_size=0.2, random_state=42, stratify=ym)
meta = CalibratedClassifierCV(LogisticRegression(max_iter=2000), method="isotonic", cv=3)
meta.fit(Xtr, ytr)
mp = meta.predict_proba(Xte)[:, 1]
metrics = {
    "auc": float(roc_auc_score(yte, mp)),
    "f1": float(f1_score(yte, (mp >= 0.5).astype(int))),
    "n_train": int(len(ytr)),
    "n_test": int(len(yte)),
    "gate_auc_ok": float(roc_auc_score(yte, mp)) >= 0.90,
    "production": True,
    "synthetic_scores": False,
    "note": "Calibrated LR on real engine outputs from labeled SMS (+ optional URL sample)",
}
print(json.dumps(metrics, indent=2))
out_path = ART / "meta_scam.joblib"
joblib.dump(meta, out_path)
(ART / "meta_scam.metrics.json").write_text(json.dumps(metrics, indent=2))
(ART / "meta_scam.sha256").write_text(hashlib.sha256(out_path.read_bytes()).hexdigest())
print("Wrote", out_path)
