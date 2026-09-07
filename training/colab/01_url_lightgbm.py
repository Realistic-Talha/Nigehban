# %% [markdown]
# 01 — URL LightGBM on PhiUSIIL (Colab)
#
# 1. Runtime → GPU optional (CPU fine for LightGBM)
# 2. Mount Drive, set DRIVE_ROOT
# 3. Download PhiUSIIL CSV into datasets/phiusiil/
# 4. Run this script; copy artifacts to the API machine

# %%
DRIVE_ROOT = "/content/drive/MyDrive/Nigehban"  # change if needed
import os
from pathlib import Path

try:
    from google.colab import drive  # type: ignore

    drive.mount("/content/drive")
except Exception:
    print("Not on Colab — using local DRIVE_ROOT or ./nigehban_drive")
    if not Path(DRIVE_ROOT).exists():
        DRIVE_ROOT = str(Path("./nigehban_drive").resolve())

ROOT = Path(DRIVE_ROOT)
DATA = ROOT / "datasets" / "phiusiil"
ART = ROOT / "artifacts"
DATA.mkdir(parents=True, exist_ok=True)
ART.mkdir(parents=True, exist_ok=True)

# %%
# pip installs (Colab)
import subprocess
import sys

subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "lightgbm", "scikit-learn", "pandas", "joblib", "tldextract"])

# %%
import hashlib
import json
import re
from urllib.parse import urlparse

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import f1_score, roc_auc_score
from sklearn.model_selection import train_test_split

FEATURE_NAMES = [
    "url_length", "host_length", "path_length", "num_digits", "num_dots",
    "num_hyphens", "num_at", "num_slash", "num_question", "num_equals",
    "num_percent", "has_ip", "has_https", "subdomain_depth", "has_punycode",
    "suspicious_tld", "brand_in_host", "brand_in_path", "brand_typosquat",
    "entropy", "digit_ratio", "uppercase_ratio", "has_shortener",
    "query_length", "max_label_len",
]

PK_BRANDS = ["jazzcash", "easypaisa", "sbp", "fia", "nadra", "bisp", "hbl", "meezan"]
_BAD_TLDS = {".xyz", ".tk", ".ml", ".ga", ".cf", ".gq", ".buzz", ".top", ".click"}
_SHORTENERS = {"bit.ly", "tinyurl.com", "t.co", "goo.gl", "is.gd"}


def entropy(s: str) -> float:
    from collections import Counter
    import math

    if not s:
        return 0.0
    c = Counter(s)
    n = len(s)
    return -sum((v / n) * math.log2(v / n) for v in c.values())


def levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def extract_url_features(url: str) -> dict:
    raw = url if str(url).startswith("http") else "http://" + str(url)
    parsed = urlparse(raw)
    host = (parsed.hostname or "").lower()
    path = parsed.path or ""
    query = parsed.query or ""
    full = raw.lower()
    labels = [x for x in host.split(".") if x]
    host_core = labels[-2] if len(labels) >= 2 else host
    typosquat = 0.0
    for b in PK_BRANDS:
        if host_core != b and 0 < levenshtein(host_core, b) <= 2 and len(b) >= 4:
            typosquat = 1.0
            break
    tld = "." + labels[-1] if labels else ""
    digits = sum(ch.isdigit() for ch in full)
    return {
        "url_length": float(len(raw)),
        "host_length": float(len(host)),
        "path_length": float(len(path)),
        "num_digits": float(digits),
        "num_dots": float(raw.count(".")),
        "num_hyphens": float(raw.count("-")),
        "num_at": float(raw.count("@")),
        "num_slash": float(raw.count("/")),
        "num_question": float(raw.count("?")),
        "num_equals": float(raw.count("=")),
        "num_percent": float(raw.count("%")),
        "has_ip": 1.0 if re.fullmatch(r"\d{1,3}(?:\.\d{1,3}){3}", host or "") else 0.0,
        "has_https": 1.0 if parsed.scheme == "https" else 0.0,
        "subdomain_depth": float(max(0, len(labels) - 2)),
        "has_punycode": 1.0 if "xn--" in host else 0.0,
        "suspicious_tld": 1.0 if tld in _BAD_TLDS else 0.0,
        "brand_in_host": 1.0 if any(b in host for b in PK_BRANDS) else 0.0,
        "brand_in_path": 1.0 if any(b in path.lower() for b in PK_BRANDS) else 0.0,
        "brand_typosquat": typosquat,
        "entropy": entropy(host),
        "digit_ratio": digits / max(1, len(full)),
        "uppercase_ratio": sum(ch.isupper() for ch in str(url)) / max(1, len(str(url))),
        "has_shortener": 1.0 if host in _SHORTENERS else 0.0,
        "query_length": float(len(query)),
        "max_label_len": float(max((len(x) for x in labels), default=0)),
    }


# %%
# Expect a CSV with columns URL + label (0 legit / 1 phish) OR PhiUSIIL feature table.
# If only features exist, train on those columns that intersect FEATURE_NAMES.

candidates = list(DATA.glob("*.csv"))
if not candidates:
    raise SystemExit(f"Place PhiUSIIL CSV under {DATA}")

df = pd.read_csv(candidates[0])
print("Loaded", candidates[0], "shape", df.shape)

label_col = None
for c in ("label", "Label", "CLASS_LABEL", "Result", "phishing"):
    if c in df.columns:
        label_col = c
        break
if label_col is None:
    raise SystemExit(f"No label column in {list(df.columns)[:20]}")

url_col = None
for c in ("URL", "url", "Url"):
    if c in df.columns:
        url_col = c
        break

y = df[label_col].astype(int).values
# PhiUSIIL labels sometimes use 1=legit — flip if mean > 0.6 and docs say so
if y.mean() > 0.55:
    print("Warning: label mean high — verify 1=phishing convention; not auto-flipping")

if url_col:
    # subsample for Colab RAM if huge
    if len(df) > 80000:
        df = df.sample(80000, random_state=42)
        y = df[label_col].astype(int).values
    X = np.array([list(extract_url_features(u).values()) for u in df[url_col].astype(str)])
    # ensure order
    X = np.array([[extract_url_features(u)[n] for n in FEATURE_NAMES] for u in df[url_col].astype(str)])
else:
    # use numeric intersection
    cols = [c for c in FEATURE_NAMES if c in df.columns]
    if len(cols) < 10:
        raise SystemExit("Need URL column or overlapping feature names")
    X = df[cols].fillna(0).to_numpy(dtype=np.float64)
    FEATURE_NAMES = cols  # type: ignore

Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
model = lgb.LGBMClassifier(n_estimators=120, max_depth=8, learning_rate=0.05, random_state=42)
model.fit(Xtr, ytr)
proba = model.predict_proba(Xte)[:, 1]
pred = (proba >= 0.5).astype(int)
auc = float(roc_auc_score(yte, proba))
f1 = float(f1_score(yte, pred))

# FPR at 95% recall
order = np.argsort(-proba)
yt_sorted = yte[order]
pr_sorted = proba[order]
target_rec = 0.95
tp = 0
fp = 0
P = max(1, int((yte == 1).sum()))
N = max(1, int((yte == 0).sum()))
fpr_at_95 = None
for yt in yt_sorted:
    if yt == 1:
        tp += 1
    else:
        fp += 1
    if tp / P >= target_rec:
        fpr_at_95 = fp / N
        break

metrics = {
    "auc": auc,
    "f1": f1,
    "fpr_at_95_recall": fpr_at_95,
    "n_train": int(len(ytr)),
    "n_test": int(len(yte)),
    "gate_auc_ok": auc >= 0.97,
    "gate_fpr_ok": fpr_at_95 is not None and fpr_at_95 <= 0.05,
    "feature_names": list(FEATURE_NAMES),
}
print(json.dumps(metrics, indent=2))

out_path = ART / "url_lgbm.joblib"
joblib.dump(model, out_path)
metrics_path = ART / "url_lgbm.metrics.json"
metrics_path.write_text(json.dumps(metrics, indent=2))
digest = hashlib.sha256(out_path.read_bytes()).hexdigest()
(ART / "url_lgbm.sha256").write_text(digest)
print("Wrote", out_path, "sha256", digest)
print("Copy these files to apps/api/models/artifacts/ on your PC")
