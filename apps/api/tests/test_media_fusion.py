"""Unit tests for three-axis media fusion decision table."""

from __future__ import annotations

from app.engines.base import EngineResult, Evidence
from app.engines.media_fusion import (
    MediaAxes,
    compute_axes,
    compute_s_cam_and_threat,
    decide_media_verdict,
    soft_watermark_boost,
)


def test_oppo_like_authentic_high():
    axes = MediaAxes(p_ai=0.32, p_edit=0.15, s_cam=0.90, aigc_ready=True)
    d = decide_media_verdict(axes)
    assert d.verdict == "likely_authentic"
    assert d.confidence >= 70
    assert d.agreement == "aligned"
    assert d.rule_id == "authentic_axes_aligned"


def test_gemini_watermark_no_exif_manipulated():
    axes = MediaAxes(
        p_ai=0.94,
        p_edit=0.15,
        s_cam=0.12,
        watermark_hit=True,
        watermark_score=0.8,
        aigc_ready=True,
    )
    d = decide_media_verdict(axes)
    assert d.verdict == "likely_manipulated"
    assert d.confidence >= 70
    assert d.abstain is False


def test_conflict_cam_vs_aigc_never_94():
    """User bug: strong EXIF + clean forensics + high AIGC/wm → inconclusive < 55."""
    axes = MediaAxes(
        p_ai=0.94,
        p_edit=0.15,
        s_cam=0.88,
        watermark_hit=True,
        watermark_score=0.85,
        aigc_ready=True,
    )
    d = decide_media_verdict(axes)
    assert d.verdict == "inconclusive"
    assert d.abstain is True
    assert d.confidence < 55
    assert d.agreement == "conflict"
    assert d.rule_id == "conflict_cam_vs_aigc"


def test_aigc_offline_strong_exif_authentic_medium():
    axes = MediaAxes(p_ai=0.35, p_edit=0.15, s_cam=0.88, aigc_ready=False)
    d = decide_media_verdict(axes)
    assert d.verdict == "likely_authentic"
    assert 60 <= d.confidence <= 78
    assert d.rule_id == "authentic_exif_forensics_aigc_offline"


def test_no_exif_mid_aigc_inconclusive():
    axes = MediaAxes(p_ai=0.50, p_edit=0.20, s_cam=0.12, aigc_ready=True)
    d = decide_media_verdict(axes)
    assert d.verdict == "inconclusive"
    assert d.abstain is True


def test_soft_watermark_boost_not_hard_max():
    p, hit, score = soft_watermark_boost(0.40, {"hit": True, "score": 0.80})
    assert hit is True
    # floor 0.50 + 0.28*0.80 = 0.724 — soft, not old max(p, 0.88+)
    assert abs(p - (0.50 + 0.28 * 0.80)) < 1e-6
    assert p < 0.88


def test_metadata_s_cam_threat_coherent_camera():
    feat = {
        "exif": {"make": "Z Camera", "model": "RNE-L21", "datetime_original": "2023:07:04 18:31:36"},
        "suspicious": [],
        "integrity_score": 88.0,
    }
    s_cam, p_threat, likely = compute_s_cam_and_threat(feat)
    assert s_cam >= 0.75
    assert p_threat < 0.35
    assert likely is True


def test_iphone_lightroom_edited_not_ai():
    """Camera EXIF + Lightroom + channel-noise + low AIGC → likely_edited (not AI, not inconclusive)."""
    meta = EngineResult(
        engine_id="metadata",
        probability=0.42,
        features={
            "exif": {
                "make": "Apple",
                "model": "iPhone 12 Pro Max",
                "datetime_original": "2024:05:18 19:20:20",
                "software": "Adobe Lightroom 9.2.2 (Android)",
            },
            "s_cam": 0.80,
            "integrity_score": 78,
            "camera_capture_likely": True,
            "edit_software": True,
            "generative_software": False,
            "suspicious": ["Post-capture editor in metadata: Adobe Lightroom 9.2.2 (Android)"],
        },
    )
    fora = EngineResult(
        engine_id="forensics_ela",
        probability=0.15,  # old aggregate buried the signal
        features={
            "ela_p": 0.05,
            "noise_p": 0.15,
            "edge_p": 0.45,
            "cfa_p": 0.15,
            "notes": [
                "Inconsistent color-channel noise",
                "CFA residual energy consistent with demosaiced camera capture",
            ],
        },
        evidence=[
            Evidence(type="forensics", value="Inconsistent color-channel noise", signal="ela_or_noise"),
        ],
    )
    aigc = EngineResult(
        engine_id="aigc",
        probability=0.31,
        features={"p_after_wm": 0.31, "watermark": {"hit": False, "score": 0}},
    )
    axes = compute_axes(meta, fora, aigc)
    assert axes.s_cam >= 0.70
    assert axes.p_edit >= 0.48
    assert axes.p_ai <= 0.45
    d = decide_media_verdict(axes)
    assert d.verdict == "likely_edited"
    assert d.abstain is False
    assert d.confidence >= 65
    assert d.rule_id == "edited_camera_low_ai"


def test_lightroom_does_not_tank_s_cam_via_generative_word():
    feat = {
        "exif": {
            "make": "Apple",
            "model": "iPhone 12 Pro Max",
            "datetime_original": "2024:05:18 19:20:20",
            "software": "Adobe Lightroom 9.2.2 (Android)",
        },
        "suspicious": ["Post-capture editor in metadata: Adobe Lightroom 9.2.2 (Android)"],
        "integrity_score": 78.0,
        "edit_software": True,
        "generative_software": False,
    }
    s_cam, p_threat, likely = compute_s_cam_and_threat(feat)
    assert s_cam >= 0.70
    assert likely is True
    assert p_threat < 0.55
