"""VisualAnalysisAgent — delegates to forensics engine (no hardcoded GAN probs)."""

from typing import Any

from app.agents.base import BaseAgent
from app.engines.media_forensics import run_forensics_engine


class VisualAnalysisAgent(BaseAgent):
    """Analyze image via ELA / noise forensics."""

    name: str = "visual_analysis"
    model_tier: str = "haiku"
    timeout: float = 30.0

    async def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        media_url = input_data.get("media_url", "")
        result = await run_forensics_engine(media_url)
        out = {
            "face_artifacts_detected": None,  # unknown without face ONNX
            "lighting_consistency": None,
            "edge_anomalies": [e.value for e in result.evidence],
            "gan_probability": None,  # never fabricate — use deepfake/aigc engines
            "manipulation_regions": [],
            "visual_integrity_score": round((1.0 - result.probability) * 100, 1),
            "forensics_p": result.probability,
            "engine": result.to_dict(),
            "domain_shift_warning": result.features.get("domain_shift_warning"),
        }
        if not result.available:
            out["engine_offline"] = True
            out["note"] = result.note
        conf = 55 if result.evidence else 30
        return {"output": out, "confidence": conf}
