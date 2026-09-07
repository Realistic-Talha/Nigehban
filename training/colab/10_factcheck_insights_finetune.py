# %% [markdown]
# 10 — Fact-Check Insights mix-in (run when CSV arrives under datasets/factcheck_insights/)
# Maps ClaimReview-style ratings → NLI pairs; mixes with FEVER packed pairs; GPU fine-tune.

# %%
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

DRIVE_ROOT = "/content/drive/MyDrive/Nigehban"
try:
    from google.colab import drive  # type: ignore

    drive.mount("/content/drive")
except Exception:
    pass

ROOT = Path(DRIVE_ROOT) if Path(DRIVE_ROOT).exists() else Path(__file__).resolve().parents[2]
FCI = ROOT / "datasets" / "factcheck_insights"
FEVER = ROOT / "datasets" / "fever"
ART = ROOT / "artifacts" / "fact_nli" / "model"
FCI.mkdir(parents=True, exist_ok=True)

csvs = list(FCI.glob("*.csv")) + list(FCI.glob("*.jsonl"))
if not csvs:
    print(
        "No Fact-Check Insights files yet. After approval, place CSV/JSONL under:\n",
        FCI,
        "\nThen re-run this script on Colab GPU.",
    )
    raise SystemExit(0)

subprocess.check_call(
    [sys.executable, "-m", "pip", "install", "-q", "transformers", "datasets", "accelerate", "scikit-learn", "pandas"]
)
import pandas as pd
import torch
from datasets import Dataset
from sklearn.metrics import accuracy_score, f1_score
from transformers import AutoModelForSequenceClassification, AutoTokenizer, Trainer, TrainingArguments
import numpy as np

assert torch.cuda.is_available(), "Use Colab Runtime → GPU"

# Rating → NLI label (contradiction=0, entailment=1, neutral=2) matching DeBERTa NLI
RATING_MAP = {
    "false": 0,
    "mostly false": 0,
    "pants on fire": 0,
    "incorrect": 0,
    "true": 1,
    "mostly true": 1,
    "correct": 1,
    "mixture": 2,
    "half-true": 2,
    "unproven": 2,
    "unverifiable": 2,
    "opinion": 2,
    "not enough info": 2,
}


def load_fci_pairs(limit: int = 8000) -> list[dict]:
    rows = []
    for path in csvs:
        if path.suffix.lower() == ".csv":
            df = pd.read_csv(path)
        else:
            df = pd.read_json(path, lines=True)
        claim_col = next((c for c in df.columns if c.lower() in {"claim", "claimreviewed", "text", "headline"}), None)
        rate_col = next(
            (c for c in df.columns if c.lower() in {"rating", "reviewrating", "textualrating", "label"}),
            None,
        )
        body_col = next(
            (c for c in df.columns if c.lower() in {"text", "body", "article", "claimreview", "evidence"}),
            None,
        )
        if not claim_col or not rate_col:
            print("skip columns", path.name, list(df.columns)[:12])
            continue
        for _, r in df.iterrows():
            claim = str(r[claim_col] or "").strip()
            rating = str(r[rate_col] or "").strip().lower()
            ev = str(r[body_col] or "").strip() if body_col else ""
            if not claim:
                continue
            y = None
            for k, v in RATING_MAP.items():
                if k in rating:
                    y = v
                    break
            if y is None:
                continue
            if not ev:
                ev = claim if y == 2 else ""
            if y != 2 and (not ev or ev == claim):
                continue
            rows.append({"text": claim, "text_pair": ev or claim, "label": y})
            if len(rows) >= limit:
                return rows
    return rows


fci_rows = load_fci_pairs()
print("FCI pairs", len(fci_rows))
fever_packed = FEVER / "train_packed.jsonl"
fever_rows = []
if fever_packed.exists():
    with open(fever_packed, encoding="utf-8") as f:
        for i, line in enumerate(f):
            fever_rows.append(json.loads(line))
            if i >= 12000:
                break
print("FEVER packed", len(fever_rows))

# 70/30 mix
n_fci = min(len(fci_rows), max(1, int(0.3 * (len(fever_rows) + len(fci_rows)))))
mix = fever_rows[: max(0, 12000 - n_fci)] + fci_rows[:n_fci]
print("mix", len(mix), "fci_in_mix", n_fci)

BASE = "cross-encoder/nli-deberta-v3-xsmall"
tok = AutoTokenizer.from_pretrained(BASE)
# Prefer continuing from previous FEVER-tuned weights if present
start = ART if (ART / "config.json").exists() else BASE
model = AutoModelForSequenceClassification.from_pretrained(start)

ds = Dataset.from_list(mix)


def tokenize(batch):
    return tok(batch["text"], batch["text_pair"], truncation=True, max_length=192, padding="max_length")


ds = ds.map(tokenize, batched=True)
cols = ["input_ids", "attention_mask", "label"]
if "token_type_ids" in ds.column_names:
    cols.insert(2, "token_type_ids")
ds = ds.remove_columns([c for c in ds.column_names if c not in cols])
split = ds.train_test_split(test_size=0.1, seed=42)


def compute_metrics(eval_pred):
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=-1)
    return {
        "accuracy": float(accuracy_score(labels, preds)),
        "macro_f1": float(f1_score(labels, preds, average="macro")),
    }


args = TrainingArguments(
    output_dir=str(FEVER / "fci_trainer_out"),
    per_device_train_batch_size=16,
    per_device_eval_batch_size=32,
    num_train_epochs=1,
    learning_rate=2e-5,
    eval_strategy="epoch",
    save_strategy="no",
    fp16=True,
    report_to=[],
)
trainer = Trainer(
    model=model,
    args=args,
    train_dataset=split["train"],
    eval_dataset=split["test"],
    compute_metrics=compute_metrics,
)
trainer.train()
metrics = trainer.evaluate()
ART.mkdir(parents=True, exist_ok=True)
model.save_pretrained(ART)
tok.save_pretrained(ART)
summary = {
    "status": "fever_plus_factcheck_insights",
    "factcheck_insights": True,
    "n_fci": n_fci,
    "n_fever": len(mix) - n_fci,
    "eval": {k: float(v) for k, v in metrics.items() if isinstance(v, (int, float))},
    "production": float(metrics.get("eval_macro_f1", 0)) >= 0.55,
    "synthetic": False,
    "trained_on": "colab_gpu",
}
(ART.parent / "fact_nli.metrics.json").write_text(json.dumps(summary, indent=2))
print(json.dumps(summary, indent=2))
