"""Train a tiny meta_scam.joblib on synthetic engine probability vectors."""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression

ART = Path(__file__).resolve().parents[1] / "models" / "artifacts"
ART.mkdir(parents=True, exist_ok=True)

# Feature layout matches meta._apply_joblib_meta
# [url_p, url_on, text_p, text_on, rules_p, rules_on, fact_p, fact_on, df_p, df_on, aigc_p, aigc_on, prov_p, prov_on]
rng = np.random.default_rng(42)
X, y = [], []
for _ in range(400):
    scam = rng.random() > 0.45
    url = rng.uniform(0.7, 0.98) if scam else rng.uniform(0.0, 0.35)
    text = rng.uniform(0.65, 0.97) if scam else rng.uniform(0.0, 0.4)
    rules = rng.uniform(0.5, 0.95) if scam else rng.uniform(0.0, 0.3)
    vec = [
        url, 1.0, text, 1.0, rules, 1.0,
        0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.2, 0.0,
    ]
    X.append(vec)
    y.append(1 if scam else 0)

X_arr = np.array(X)
y_arr = np.array(y)
clf = LogisticRegression(max_iter=500)
clf.fit(X_arr, y_arr)
joblib.dump(clf, ART / "meta_scam.joblib")
proba = clf.predict_proba(X_arr)[:, 1]
metrics = {"train_acc": float((clf.predict(X_arr) == y_arr).mean()), "note": "synthetic meta bootstrap"}
(ART / "meta_scam.metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
print(json.dumps(metrics, indent=2))
