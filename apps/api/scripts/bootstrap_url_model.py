"""Bootstrap a tiny URL LightGBM (or sklearn) model for local smoke tests.

For production metrics, run training/colab/01_url_lightgbm.py on Colab with PhiUSIIL.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.engines.url_reputation import FEATURE_NAMES, extract_url_features  # noqa: E402

ART = ROOT / "models" / "artifacts"
ART.mkdir(parents=True, exist_ok=True)

# Synthetic labeled URLs (bootstrap only — not a substitute for PhiUSIIL)
SAMPLES: list[tuple[str, int]] = [
    ("https://www.sbp.org.pk/press/", 0),
    ("https://jazzcash.com.pk/login", 0),
    ("https://easypaisa.com.pk/", 0),
    ("https://nadra.gov.pk/", 0),
    ("https://dawn.com/", 0),
    ("http://192.168.1.1/jazzcash-login", 1),
    ("http://jazzcash-secure.xyz/otp", 1),
    ("http://bit.ly/easypaisa-verify", 1),
    ("http://www.jazzcaslh.com/login", 1),
    ("http://secure-nadra.tk/cnic", 1),
    ("https://fia-gov.pk-alert.buzz/pay", 1),
    ("http://login-jazzcash.com.evil.test/otp", 1),
    ("https://google.com/", 0),
    ("https://facebook.com/", 0),
    ("http://tinyurl.com/sbp-fine-pay", 1),
]


def main() -> None:
    X, y = [], []
    for url, label in SAMPLES * 20:  # oversample for stable trees
        feats = extract_url_features(url)
        X.append([feats[n] for n in FEATURE_NAMES])
        y.append(label)
    X_arr = np.array(X, dtype=np.float64)
    y_arr = np.array(y, dtype=np.int32)

    try:
        import lightgbm as lgb
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import roc_auc_score, f1_score

        Xtr, Xte, ytr, yte = train_test_split(X_arr, y_arr, test_size=0.25, random_state=42, stratify=y_arr)
        model = lgb.LGBMClassifier(
            n_estimators=60,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.9,
            colsample_bytree=0.9,
            random_state=42,
        )
        model.fit(Xtr, ytr)
        proba = model.predict_proba(Xte)[:, 1]
        pred = (proba >= 0.5).astype(int)
        metrics = {
            "backend": "lightgbm",
            "auc": float(roc_auc_score(yte, proba)),
            "f1": float(f1_score(yte, pred)),
            "n_train": int(len(ytr)),
            "note": "BOOTSTRAP synthetic URLs — replace via Colab PhiUSIIL notebook",
            "feature_names": FEATURE_NAMES,
        }
    except Exception as exc:
        from sklearn.linear_model import LogisticRegression
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import roc_auc_score, f1_score

        Xtr, Xte, ytr, yte = train_test_split(X_arr, y_arr, test_size=0.25, random_state=42, stratify=y_arr)
        model = LogisticRegression(max_iter=500)
        model.fit(Xtr, ytr)
        proba = model.predict_proba(Xte)[:, 1]
        pred = (proba >= 0.5).astype(int)
        metrics = {
            "backend": "sklearn_logreg",
            "auc": float(roc_auc_score(yte, proba)),
            "f1": float(f1_score(yte, pred)),
            "n_train": int(len(ytr)),
            "fallback_reason": str(exc),
            "note": "BOOTSTRAP — install lightgbm for preferred artifact",
            "feature_names": FEATURE_NAMES,
        }

    import joblib

    out = ART / "url_lgbm.joblib"
    joblib.dump({"model": model, "feature_names": FEATURE_NAMES}, out)
    # Also dump bare model for engines expecting estimator with predict_proba
    joblib.dump(model, ART / "url_lgbm_model_only.joblib")
    # Prefer unified load: wrap
    joblib.dump(model, out)

    (ART / "url_lgbm.metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print("Wrote", out)
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
