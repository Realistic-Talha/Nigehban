# %% [markdown]
# 09 — Pack FEVER evidence sentences (never use claim as evidence for SUPPORTS/REFUTES)
# Run on Colab with Drive mounted. Downloads wiki-pages JSONL if needed.

# %%
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

DRIVE_ROOT = "/content/drive/MyDrive/Nigehban"
try:
    from google.colab import drive  # type: ignore

    drive.mount("/content/drive")
except Exception:
    pass

ROOT = Path(DRIVE_ROOT) if Path(DRIVE_ROOT).exists() else Path(__file__).resolve().parents[2]
FEVER = ROOT / "datasets" / "fever"
FEVER.mkdir(parents=True, exist_ok=True)
WIKI = FEVER / "wiki-pages"
WIKI.mkdir(parents=True, exist_ok=True)

# Prefer already-cached train/dev
train_path = FEVER / "train.jsonl"
dev_path = FEVER / "paper_dev.jsonl"
for name, url in (
    ("train.jsonl", "https://fever.ai/download/fever/train.jsonl"),
    ("paper_dev.jsonl", "https://fever.ai/download/fever/paper_dev.jsonl"),
):
    dest = FEVER / name
    if not dest.exists() or dest.stat().st_size < 1000:
        print("dl", url)
        dest.write_bytes(urllib.request.urlopen(url, timeout=180).read())

# Wiki pages: FEVER ships wiki-pages.zip on fever.ai
wiki_zip = FEVER / "wiki-pages.zip"
if not any(WIKI.glob("*.jsonl")):
    wiki_url = "https://fever.ai/download/fever/wiki-pages.zip"
    try:
        print("Downloading wiki-pages (large)…", wiki_url)
        data = urllib.request.urlopen(wiki_url, timeout=600).read()
        wiki_zip.write_bytes(data)
        import zipfile

        with zipfile.ZipFile(wiki_zip) as z:
            z.extractall(FEVER)
        print("Extracted wiki into", FEVER)
    except Exception as e:
        print("wiki download failed — will only keep NEI / drop unresolved SUPPORTS/REFUTES:", e)

# Build page_id -> list[sentences]
page_sents: dict[str, list[str]] = {}
for wp in list(WIKI.glob("*.jsonl")) + list(FEVER.glob("wiki-pages/*.jsonl")):
    with open(wp, encoding="utf-8") as f:
        for line in f:
            try:
                obj = json.loads(line)
            except Exception:
                continue
            pid = str(obj.get("id") or obj.get("page_id") or "")
            lines = obj.get("lines") or obj.get("text") or ""
            if isinstance(lines, str):
                # FEVER format: "0\\tsent\\t...\\n1\\tsent"
                sents = []
                for raw in lines.split("\n"):
                    parts = raw.split("\t")
                    if len(parts) >= 2 and parts[0].isdigit():
                        sents.append(parts[1])
                page_sents[pid] = sents
            elif isinstance(lines, list):
                page_sents[pid] = [str(x) for x in lines]
print("wiki pages indexed", len(page_sents))


def resolve_evidence(ex: dict) -> str | None:
    evidence = ex.get("evidence")
    if not isinstance(evidence, list):
        return None
    for group in evidence:
        if not isinstance(group, list):
            continue
        for triple in group:
            # [annotation_id, evidence_id, page_id, sent_id] or nested
            if not isinstance(triple, (list, tuple)) or len(triple) < 4:
                continue
            page_id, sent_id = triple[2], triple[3]
            if page_id is None or sent_id is None:
                continue
            sents = page_sents.get(str(page_id)) or page_sents.get(str(page_id).replace(" ", "_"))
            if not sents:
                continue
            try:
                sid = int(sent_id)
            except Exception:
                continue
            if 0 <= sid < len(sents) and sents[sid].strip():
                return sents[sid].strip()
    return None


LABEL_MAP = {
    "SUPPORTS": ("entailment", 1),
    "REFUTES": ("contradiction", 0),
    "NOT ENOUGH INFO": ("neutral", 2),
}


def pack_split(src: Path, dest: Path, limit: int | None = None) -> dict:
    rows = []
    stats = {"kept": 0, "dropped_no_ev": 0, "nei": 0, "supports": 0, "refutes": 0}
    with open(src, encoding="utf-8") as f:
        for line in f:
            ex = json.loads(line)
            lab = str(ex.get("label") or "").upper().replace("_", " ")
            if "NOT" in lab and "INFO" in lab:
                key = "NOT ENOUGH INFO"
            elif lab.startswith("SUPPORT"):
                key = "SUPPORTS"
            elif lab.startswith("REFUT"):
                key = "REFUTES"
            else:
                continue
            claim = (ex.get("claim") or "").strip()
            if not claim:
                continue
            if key == "NOT ENOUGH INFO":
                # NEI may use empty or claim-only with honest neutral label
                ev = resolve_evidence(ex) or ""
                nli_name, nli_y = LABEL_MAP[key]
                rows.append({"text": claim, "text_pair": ev or claim, "label": nli_y, "fever_label": key})
                stats["nei"] += 1
                stats["kept"] += 1
            else:
                ev = resolve_evidence(ex)
                if not ev:
                    stats["dropped_no_ev"] += 1
                    continue
                if ev.strip() == claim.strip():
                    stats["dropped_no_ev"] += 1
                    continue
                nli_name, nli_y = LABEL_MAP[key]
                rows.append({"text": claim, "text_pair": ev, "label": nli_y, "fever_label": key})
                stats["kept"] += 1
                stats["supports" if key == "SUPPORTS" else "refutes"] += 1
            if limit and stats["kept"] >= limit:
                break
    dest.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + ("\n" if rows else ""), encoding="utf-8")
    stats["out"] = str(dest)
    stats["n"] = len(rows)
    return stats


train_stats = pack_split(train_path, FEVER / "train_packed.jsonl", limit=None)
dev_stats = pack_split(dev_path, FEVER / "paper_dev_packed.jsonl", limit=None)
print(json.dumps({"train": train_stats, "dev": dev_stats}, indent=2))
print("Next: run 03_fact_nli.py against *_packed.jsonl (GPU)")
