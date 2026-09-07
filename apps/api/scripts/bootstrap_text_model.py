"""Train interim TF-IDF text scam model from datasets/pk_scam/messages.csv."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

ROOT = Path(__file__).resolve().parents[3]
CSV = ROOT / "datasets" / "pk_scam" / "messages.csv"
ART = Path(__file__).resolve().parents[1] / "models" / "artifacts"
ART.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(CSV)
X = df["text"].astype(str).tolist()
y = df["label"].astype(int).values
# Oversample tiny seed
X = X * 30
y = list(y) * 30

Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
pipe = Pipeline(
    [
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1, max_features=20000)),
        ("clf", LogisticRegression(max_iter=1000, class_weight="balanced")),
    ]
)
pipe.fit(Xtr, ytr)
pred = pipe.predict(Xte)
metrics = {
    "macro_f1": float(f1_score(yte, pred, average="macro")),
    "n_train": len(ytr),
    "note": "seed CSV bootstrap — expand on Drive + Colab",
}
joblib.dump(pipe, ART / "text_scam_tfidf.joblib")
(ART / "text_scam.metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
print(json.dumps(metrics, indent=2))
print("Wrote", ART / "text_scam_tfidf.joblib")
