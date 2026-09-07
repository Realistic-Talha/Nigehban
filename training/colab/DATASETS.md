# Real datasets registry (Synthetic → Real)

Store raw corpora on **Google Drive** (`MyDrive/Nigehban/datasets/`). Do **not** commit PII-rich SMS dumps or FF++/DFDC videos to git. Slim artifacts only under `apps/api/models/artifacts/`.

## Text scam / smishing

| Source | License | Size | Map → `text,label` | Path on Drive |
|--------|---------|------|--------------------|---------------|
| [Zenodo Roman Urdu SMS](https://zenodo.org/records/21810885) DOI [10.5281/zenodo.21810885](https://doi.org/10.5281/zenodo.21810885) | CC-BY-4.0 | 1000 (595/405) | `Raw_text`→text, `Labels`→label | `pk_scam/sources/zenodo_21810885.csv` |
| [IMC25 Smishing](https://github.com/reportsmishing/Smishing-Dataset-IMC25) | see repo | user reports (no label col) | body→text; **train-only unlabeled phish**; exclude from holdout | `pk_scam/sources/imc25_smishing.csv` / `final_dataset_output.csv` |
| [Mendeley financial scams](https://doi.org/10.17632/znsk27yk3h) EN+Bangla | CC-BY-4.0 | form-collected | **OUT OF SCOPE for Nigehban PK** (Bangladesh bKash/Nagad, not JazzCash/Roman Urdu). Do not ingest as primary. | — |
| [UCI SMS Spam](https://archive.ics.uci.edu/dataset/228/sms+spam+collection) | UCI | 5574 EN | sms→text, spam=1 ham=0 | `pk_scam/sources/uci_sms_spam.csv` |

**Unified columns:** `text,label,lang,scam_type,source` with `label` ∈ {0,1}, `1=scam`.

**Zenodo:** use template-aware splits when `Template` / source fields exist — avoid template leakage.

**Citation (Zenodo):** Siddiq, G. (2026). Roman Urdu Phishing SMS Dataset for Smishing Detection Research. Zenodo. https://doi.org/10.5281/zenodo.21810885

## URL

| Source | Notes |
|--------|--------|
| [PhiUSIIL UCI #967](https://archive.ics.uci.edu/dataset/967/phiusiil+phishing+url+dataset) | Already trained; label 1=legit, 0=phish — flip for Nigehban `1=phish` |

## Fact / NLI

| Source | Access |
|--------|--------|
| [FEVER on HF](https://huggingface.co/datasets/fever/fever) | Open; pack wiki sentences via `09_fever_pack_evidence.py` (never claim=ev for SUP/REF) |
| [Fact-Check Insights](https://www.factcheckinsights.org/guide) | Free registration; place CSV under `datasets/factcheck_insights/` then run `10_factcheck_insights_finetune.py` |

## Media

| Source | Access | Drive folder |
|--------|--------|--------------|
| [DeepfakeBench](https://github.com/SCLBD/DeepfakeBench) + FF++/DFDC/Celeb-DF | Form / Kaggle | `deepfake/` |
| [UnivFD / UniversalFakeDetect](https://github.com/WisconsinAIVision/UniversalFakeDetect) | Google Drive (~72GB+) | `aigc/` |

## PII rules

- Anonymize phones/CNICs before sharing outside Drive.
- Never commit `datasets/pk_scam/messages.csv` if it contains user-uploaded PII (repo may keep tiny seeds / Zenodo redistributions that are already published).
- Golden holdouts live in `datasets/golden/` on Drive; a slim copy may live under `apps/api/evals/fixtures/` for CI.
