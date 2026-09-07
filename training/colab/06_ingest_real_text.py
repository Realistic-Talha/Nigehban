# %% [markdown]
# 06 — Ingest real smishing/SMS corpora → messages.csv + golden holdout
# Run on Colab (Drive mounted) or locally with DRIVE_ROOT pointing at a local mirror.

# %%
from __future__ import annotations

import io
import re
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

DRIVE_ROOT = "/content/drive/MyDrive/Nigehban"
try:
    from google.colab import drive  # type: ignore

    drive.mount("/content/drive")
except Exception:
    # Local Nigehban repo mirror
    repo = Path(__file__).resolve().parents[2]
    local_mirror = repo / "nigehban_drive"
    if (repo / "datasets" / "pk_scam").exists():
        DRIVE_ROOT = str(repo)
    elif local_mirror.exists():
        DRIVE_ROOT = str(local_mirror)
    else:
        DRIVE_ROOT = str(repo)

ROOT = Path(DRIVE_ROOT)
DATA = ROOT / "datasets" / "pk_scam"
SRC = DATA / "sources"
GOLDEN = ROOT / "datasets" / "golden"
for p in (DATA, SRC, GOLDEN):
    p.mkdir(parents=True, exist_ok=True)


def _norm_label(v) -> int | None:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    s = str(v).strip().lower()
    if s in {"1", "scam", "spam", "phishing", "smishing", "fraud", "true", "yes"}:
        return 1
    if s in {"0", "ham", "legit", "legitimate", "benign", "ok", "false", "no"}:
        return 0
    try:
        i = int(float(s))
        return 1 if i == 1 else 0 if i == 0 else None
    except Exception:
        return None


def _frame(text, label, lang, scam_type, source) -> dict | None:
    lab = _norm_label(label)
    t = str(text or "").strip()
    if lab is None or not t:
        return None
    return {
        "text": t,
        "label": lab,
        "lang": lang,
        "scam_type": scam_type or "",
        "source": source,
    }


rows: list[dict] = []

# --- Zenodo Roman Urdu (local xlsx/csv preferred) ---
zenodo_candidates = [
    SRC / "zenodo_21810885.csv",
    DATA / "roman_urdu_smishing_1000.csv",
    DATA / "phishing_dataset_1000.xlsx",
    Path(__file__).resolve().parents[2] / "datasets" / "pk_scam" / "roman_urdu_smishing_1000.csv",
    Path(__file__).resolve().parents[2] / "datasets" / "pk_scam" / "phishing_dataset_1000.xlsx",
]
for zpath in zenodo_candidates:
    if not zpath.exists():
        continue
    if zpath.suffix.lower() in {".xlsx", ".xls"}:
        zdf = pd.read_excel(zpath)
    else:
        zdf = pd.read_csv(zpath)
    text_col = next((c for c in ("Raw_text", "text", "Normalized_text") if c in zdf.columns), None)
    lab_col = next((c for c in ("Labels", "label") if c in zdf.columns), None)
    if not text_col or not lab_col:
        continue
    for _, r in zdf.iterrows():
        rec = _frame(
            r[text_col],
            r[lab_col],
            "roman_urdu",
            str(r.get("Source_Type", r.get("scam_type", ""))),
            "zenodo_21810885",
        )
        if rec:
            rows.append(rec)
    out_src = SRC / "zenodo_21810885.csv"
    pd.DataFrame(rows[-len(zdf) :]).to_csv(out_src, index=False) if False else None
    # write cleaned source copy
    cleaned = [x for x in rows if x["source"] == "zenodo_21810885"]
    pd.DataFrame(cleaned).drop_duplicates("text").to_csv(SRC / "zenodo_21810885.csv", index=False)
    print("Zenodo rows", len(cleaned), "from", zpath)
    break
else:
    print("Zenodo file not found — skip")

# --- IMC25 smishing from GitHub ---
# Unlabeled report rows are train-only phishing; holdout excludes them so metrics stay honest.
imc_url = (
    "https://raw.githubusercontent.com/reportsmishing/Smishing-Dataset-IMC25/"
    "main/dataset/final_dataset_output.csv"
)
imc_unlabeled_train_only: list[dict] = []
try:
    raw = urllib.request.urlopen(imc_url, timeout=120).read()
    imc = pd.read_csv(io.BytesIO(raw))
    imc.to_csv(SRC / "imc25_smishing_raw.csv", index=False)
    print("IMC25 columns", list(imc.columns))
    text_col = next(
        (
            c
            for c in imc.columns
            if c.lower() in {"text", "message", "sms", "body", "content", "sms_text", "translation"}
        ),
        None,
    )
    if text_col is None:
        str_cols = [c for c in imc.columns if imc[c].dtype == object]
        text_col = max(str_cols, key=lambda c: imc[c].astype(str).str.len().mean()) if str_cols else None
    lab_col = next(
        (
            c
            for c in imc.columns
            if c.lower()
            in {
                "label",
                "labels",
                "is_smishing",
                "smishing",
                "phishing",
                "class",
                "category",
                "verdict",
                "is_phishing",
            }
        ),
        None,
    )
    n_labeled = 0
    n_unlabeled = 0
    for _, r in imc.iterrows():
        t = str(r.get(text_col) or "").strip()
        if not t or text_col is None:
            # try translation fallback
            t = str(r.get("translation") or r.get("text") or "").strip()
        if not t:
            continue
        if lab_col is not None and _norm_label(r[lab_col]) is not None:
            rec = _frame(t, r[lab_col], str(r.get("language") or "mixed"), "imc25", "imc25_smishing")
            if rec:
                rows.append(rec)
                n_labeled += 1
        else:
            # User-reported smishing corpus without labels → train-only positive (not in holdout)
            rec = {
                "text": t,
                "label": 1,
                "lang": str(r.get("language") or "mixed"),
                "scam_type": "imc25",
                "source": "imc25_smishing_unlabeled",
                "holdout_eligible": False,
            }
            imc_unlabeled_train_only.append(rec)
            n_unlabeled += 1
    print("IMC25 labeled", n_labeled, "unlabeled_train_only", n_unlabeled, "lab_col", lab_col)
except Exception as e:
    print("IMC25 download failed:", e)

# --- Mendeley financial scams: OUT OF SCOPE (Bangladesh, not Pakistan) ---
print(
    "Skipping Mendeley financial scams (DOI 10.17632/znsk27yk3h) — Bangladesh bKash/Nagad, "
    "not JazzCash/Roman Urdu PK. See DATASETS.md."
)

# --- UCI / HF SMS spam ---
try:
    sms_url = (
        "https://raw.githubusercontent.com/mohitgupta-omg/Kaggle-SMS-Spam-Collection-Dataset-/"
        "master/spam.csv"
    )
    raw = urllib.request.urlopen(sms_url, timeout=60).read()
    sms = pd.read_csv(io.BytesIO(raw), encoding="latin-1")
    v1, v2 = ("v1", "v2") if "v1" in sms.columns else (sms.columns[0], sms.columns[1])
    n_before = len(rows)
    for _, r in sms.iterrows():
        lab = 1 if str(r[v1]).lower().startswith("spam") else 0
        rec = _frame(r[v2], lab, "en", "sms_spam", "uci_sms_spam")
        if rec:
            rows.append(rec)
    sms_out = pd.DataFrame([x for x in rows if x["source"] == "uci_sms_spam"])
    sms_out.to_csv(SRC / "uci_sms_spam.csv", index=False)
    print("UCI SMS added", len(rows) - n_before)
except Exception as e:
    print("UCI SMS failed:", e)

# --- Seed messages in repo (tiny) ---
seed = Path(__file__).resolve().parents[2] / "datasets" / "pk_scam" / "messages.csv"
if seed.exists():
    sdf = pd.read_csv(seed)
    for _, r in sdf.iterrows():
        if "zenodo" in str(r.get("source", "")).lower():
            continue
        # skip if this is already a merged file from a previous run with many sources
        rec = _frame(r.get("text"), r.get("label"), r.get("lang", "mixed"), r.get("scam_type", "seed"), "repo_seed")
        if rec and len(str(rec["text"])) > 5:
            rows.append(rec)

df = pd.DataFrame(rows).dropna(subset=["text", "label"])
df["label"] = df["label"].astype(int)
df = df.drop_duplicates(subset=["text"]).reset_index(drop=True)
print("Labeled unique", df.shape, "pos_rate", float(df["label"].mean()))
print(df["source"].value_counts().to_dict())

# Holdout only from sources with real labels (exclude IMC unlabeled train-only)
from sklearn.model_selection import train_test_split

holdout_pool = df[df["source"] != "imc25_smishing_unlabeled"].copy()
if holdout_pool["label"].nunique() > 1 and len(holdout_pool) >= 50:
    train_labeled, hold_df = train_test_split(
        holdout_pool, test_size=0.15, random_state=42, stratify=holdout_pool["label"]
    )
else:
    train_labeled, hold_df = train_test_split(holdout_pool, test_size=0.15, random_state=42)

unlab_df = pd.DataFrame(imc_unlabeled_train_only)
if len(unlab_df):
    unlab_df = unlab_df.drop_duplicates(subset=["text"])
    # drop texts already in holdout
    hold_texts = set(hold_df["text"].astype(str))
    unlab_df = unlab_df[~unlab_df["text"].astype(str).isin(hold_texts)]
    train_df = pd.concat([train_labeled, unlab_df.drop(columns=["holdout_eligible"], errors="ignore")], ignore_index=True)
else:
    train_df = train_labeled

train_df = train_df.drop_duplicates(subset=["text"]).reset_index(drop=True)
print(
    "Train",
    train_df.shape,
    "pos_rate",
    float(train_df["label"].mean()),
    "Holdout",
    hold_df.shape,
    "holdout_pos",
    float(hold_df["label"].mean()),
)

messages_path = DATA / "messages.csv"
hold_path = GOLDEN / "text_scam_holdout.csv"
train_df.to_csv(messages_path, index=False)
hold_df.to_csv(hold_path, index=False)
# Also mirror under repo datasets when running locally from repo
repo_data = Path(__file__).resolve().parents[2] / "datasets" / "pk_scam"
repo_golden = Path(__file__).resolve().parents[2] / "datasets" / "golden"
if repo_data != DATA:
    repo_data.mkdir(parents=True, exist_ok=True)
    repo_golden.mkdir(parents=True, exist_ok=True)
    train_df.to_csv(repo_data / "messages.csv", index=False)
    hold_df.to_csv(repo_golden / "text_scam_holdout.csv", index=False)

print("Wrote", messages_path, "n=", len(train_df))
print("Wrote", hold_path, "n=", len(hold_df))
print("synthetic_templates=false — real sources only in this merge")
print("imc_unlabeled_excluded_from_holdout=true")
