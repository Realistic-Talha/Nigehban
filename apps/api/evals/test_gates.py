"""Detection Kernel eval smoke gates (local). Full AUC gates run on Colab."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.engines.meta import lock_verdict
from app.engines.rules_pk import run_pk_rules
from app.engines.text_scam import run_text_scam_engine
from app.engines.url_reputation import run_url_engine


FIXTURES = Path(__file__).parent / "fixtures"
ART = ROOT / "models" / "artifacts"


def test_url_engine_flags_ip_host():
    r = run_url_engine(["http://192.168.0.5/jazzcash-otp"])
    assert r.engine_id == "url_lgbm"
    assert r.probability >= 0.2


def test_url_allowlist_sbp_low():
    r = run_url_engine(["https://www.sbp.org.pk/press/"])
    assert r.probability <= 0.15


def test_text_otp_scam_high():
    r = run_text_scam_engine(
        "URGENT JazzCash: send OTP to 03001234567 or account blocked"
    )
    assert r.probability >= 0.45


def test_text_benign_lower():
    r = run_text_scam_engine("See you at dinner tomorrow in Lahore.")
    assert r.probability < 0.55 or r.abstain


def test_meta_locks_scam_without_llm():
    results = [
        run_url_engine(["http://jazzcash-secure.xyz/otp"]),
        run_text_scam_engine("Send OTP now jazzcash"),
        run_pk_rules("Send OTP now jazzcash FIA"),
    ]
    locked = lock_verdict("scamcheck", results)
    assert locked.verdict in ("likely_scam", "needs_caution")
    assert locked.confidence > 0
    assert locked.engines


def test_fact_nei_empty_claim():
    import asyncio
    from app.engines.fact_nli import run_fact_nli_engine

    r = asyncio.run(run_fact_nli_engine(""))
    assert r.abstain
    assert r.features.get("nli_label") == "NEI"


def test_golden_scam_fixture_file_exists():
    path = FIXTURES / "scam_golden.jsonl"
    assert path.exists()
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) >= 30


def test_pk_golden_text_engine_separation():
    path = FIXTURES / "scam_golden.jsonl"
    rows = [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    fails = []
    scam_ps: list[float] = []
    benign_ps: list[float] = []
    for row in rows:
        r = run_text_scam_engine(row["text"])
        p = float(r.probability)
        if int(row.get("label", -1)) == 1:
            scam_ps.append(p)
        elif int(row.get("label", -1)) == 0:
            benign_ps.append(p)
        if "expect_min_p" in row and p < float(row["expect_min_p"]) and not r.abstain:
            fails.append((row["id"], "min", p, row["expect_min_p"]))
        if "expect_max_p" in row and p > float(row["expect_max_p"]):
            fails.append((row["id"], "max", p, row["expect_max_p"]))
    # Allow a few edge cases; require majority pass + mean separation
    assert len(fails) <= max(3, len(rows) // 8), f"too many golden fails: {fails[:8]}"
    assert scam_ps and benign_ps
    assert (sum(scam_ps) / len(scam_ps)) - (sum(benign_ps) / len(benign_ps)) >= 0.2


def test_face_crop_helper_smoke():
    from PIL import Image

    from app.engines.media_forensics import _largest_face_crop

    img = Image.new("RGB", (400, 400), color=(180, 140, 120))
    crop, found = _largest_face_crop(img)
    assert crop.size[0] > 0 and crop.size[1] > 0
    assert found is False  # blank image — center crop fallback


def test_meta_logging_appends_jsonl(tmp_path):
    from app.engines.base import EngineResult, LockedVerdict
    from app.engines.meta_logging import log_engine_outcome

    log = tmp_path / "meta.jsonl"
    results = [
        EngineResult(engine_id="url_lgbm", probability=0.9, available=True),
        EngineResult(engine_id="text_scam", probability=0.8, available=True),
        EngineResult(engine_id="rules_pk", probability=0.7, available=True, abstain=False),
    ]
    locked = LockedVerdict(
        verdict="likely_scam",
        confidence=90.0,
        abstain=False,
        engines=[],
        evidence=[],
        ece_bucket="well_calibrated",
        path="scamcheck",
    )
    log_engine_outcome(
        check_id="test-1",
        path="scamcheck",
        results=results,
        locked=locked,
        text_preview="otp jazzcash",
        log_path=log,
    )
    assert log.exists()
    row = json.loads(log.read_text(encoding="utf-8").strip().splitlines()[-1])
    assert row["check_id"] == "test-1"
    assert len(row["vector"]) == 14


def test_text_metrics_not_synthetic_and_gates():
    path = ART / "text_scam.metrics.json"
    assert path.exists(), "text_scam.metrics.json missing — copy from Colab Drive"
    m = json.loads(path.read_text(encoding="utf-8"))
    assert m.get("synthetic_templates") is False
    assert float(m.get("macro_f1", 0)) >= 0.85
    assert float(m.get("auc", 0)) >= 0.95
    assert m.get("gate_f1_ok") is True
    assert m.get("gate_auc_ok") is True


def test_meta_metrics_not_synthetic():
    path = ART / "meta_scam.metrics.json"
    assert path.exists(), "meta_scam.metrics.json missing — copy from Colab Drive"
    m = json.loads(path.read_text(encoding="utf-8"))
    assert m.get("synthetic_scores") is False
    assert float(m.get("auc", 0)) >= 0.90


def test_deepfake_metrics_honest_dfdc():
    path = ART / "deepfake_xception.metrics.json"
    assert path.exists()
    m = json.loads(path.read_text(encoding="utf-8"))
    assert m.get("synthetic") is False
    dfdc = float(m.get("dfdc_auc") or m.get("expected_dfdc_auc_literature") or 0)
    assert 0.65 <= dfdc <= 0.85, "DFDC AUC must stay honest (~0.71), not 0.99 marketing"
    assert (ART / "deepfake_xception.onnx").exists()


def test_aigc_univfd_head_or_metrics():
    metrics = ART / "aigc_univfd.metrics.json"
    assert metrics.exists()
    m = json.loads(metrics.read_text(encoding="utf-8"))
    assert m.get("synthetic") is False
    head = ART / "aigc_univfd_head.onnx"
    assert head.exists() or m.get("status") == "awaiting_univfd_weights"


def test_golden_holdout_csv_optional_gates():
    """If Colab holdout was copied locally, spot-check text engine separation."""
    holdout = Path(__file__).resolve().parents[3] / "datasets" / "golden" / "text_scam_holdout.csv"
    if not holdout.exists():
        pytest.skip("golden holdout not on laptop")
    import pandas as pd

    df = pd.read_csv(holdout).dropna(subset=["text", "label"])
    df = df.sample(n=min(40, len(df)), random_state=0)
    scores = []
    for _, row in df.iterrows():
        r = run_text_scam_engine(str(row["text"]))
        scores.append((int(row["label"]), float(r.probability)))
    pos = [p for y, p in scores if y == 1]
    neg = [p for y, p in scores if y == 0]
    if pos and neg:
        assert sum(pos) / len(pos) > sum(neg) / len(neg)
