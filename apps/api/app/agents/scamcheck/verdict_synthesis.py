"""ScamVerdictAgent — synthesize a scam verdict from pattern matches and risk signals."""

import json
import logging
from typing import Any

from app.agents.base import BaseAgent

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are the scam verdict engine for Nigehban, a Pakistani anti-fraud platform.

Your task: Produce a scam assessment verdict based on pattern match results and risk
signal analysis. You must be cautious, transparent, and bilingual.

## Verdict Categories (choose exactly one):
- **likely_scam**: Strong evidence that this is a scam. Multiple high-severity red flags
  and/or pattern match to known scam types.
- **needs_caution**: Some suspicious elements detected, but not conclusive enough to
  definitively label as a scam. The user should be careful.
- **likely_safe**: No significant scam indicators found. The message appears legitimate.
  Note: absence of red flags does not guarantee safety.

## Rules:
1. Weigh the severity and number of red flags heavily. A single high-severity flag
   (e.g., money request + impersonation) should push toward likely_scam.
2. Pattern matches to known scam types are strong signals — respect them.
3. When uncertain, err on the side of caution (needs_caution).
4. Write explanations in BOTH English and Urdu. The Urdu should be natural, clear,
   and accessible to a general Pakistani audience. Use plain language.
5. Explain *why* the verdict was reached, referencing specific red flags.
6. If likely_scam, identify the scam_type if determinable.
7. Include practical advice for the user (e.g., "Do not send money", "Verify with the
   organization directly").

## Return ONLY valid JSON (no markdown fences):
{
  "verdict": "likely_scam | needs_caution | likely_safe",
  "confidence": 80,
  "explanation_en": "Detailed English explanation...",
  "explanation_ur": "تفصیلی اردو وضاحت...",
  "red_flags": [
    {"type": "flag type", "severity": "high|medium|low", "description": "Why this is concerning"}
  ],
  "scam_type": "phishing | advance_fee | impersonation | lottery | investment | romance | other | null",
  "advice": "Practical advice for the user",
  "sources": []
}
"""


# ---------------------------------------------------------------------------
# Agent implementation
# ---------------------------------------------------------------------------

class ScamVerdictSynthesisAgent(BaseAgent):
    """Synthesize a scam verdict from pattern matches and risk signal analysis.

    This is the final step in the scam-check pipeline. It uses Sonnet (the
    reasoning model) to combine pattern match data and risk signals into
    a coherent, bilingual verdict with actionable advice.
    """

    name: str = "scamcheck_verdict"
    model_tier: str = "sonnet"
    timeout: float = 30.0

    async def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Produce a scam verdict.

        Args:
            input_data: Dict with keys:
                - text (str): The original text being analyzed.
                - pattern_match (dict): Output from PatternMatchAgent.
                - risk_signals (dict): Output from RiskSignalAgent.
                - language (str): Language code.

        Returns:
            Dict with keys:
                - verdict (str): One of the three verdict categories.
                - confidence (int): 0–100.
                - explanation_en (str): English explanation.
                - explanation_ur (str): Urdu explanation.
                - red_flags (list): Consolidated red flags.
                - scam_type (str | None): Identified scam type.
                - sources (list): Reference sources (usually empty for scam checks).
        """
        text = input_data.get("text", "")
        pattern_match = input_data.get("pattern_match", {})
        risk_signals = input_data.get("risk_signals", {})
        language = input_data.get("language", "en")

        # Build the user message
        user_content = (
            f"## Original Message\n{text}\n\n"
            f"## Language\n{language}\n\n"
            f"## Pattern Match Results\n{json.dumps(pattern_match, indent=2, default=str)}\n\n"
            f"## Risk Signal Analysis\n{json.dumps(risk_signals, indent=2, default=str)}\n\n"
            "Produce your scam assessment verdict based on the above information."
        )

        try:
            response = await self.call_llm(
                system_prompt=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_content}],
                max_tokens=2048,
            )

            parsed = response.get("json")
            if parsed and isinstance(parsed, dict):
                return self._normalize_verdict(parsed, risk_signals)

            # Fallback: parse from raw text
            raw_text = response.get("text", "")
            try:
                parsed = json.loads(raw_text)
                if isinstance(parsed, dict):
                    return self._normalize_verdict(parsed, risk_signals)
            except (json.JSONDecodeError, ValueError):
                pass

            # Last resort: derive verdict from risk score alone
            return self._fallback_verdict(risk_signals)

        except Exception:
            logger.exception("ScamVerdictSynthesisAgent failed")
            return {
                "verdict": "needs_caution",
                "confidence": 0,
                "explanation_en": "An error occurred during scam verdict synthesis.",
                "explanation_ur": "اسکیم فیصلے کی تیاری میں خرابی پیش آئی۔",
                "red_flags": [],
                "scam_type": None,
                "sources": [],
            }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_verdict(
        parsed: dict[str, Any],
        risk_signals: dict[str, Any],
    ) -> dict[str, Any]:
        """Ensure the parsed LLM output conforms to the expected schema."""
        valid_verdicts = {"likely_scam", "needs_caution", "likely_safe"}
        valid_scam_types = {
            "phishing", "advance_fee", "impersonation", "lottery",
            "investment", "romance", "other", None,
        }

        verdict = str(parsed.get("verdict", "needs_caution")).lower().strip()
        if verdict not in valid_verdicts:
            verdict = "needs_caution"

        conf = parsed.get("confidence", 50)
        if isinstance(conf, float) and conf <= 1.0:
            conf = int(conf * 100)
        confidence = max(0, min(100, int(conf)))

        scam_type = parsed.get("scam_type")
        if scam_type is not None:
            scam_type = str(scam_type).lower().strip()
            if scam_type == "null" or scam_type == "none":
                scam_type = None

        red_flags = parsed.get("red_flags", risk_signals.get("red_flags", []))
        if not isinstance(red_flags, list):
            red_flags = []

        sources = parsed.get("sources", [])
        if not isinstance(sources, list):
            sources = []

        return {
            "verdict": verdict,
            "confidence": confidence,
            "explanation_en": str(parsed.get("explanation_en", "")),
            "explanation_ur": str(parsed.get("explanation_ur", "")),
            "red_flags": red_flags,
            "scam_type": scam_type,
            "advice": str(parsed.get("advice", "")),
            "sources": sources,
        }

    @staticmethod
    def _fallback_verdict(risk_signals: dict[str, Any]) -> dict[str, Any]:
        """Derive a verdict purely from risk score when LLM parsing fails."""
        risk_score = risk_signals.get("risk_score", 0)
        red_flags = risk_signals.get("red_flags", [])

        if risk_score >= 60:
            verdict = "likely_scam"
        elif risk_score >= 30:
            verdict = "needs_caution"
        else:
            verdict = "likely_safe"

        return {
            "verdict": verdict,
            "confidence": 30,  # Low confidence — no LLM synthesis
            "explanation_en": (
                f"Based on automated analysis (risk score: {risk_score}/100), "
                f"this message is assessed as '{verdict}'. "
                f"{len(red_flags)} red flag(s) were detected."
            ),
            "explanation_ur": (
                f"خودکار تجزیہ کی بنیاد پر (رسک اسکور: {risk_score}/100)، "
                f"یہ پیغام '{verdict}' کے طور پر جانچا گیا ہے۔"
            ),
            "red_flags": red_flags,
            "scam_type": risk_signals.get("scam_type_guess"),
            "sources": [],
        }
