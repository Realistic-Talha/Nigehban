# %% [markdown]
# 02 — Pakistan scam text classifier on REAL corpora only
# Requires: 06_ingest_real_text.py → datasets/pk_scam/messages.csv

# %%
DRIVE_ROOT = "/content/drive/MyDrive/Nigehban"
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys

try:
    from google.colab import drive  # type: ignore

    drive.mount("/content/drive")
except Exception:
    repo = Path(__file__).resolve().parents[2]
    DRIVE_ROOT = str(repo if (repo / "datasets" / "pk_scam" / "messages.csv").exists() else repo)

ROOT = Path(DRIVE_ROOT)
DATA = ROOT / "datasets" / "pk_scam"
GOLDEN = ROOT / "datasets" / "golden"
ART = ROOT / "artifacts"
# Prefer API artifacts dir when running inside monorepo
api_art = Path(__file__).resolve().parents[2] / "apps" / "api" / "models" / "artifacts"
if api_art.parent.exists():
    ART = api_art
DATA.mkdir(parents=True, exist_ok=True)
ART.mkdir(parents=True, exist_ok=True)
GOLDEN.mkdir(parents=True, exist_ok=True)

subprocess.check_call(
    [sys.executable, "-m", "pip", "install", "-q", "scikit-learn", "pandas", "joblib", "lightgbm"]
)

# %%
import lightgbm as lgb
import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, f1_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

csv_path = DATA / "messages.csv"
hold_path = GOLDEN / "text_scam_holdout.csv"
if not csv_path.exists():
    raise SystemExit(f"Missing {csv_path} — run 06_ingest_real_text.py first")

df = pd.read_csv(csv_path).dropna(subset=["text", "label"])
# Reject pure synthetic template dumps if flagged
if "source" in df.columns:
    synth = df["source"].astype(str).str.contains("synth|template_gen", case=False, na=False)
    if synth.any():
        print("Dropping synthetic-flagged rows", int(synth.sum()))
        df = df.loc[~synth]

X = df["text"].astype(str).tolist()
y = df["label"].astype(int).values
sources = sorted(df["source"].dropna().unique().tolist()) if "source" in df.columns else []

if hold_path.exists():
    hold = pd.read_csv(hold_path).dropna(subset=["text", "label"])
    Xte = hold["text"].astype(str).tolist()
    yte = hold["label"].astype(int).values
    Xtr, ytr = X, y
else:
    Xtr, Xte, ytr, yte = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y if len(set(y)) > 1 else None
    )

pipe = Pipeline(
    [
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_features=80000, sublinear_tf=True)),
        ("clf", LogisticRegression(max_iter=2000, class_weight="balanced", C=2.0)),
    ]
)
pipe.fit(Xtr, ytr)
proba = pipe.predict_proba(Xte)[:, 1]
pred = (proba >= 0.5).astype(int)
macro_f1 = float(f1_score(yte, pred, average="macro"))
auc = float(roc_auc_score(yte, proba)) if len(set(yte)) > 1 else None
metrics = {
    "macro_f1": macro_f1,
    "auc": auc,
    "n_train": int(len(ytr)),
    "n_test": int(len(yte)),
    "gate_f1_ok": macro_f1 >= 0.85,
    "gate_auc_ok": (auc or 0) >= 0.95,
    "production": True,
    "synthetic_templates": False,
    "data_sources": sources,
    "backend": "tfidf_lr",
    "report": classification_report(yte, pred, output_dict=True),
}
print(json.dumps({k: metrics[k] for k in metrics if k != "report"}, indent=2))
if not metrics["gate_f1_ok"] or not metrics["gate_auc_ok"]:
    print("WARNING: holdout gates failed — still exporting for inspection")

out = ART / "text_scam_tfidf.joblib"
joblib.dump(pipe, out)
(ART / "text_scam.metrics.json").write_text(json.dumps(metrics, indent=2))
(ART / "text_scam.sha256").write_text(hashlib.sha256(out.read_bytes()).hexdigest())
print("Wrote", out)


def feats(text: str) -> list[float]:
    t = text.lower()
    toks = re.findall(r"\w+", t)
    return [
        float(len(text)),
        float(len(toks)),
        float(pipe.predict_proba([text])[0][1]),
        float(sum(k in t for k in ("otp", "cnic", "urgent", "jazzcash", "fia"))),
        1.0 if "otp" in t else 0.0,
        1.0 if re.search(r"03\d{9}", t.replace(" ", "")) else 0.0,
    ]


idx = np.random.choice(len(Xtr), size=min(8000, len(Xtr)), replace=False)
Xf = np.array([feats(Xtr[i]) for i in idx])
yf = np.array([ytr[i] for i in idx])
lgbm = lgb.LGBMClassifier(n_estimators=80, max_depth=5, learning_rate=0.05, random_state=42)
lgbm.fit(Xf, yf)
joblib.dump(lgbm, ART / "text_scam_lgbm_head.joblib")
print("Wrote text_scam_lgbm_head.joblib")
