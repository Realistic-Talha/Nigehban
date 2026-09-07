"""Isotonic / logistic meta-learner — sole verdict authority."""

from __future__ import annotations

from typing import Any

from app.engines.artifacts import load_joblib
from app.engines.base import EngineResult, LockedVerdict
from app.engines.media_fusion import build_analytics_payload, compute_axes, decide_media_verdict

# Path-specific label maps
_SCAM_LABELS = [
    (0.75, "likely_scam"),
    (0.45, "needs_caution"),
    (0.0, "likely_safe"),
]
_FACT_LABELS = [
    (0.70, "false"),  # high P(false/misleading) — mapped below more carefully
]
_MEDIA_LABELS = [
    (0.70, "likely_manipulated"),
    (0.45, "inconclusive"),
    (0.0, "likely_authentic"),
]


def _fuse_probability(results: list[EngineResult]) -> tuple[float, float, bool]:
    """Return fused_p, evidence_mass, should_abstain."""
    usable = [r for r in results if r.available and not (r.abstain and r.probability < 0.15)]
    if not usable:
        return 0.0, 0.0, True

    # Weighted mean: prefer models with evidence
    weights = []
    vals = []
    for r in usable:
        w = 1.0 + 0.35 * len(r.evidence)
        if r.features.get("backend") in ("onnx", "joblib"):
            w += 0.5
        weights.append(w)
        vals.append(r.probability)
    fused = sum(v * w for v, w in zip(vals, weights)) / sum(weights)
    mass = sum(len(r.evidence) for r in usable) + sum(
        1 for r in usable if r.features.get("backend") in ("onnx", "joblib")
    )
    abstain = mass < 1 and fused < 0.55
    return float(fused), float(mass), abstain


def _apply_joblib_meta(results: list[EngineResult]) -> float | None:
    model = load_joblib("meta_scam.joblib")
    if model is None:
        return None
    import numpy as np

    # Fixed order feature vector
    ids = ["url_lgbm", "text_scam", "rules_pk", "fact_nli", "deepfake", "aigc", "provenance"]
    by_id = {r.engine_id: r for r in results}
    vec = []
    for i in ids:
        r = by_id.get(i)
        vec.append(r.probability if r and r.available else 0.0)
        vec.append(0.0 if not r or r.abstain else 1.0)
    X = np.array([vec], dtype=np.float64)
    if hasattr(model, "predict_proba"):
        return float(model.predict_proba(X)[0][1])
    return float(model.predict(X)[0])


def lock_verdict(
    path: str,
    results: list[EngineResult],
    *,
    domain_shift_warning: bool = False,
) -> LockedVerdict:
    # Scam meta calibrator is wrong-domain for fact/media — only apply on scamcheck.
    meta_p = _apply_joblib_meta(results) if path == "scamcheck" else None
    fused, mass, abstain_flag = _fuse_probability(results)
    p = meta_p if meta_p is not None else fused

    # Guard: Colab meta on real outcomes can under-score URL-absent OTP / wallet scams.
    # Keep meta primary, but never lock "safe" against strong text + money_otp evidence.
    if path == "scamcheck":
        text = next((r for r in results if r.engine_id == "text_scam"), None)
        if text and text.available and not text.abstain and text.probability >= 0.7:
            otpish = any(getattr(e, "signal", "") == "money_otp_request" for e in text.evidence)
            if otpish:
                p = max(float(p), float(fused), float(text.probability) * 0.85)

    evidence: list[dict[str, Any]] = []
    for r in results:
        evidence.extend(e.to_dict() for e in r.evidence)

    engines = [r.to_dict() for r in results]

    if path == "scamcheck":
        if abstain_flag or (mass < 1 and p < 0.5):
            verdict, conf, abstain = "needs_caution", min(49.0, p * 100), True
        elif p >= 0.75:
            verdict, conf, abstain = "likely_scam", p * 100, False
        elif p >= 0.45:
            verdict, conf, abstain = "needs_caution", p * 100, False
        else:
            verdict, conf, abstain = "likely_safe", max(55.0, (1 - p) * 100), False

    elif path == "factcheck":
        # fact_nli: P(claim false). Web dispute / ClaimReview / NLI set nli_label.
        # Do not let empty fuse mass or scam-meta force unverified when engine is conclusive.
        nli = next((r for r in results if r.engine_id == "fact_nli"), None)
        label = (nli.features.get("nli_label") if nli else None) or "NEI"
        eng_p = float(nli.probability) if nli and nli.available else float(p)
        if nli and not nli.abstain and label in ("REFUTES", "MISLEADING", "SUPPORTS"):
            p = eng_p
        if label == "NEI" or (nli and nli.abstain and label == "NEI"):
            verdict, conf, abstain = "unverified", min(45.0, max(20.0, eng_p * 100)), True
        elif label == "REFUTES":
            verdict, conf, abstain = "false", min(95.0, max(55.0, eng_p * 100)), False
        elif label == "MISLEADING":
            verdict, conf, abstain = "misleading", min(90.0, max(55.0, eng_p * 100)), False
        elif label == "SUPPORTS":
            sp = float(nli.features.get("support_p", 1 - eng_p)) if nli else (1 - eng_p)
            verdict, conf, abstain = "true", min(95.0, max(55.0, sp * 100)), False
        else:
            verdict, conf, abstain = "unverified", 40.0, True

    else:  # mediacheck — three-axis fusion (P_ai, P_edit, S_cam); conflict → inconclusive
        aigc = next((r for r in results if r.engine_id == "aigc"), None)
        meta_eng = next((r for r in results if r.engine_id == "metadata"), None)
        fora = next((r for r in results if r.engine_id == "forensics_ela"), None)
        axes = compute_axes(meta_eng, fora, aigc)
        decision = decide_media_verdict(axes, domain_shift=domain_shift_warning)
        verdict, conf, abstain = decision.verdict, decision.confidence, decision.abstain
        # Attach fusion analytics onto locked signals later via kernel; stash on aigc features for report
        fusion_blob = {
            "decision": decision.to_report_decision(),
            "analytics": build_analytics_payload(decision, meta_eng, fora, aigc),
        }
        if aigc is not None:
            aigc.features = {**(aigc.features or {}), "media_fusion": fusion_blob}
        elif meta_eng is not None:
            meta_eng.features = {**(meta_eng.features or {}), "media_fusion": fusion_blob}
        # Keep fused p for ECE logging (axis P_ai when ready)
        if axes.aigc_ready:
            p = float(axes.p_ai)
        else:
            p = float(1.0 - axes.s_cam) * 0.5 + float(axes.p_edit) * 0.5
        engines = [r.to_dict() for r in results]

    # ECE bucket heuristic until calibrator present
    ece_bucket = "well_calibrated" if meta_p is not None else "uncalibrated_heuristic"

    return LockedVerdict(
        verdict=verdict,
        confidence=round(float(conf), 1),
        abstain=abstain,
        engines=engines,
        evidence=evidence,
        ece_bucket=ece_bucket,
        domain_shift_warning=domain_shift_warning,
        path=path,
    )
