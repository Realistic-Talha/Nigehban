# %% [markdown]
# 03 — FEVER fine-tune for fact NLI (Colab GPU)
# Prefers packed pairs from 09_fever_pack_evidence.py (claim≠evidence).
# Fact-Check Insights: see 10_factcheck_insights_finetune.py after registration.

# %%
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np

DRIVE_ROOT = "/content/drive/MyDrive/Nigehban"
try:
    from google.colab import drive  # type: ignore

    drive.mount("/content/drive")
except Exception:
    pass

REPO = Path(__file__).resolve().parents[2]
ROOT = Path(DRIVE_ROOT) if Path(DRIVE_ROOT).exists() else REPO
FEVER_DIR = ROOT / "datasets" / "fever"
DRIVE_ART = ROOT / "artifacts" / "fact_nli" / "model"
FEVER_DIR.mkdir(parents=True, exist_ok=True)
DRIVE_ART.mkdir(parents=True, exist_ok=True)

subprocess.check_call(
    [
        sys.executable,
        "-m",
        "pip",
        "install",
        "-q",
        "transformers",
        "datasets",
        "accelerate",
        "scikit-learn",
        "sentencepiece",
    ]
)

import torch
from datasets import Dataset
from sklearn.metrics import accuracy_score, f1_score
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    Trainer,
    TrainingArguments,
)

assert torch.cuda.is_available(), "Switch Colab Runtime → GPU (T4)"

BASE = "cross-encoder/nli-deberta-v3-xsmall"
MAX_SAMPLES = 12000
MAX_EVAL = 1500
EPOCHS = 1
LR = 2e-5

packed_train = FEVER_DIR / "train_packed.jsonl"
packed_dev = FEVER_DIR / "paper_dev_packed.jsonl"
if not packed_train.exists():
    raise SystemExit("Run 09_fever_pack_evidence.py first to create train_packed.jsonl")


def load_packed(path: Path, limit: int) -> Dataset:
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            rows.append(json.loads(line))
            if len(rows) >= limit:
                break
    return Dataset.from_list(rows)


train_ds = load_packed(packed_train, MAX_SAMPLES)
eval_ds = load_packed(packed_dev if packed_dev.exists() else packed_train, MAX_EVAL)
print("splits", len(train_ds), len(eval_ds))

tok = AutoTokenizer.from_pretrained(BASE)
model = AutoModelForSequenceClassification.from_pretrained(BASE)
print("labels", [model.config.id2label[i] for i in range(model.config.num_labels)])


def tokenize(batch):
    return tok(
        batch["text"],
        batch["text_pair"],
        truncation=True,
        max_length=192,
        padding="max_length",
    )


train_tok = train_ds.map(tokenize, batched=True)
eval_tok = eval_ds.map(tokenize, batched=True)
cols = ["input_ids", "attention_mask", "label"]
if "token_type_ids" in train_tok.column_names:
    cols.insert(2, "token_type_ids")
train_tok = train_tok.remove_columns([c for c in train_tok.column_names if c not in cols])
eval_tok = eval_tok.remove_columns([c for c in eval_tok.column_names if c not in cols])


def compute_metrics(eval_pred):
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=-1)
    return {
        "accuracy": float(accuracy_score(labels, preds)),
        "macro_f1": float(f1_score(labels, preds, average="macro")),
    }


args = TrainingArguments(
    output_dir=str(FEVER_DIR / "trainer_out_packed"),
    per_device_train_batch_size=16,
    per_device_eval_batch_size=32,
    num_train_epochs=EPOCHS,
    learning_rate=LR,
    eval_strategy="epoch",
    save_strategy="no",
    logging_steps=50,
    report_to=[],
    fp16=True,
)
trainer = Trainer(
    model=model,
    args=args,
    train_dataset=train_tok,
    eval_dataset=eval_tok,
    compute_metrics=compute_metrics,
)
trainer.train()
metrics = trainer.evaluate()
print("eval", metrics)
model.save_pretrained(DRIVE_ART)
tok.save_pretrained(DRIVE_ART)
macro = float(metrics.get("eval_macro_f1", 0))
summary = {
    "status": "fever_packed_finetuned",
    "base_model": BASE,
    "n_train": len(train_ds),
    "n_eval": len(eval_ds),
    "eval": {k: float(v) for k, v in metrics.items() if isinstance(v, (int, float))},
    "production": macro >= 0.55,
    "synthetic": False,
    "trained_on": "colab_gpu",
    "evidence": "wiki_packed_no_claim_eq_ev",
    "device": torch.cuda.get_device_name(0),
}
(DRIVE_ART.parent / "fact_nli.metrics.json").write_text(json.dumps(summary, indent=2))
print(json.dumps(summary, indent=2))
print("Saved", DRIVE_ART)
