"""Three-axis media authenticity fusion — research-backed conflict escalate.

Axes (all in [0, 1]):
  P_ai   — likelihood of AI generation (model + soft watermark boost)
  P_edit — classical forensic suspicion (ELA / noise / edge / CFA)
  S_cam  — camera authenticity prior from hardware EXIF

Conflict policy: strong S_cam + clean P_edit vs high P_ai/watermark → inconclusive
(never 90%+ manipulated). See docs/DETECTION_METHODOLOGY.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.engines.base import EngineResult


AXIS_LABELS = {
    "p_ai": "AI generation likelihood",
    "p_edit": "Edit / composite likelihood",
    "s_cam": "Camera authenticity prior",
}

_GEN_SOFT = ("midjourney", "gemini", "dall-e", "dall·e", "stable diffusion", "firefly", "imagen", "leonardo")
_EDIT_APPS = ("photoshop", "gimp", "lightroom", "snapseed", "picsart", "canva", "affinity", "capture one", "darktable")

# Forensic note phrases that raise edit likelihood (not AI)
_EDIT_FORENSIC_HINTS = (
    "inconsistent color-channel",
    "inconsistent residual-noise",
    "elevated ela",
    "possible heavy smoothing",
    "compos",
)


@dataclass
class MediaAxes:
    p_ai: float
    p_edit: float
    s_cam: float
    watermark_hit: bool = False
    watermark_score: float = 0.0
    aigc_ready: bool = False
    edit_software: bool = False
    generative_software: bool = False

    def as_dict(self) -> dict[str, float]:
        return {
            "p_ai": round(float(self.p_ai), 4),
            "p_edit": round(float(self.p_edit), 4),
            "s_cam": round(float(self.s_cam), 4),
        }


@dataclass
class MediaDecision:
    verdict: str
    confidence: float
    abstain: bool
    rule_id: str
    rule_label: str
    agreement: str  # aligned | partial | conflict
    axes: MediaAxes
    why: list[str] = field(default_factory=list)
    confidence_breakdown: list[dict[str, Any]] = field(default_factory=list)

    def to_report_decision(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "rule_label": self.rule_label,
            "agreement": self.agreement,
            "axes": self.axes.as_dict(),
            "axis_labels": dict(AXIS_LABELS),
            "confidence_breakdown": self.confidence_breakdown,
            "why": list(self.why),
            "watermark_hit": self.axes.watermark_hit,
            "aigc_ready": self.axes.aigc_ready,
        }


def score_s_cam_from_meta_features(features: dict[str, Any] | None) -> float:
    """Camera authenticity prior from metadata engine features.

    Post-capture editors (Lightroom, etc.) slightly reduce S_cam but do NOT
    treat the file as AI. Only generative software tags crush the prior.
    """
    feat = features or {}
    exif = feat.get("exif") if isinstance(feat.get("exif"), dict) else {}
    soft = str(exif.get("software") or "").lower()
    gen_flag = bool(feat.get("generative_software"))
    edit_flag = bool(feat.get("edit_software"))
    if not gen_flag and soft:
        gen_flag = any(g in soft for g in _GEN_SOFT) or ("dall" in soft and "dollar" not in soft)
    if not edit_flag and soft:
        edit_flag = any(e in soft for e in _EDIT_APPS)

    # Never use the word "generative" from our own warning strings as a match key
    suspicious = [str(s).lower() for s in (feat.get("suspicious") or [])]
    if any(s.startswith("generative ai software") for s in suspicious):
        gen_flag = True
    if any(s.startswith("post-capture editor") for s in suspicious):
        edit_flag = True

    make = bool(exif.get("make"))
    model = bool(exif.get("model"))
    dto = bool(exif.get("datetime_original"))
    has_camera = make or model

    if gen_flag:
        return 0.12
    if has_camera and dto:
        integrity = float(feat.get("integrity_score") or (78.0 if edit_flag else 88.0))
        s = max(0.72, min(0.95, 0.55 + integrity / 250.0))
        if edit_flag:
            s = min(s, 0.82)  # still a camera capture, but edited
        return float(s)
    if has_camera or dto or bool(exif):
        return 0.40 if edit_flag else 0.35
    return 0.12


def compute_s_cam_and_threat(features: dict[str, Any]) -> tuple[float, float, bool]:
    """Return (s_cam, p_threat, camera_capture_likely) for metadata engine."""
    s_cam = score_s_cam_from_meta_features(features)
    p_threat = max(0.08, min(0.55, 1.0 - s_cam))
    exif = features.get("exif") if isinstance(features.get("exif"), dict) else {}
    if features.get("generative_software"):
        p_threat = 0.85
        s_cam = min(s_cam, 0.12)
    elif features.get("edit_software"):
        p_threat = max(p_threat, 0.42)
    camera_likely = s_cam >= 0.70 and bool(exif.get("make") or exif.get("model")) and bool(
        exif.get("datetime_original")
    )
    return float(s_cam), float(p_threat), bool(camera_likely)


def soft_watermark_boost(p_model: float, wm: dict[str, Any] | None) -> tuple[float, bool, float]:
    """Additive watermark boost — never hard-max alone to 0.99."""
    wm = wm or {}
    score = float(wm.get("score") or 0.0)
    hit = bool(wm.get("hit")) and score >= 0.55
    if hit:
        base = max(float(p_model), 0.50)
        p = min(0.99, base + 0.28 * score)
        return p, True, score
    return float(p_model), False, score


def _edit_boost_from_sources(
    meta: EngineResult | None,
    fora: EngineResult | None,
) -> tuple[float, bool, bool]:
    """Raise P_edit from editor EXIF + forensic edit notes. Returns (boost, edit_sw, gen_sw)."""
    feat_m = (meta.features or {}) if meta else {}
    edit_sw = bool(feat_m.get("edit_software"))
    gen_sw = bool(feat_m.get("generative_software"))
    soft = str(((feat_m.get("exif") or {}) if isinstance(feat_m.get("exif"), dict) else {}).get("software") or "").lower()
    if not edit_sw and soft and any(e in soft for e in _EDIT_APPS):
        edit_sw = True
    if not gen_sw and soft and (any(g in soft for g in _GEN_SOFT) or ("dall" in soft)):
        gen_sw = True

    boost = 0.0
    if edit_sw and not gen_sw:
        boost = max(boost, 0.55)  # Lightroom/Photoshop is strong edit prior

    notes = []
    if fora and fora.features:
        notes = [str(n).lower() for n in (fora.features.get("notes") or [])]
        # Also scan evidence
    if fora:
        notes.extend(str(getattr(e, "value", "")).lower() for e in fora.evidence)
        for n in (fora.features or {}).get("notes") or []:
            notes.append(str(n).lower())
    for n in notes:
        if any(h in n for h in _EDIT_FORENSIC_HINTS):
            boost = max(boost, 0.50)
        if "inconsistent color-channel" in n:
            boost = max(boost, 0.58)

    # Edge channel inconsistency lives in edge_p even when aggregate p was crushed
    if fora and fora.features:
        edge_p = float((fora.features or {}).get("edge_p") or 0)
        if edge_p >= 0.45:
            boost = max(boost, 0.52)

    return float(boost), edit_sw, gen_sw


def compute_axes(
    meta: EngineResult | None,
    fora: EngineResult | None,
    aigc: EngineResult | None,
) -> MediaAxes:
    feat_m = (meta.features or {}) if meta else {}
    s_cam = float(feat_m.get("s_cam") if feat_m.get("s_cam") is not None else score_s_cam_from_meta_features(feat_m))

    base_edit = float(fora.probability) if fora and fora.available else 0.20
    edit_boost, edit_sw, gen_sw = _edit_boost_from_sources(meta, fora)
    # P_edit = max(classical aggregate, structured edit evidence) — do not let ELA-dominate bury Lightroom
    p_edit = max(base_edit, edit_boost)

    aigc_ready = bool(aigc and aigc.available and not aigc.abstain)
    wm = (aigc.features or {}).get("watermark") if aigc else {}
    wm = wm if isinstance(wm, dict) else {}
    watermark_hit = bool(wm.get("hit")) and float(wm.get("score") or 0) >= 0.55
    wm_score = float(wm.get("score") or 0)

    if aigc_ready:
        p_ai = float(aigc.probability)
        if aigc.features and aigc.features.get("p_after_wm") is not None:
            p_ai = float(aigc.features["p_after_wm"])
    else:
        p_ai = 0.35

    return MediaAxes(
        p_ai=max(0.0, min(1.0, p_ai)),
        p_edit=max(0.0, min(1.0, p_edit)),
        s_cam=max(0.0, min(1.0, s_cam)),
        watermark_hit=watermark_hit,
        watermark_score=wm_score,
        aigc_ready=aigc_ready,
        edit_software=edit_sw,
        generative_software=gen_sw,
    )


def _breakdown(steps: list[tuple[str, float | None, float | None]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for name, value, delta in steps:
        row: dict[str, Any] = {"step": name}
        if value is not None:
            row["value"] = round(float(value), 1)
        if delta is not None:
            row["delta"] = round(float(delta), 1)
        out.append(row)
    return out


def decide_media_verdict(
    axes: MediaAxes,
    *,
    domain_shift: bool = False,
) -> MediaDecision:
    """Lock mediacheck verdict from three axes + conflict rules."""
    p_ai, p_edit, s_cam = axes.p_ai, axes.p_edit, axes.s_cam
    wm = axes.watermark_hit

    # --- Conflict escalate FIRST when strong EXIF fights elevated AIGC/watermark ---
    if s_cam >= 0.70 and (p_ai >= 0.55 or wm):
        base = 48.0
        penalty = 12.0 if wm else 8.0
        conf = max(28.0, min(52.0, base - penalty + abs(p_ai - 0.55) * 5))
        why = [
            f"Strong camera EXIF prior (S_cam={s_cam:.2f})",
            (
                f"Clean or moderate forensics (P_edit={p_edit:.2f})"
                if p_edit < 0.52
                else f"Elevated edit score (P_edit={p_edit:.2f})"
            ),
            f"Elevated AIGC (P_ai={p_ai:.2f})" + (" + watermark" if wm else ""),
            "Axes conflict — abstaining instead of overclaiming",
        ]
        return MediaDecision(
            verdict="inconclusive",
            confidence=round(conf, 1),
            abstain=True,
            rule_id="conflict_cam_vs_aigc",
            rule_label="Camera EXIF conflicts with AIGC",
            agreement="conflict",
            axes=axes,
            why=why,
            confidence_breakdown=_breakdown(
                [
                    ("base", base, None),
                    ("conflict_penalty", None, -penalty),
                    ("final", conf, None),
                ]
            ),
        )

    # --- Edited human capture: camera prior + low AI + elevated edit evidence ---
    # This is NOT AI-generated — post-capture editing (Lightroom, channel noise, etc.)
    if (
        s_cam >= 0.55
        and p_ai <= 0.45
        and p_edit >= 0.48
        and not wm
        and not axes.generative_software
    ):
        conf = min(88.0, max(68.0, 55 + p_edit * 35 + (s_cam - 0.55) * 20))
        why = [
            f"Camera capture prior present (S_cam={s_cam:.2f})",
            f"Low AI-generation score (P_ai={p_ai:.2f}) — not classified as AI-generated",
            f"Elevated edit / composite evidence (P_edit={p_edit:.2f})",
        ]
        if axes.edit_software:
            why.append("Post-capture editor tag in EXIF (e.g. Lightroom / Photoshop)")
        return MediaDecision(
            verdict="likely_edited",
            confidence=round(conf, 1),
            abstain=False,
            rule_id="edited_camera_low_ai",
            rule_label="Human camera capture with post-capture editing",
            agreement="aligned",
            axes=axes,
            why=why,
            confidence_breakdown=_breakdown(
                [
                    ("base", 55.0, None),
                    ("p_edit_weight", None, p_edit * 35),
                    ("final", conf, None),
                ]
            ),
        )

    # --- Authentic: axes agree human unmodified ---
    if s_cam >= 0.70 and p_edit < 0.42 and (not axes.aigc_ready or p_ai <= 0.45):
        if not axes.aigc_ready:
            base = 68.0
            conf = min(78.0, max(62.0, base + (s_cam - 0.70) * 40))
            why = [
                f"Strong camera EXIF prior (S_cam={s_cam:.2f})",
                f"Clean classical forensics (P_edit={p_edit:.2f})",
                "AIGC remote offline — authentic rests on EXIF + forensics",
            ]
            return MediaDecision(
                verdict="likely_authentic",
                confidence=round(conf, 1),
                abstain=False,
                rule_id="authentic_exif_forensics_aigc_offline",
                rule_label="Camera EXIF + clean forensics (AIGC offline)",
                agreement="partial",
                axes=axes,
                why=why,
                confidence_breakdown=_breakdown(
                    [("base", 68.0, None), ("s_cam_bonus", None, conf - 68.0), ("final", conf, None)]
                ),
            )
        base = 78.0
        agreement_bonus = (0.45 - p_ai) * 20 + (0.45 - p_edit) * 10
        conf = min(92.0, max(72.0, base + agreement_bonus))
        if domain_shift:
            conf = min(conf, 70.0)
        why = [
            f"Strong camera EXIF prior (S_cam={s_cam:.2f})",
            f"Clean classical forensics (P_edit={p_edit:.2f})",
            f"Low AI-generation score (P_ai={p_ai:.2f})",
        ]
        return MediaDecision(
            verdict="likely_authentic",
            confidence=round(conf, 1),
            abstain=False,
            rule_id="authentic_axes_aligned",
            rule_label="Camera EXIF + clean forensics + low AIGC",
            agreement="aligned",
            axes=axes,
            why=why,
            confidence_breakdown=_breakdown(
                [
                    ("base", 78.0, None),
                    ("agreement_bonus", None, agreement_bonus),
                    ("domain_shift_cap", None, -8.0 if domain_shift else 0.0),
                    ("final", conf, None),
                ]
            ),
        )

    # --- Rule: Watermark + weak cam (trusted when EXIF absent/weak) ---
    if wm and s_cam < 0.45:
        conf = max(78.0, min(94.0, max(p_ai, 0.70) * 100))
        why = [
            f"Platform watermark with weak camera prior (S_cam={s_cam:.2f})",
            f"AIGC score after soft boost (P_ai={p_ai:.2f})",
        ]
        return MediaDecision(
            verdict="likely_manipulated",
            confidence=round(conf, 1),
            abstain=False,
            rule_id="manipulated_watermark_weak_cam",
            rule_label="Watermark + weak camera EXIF",
            agreement="aligned",
            axes=axes,
            why=why,
            confidence_breakdown=_breakdown([("base", conf, None), ("final", conf, None)]),
        )

    # --- Rule: Clear AI without camera story ---
    if p_ai >= 0.70 and s_cam < 0.45:
        base = max(70.0, p_ai * 100)
        conf = min(96.0, base)
        why = [
            f"High AI-generation score (P_ai={p_ai:.2f})",
            f"Weak camera authenticity prior (S_cam={s_cam:.2f})",
        ]
        return MediaDecision(
            verdict="likely_manipulated",
            confidence=round(conf, 1),
            abstain=False,
            rule_id="manipulated_high_ai_weak_cam",
            rule_label="High AIGC with weak/absent camera EXIF",
            agreement="aligned",
            axes=axes,
            why=why,
            confidence_breakdown=_breakdown([("base", base, None), ("final", conf, None)]),
        )

    # --- Rule: Heavy edit suspicion, weak cam ---
    if p_edit >= 0.60 and s_cam < 0.45:
        if p_ai >= 0.55:
            conf = min(85.0, max(60.0, 50 + p_edit * 40 + p_ai * 15))
            return MediaDecision(
                verdict="likely_manipulated",
                confidence=round(conf, 1),
                abstain=False,
                rule_id="manipulated_edit_and_ai",
                rule_label="Elevated edit forensics + elevated AIGC",
                agreement="partial",
                axes=axes,
                why=[
                    f"Elevated edit/composite score (P_edit={p_edit:.2f})",
                    f"Elevated AIGC (P_ai={p_ai:.2f})",
                    f"Weak camera prior (S_cam={s_cam:.2f})",
                ],
                confidence_breakdown=_breakdown([("base", conf, None), ("final", conf, None)]),
            )
        conf = 45.0
        return MediaDecision(
            verdict="inconclusive",
            confidence=conf,
            abstain=True,
            rule_id="inconclusive_edit_only",
            rule_label="Elevated edit forensics without clear AI",
            agreement="partial",
            axes=axes,
            why=[
                f"Elevated edit score (P_edit={p_edit:.2f})",
                "AIGC not decisive — escalate rather than overclaim",
            ],
            confidence_breakdown=_breakdown([("base", 45.0, None), ("final", 45.0, None)]),
        )

    # --- Soft / offline / mid band → inconclusive ---
    if not axes.aigc_ready:
        conf = 42.0
        why = ["AIGC remote unavailable", f"S_cam={s_cam:.2f}", f"P_edit={p_edit:.2f}"]
        # Already handled authentic offline above; remaining → inconclusive
        return MediaDecision(
            verdict="inconclusive",
            confidence=conf,
            abstain=True,
            rule_id="inconclusive_aigc_offline",
            rule_label="AIGC offline and axes not decisive for authentic",
            agreement="partial",
            axes=axes,
            why=why,
            confidence_breakdown=_breakdown([("base", 42.0, None), ("final", 42.0, None)]),
        )

    conf = max(35.0, min(52.0, 40 + abs(p_ai - 0.5) * 20))
    why = [
        f"Signals in soft band (P_ai={p_ai:.2f}, P_edit={p_edit:.2f}, S_cam={s_cam:.2f})",
        "No decisive agreement across axes",
    ]
    return MediaDecision(
        verdict="inconclusive",
        confidence=round(conf, 1),
        abstain=True,
        rule_id="inconclusive_soft_band",
        rule_label="Soft / ambiguous multi-axis band",
        agreement="partial",
        axes=axes,
        why=why,
        confidence_breakdown=_breakdown([("base", conf, None), ("final", conf, None)]),
    )


def build_analytics_payload(
    decision: MediaDecision,
    meta: EngineResult | None,
    fora: EngineResult | None,
    aigc: EngineResult | None,
) -> dict[str, Any]:
    a_feat = (aigc.features or {}) if aigc else {}
    f_feat = (fora.features or {}) if fora else {}
    m_feat = (meta.features or {}) if meta else {}
    wm = a_feat.get("watermark") if isinstance(a_feat.get("watermark"), dict) else {}

    notes = [
        "CLIP zero-shot can false-positive on real camera photos — fused conservatively with UnivFD.",
        "Platform watermark is soft evidence; strong camera EXIF triggers conflict abstain instead of a hard lock.",
        "Confidence is calibrated from axis agreement, not a raw model probability.",
    ]
    if decision.agreement == "conflict":
        notes.insert(0, "Camera authenticity prior conflicts with AIGC — verdict escalated to inconclusive.")

    return {
        "aigc_components": {
            "zeroshot": a_feat.get("p_zeroshot"),
            "univfd": a_feat.get("p_univfd"),
            "fused_model": a_feat.get("p_fused_pre_wm") or a_feat.get("p_model"),
            "watermark": wm,
            "p_ai": decision.axes.p_ai,
            "p_after_wm": a_feat.get("p_after_wm"),
        },
        "forensic_components": {
            "ela": f_feat.get("ela_p"),
            "residual_noise": f_feat.get("noise_p"),
            "edge_anomaly": f_feat.get("edge_p"),
            "cfa": f_feat.get("cfa_p"),
            "p_edit": decision.axes.p_edit,
        },
        "metadata_integrity": {
            "integrity_score": m_feat.get("integrity_score"),
            "s_cam": decision.axes.s_cam,
            "camera_capture_likely": m_feat.get("camera_capture_likely"),
            "suspicious": m_feat.get("suspicious") or [],
        },
        "reliability_notes": notes,
    }
