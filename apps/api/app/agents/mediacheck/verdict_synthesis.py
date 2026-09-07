"""MediaVerdictSynthesisAgent — synthesize a final media authenticity verdict from all sub-agent results."""

import json
import logging
from typing import Any

from app.agents.base import BaseAgent

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are the media verdict engine for Nigehban, a Pakistani media authenticity platform.

Your task: Produce a final authenticity verdict by synthesizing results from four analysis
agents: metadata extraction, visual analysis, audio synchronization, and reverse search.
You must be rigorous, transparent, and bilingual.

## Verdict Categories (choose exactly one):
- **likely_authentic**: The media shows strong signs of being genuine. Metadata is intact,
  no visual manipulation detected, audio is consistent, and/or reverse search confirms
  a known original source.
- **likely_manipulated**: Strong evidence of manipulation. Multiple analysis agents found
  manipulation indicators — face artifacts, spliced audio, stripped metadata with
  suspicious signals, or reverse search found an earlier/different version.
- **inconclusive**: Insufficient or conflicting evidence to make a definitive determination.
  DEFAULT when uncertain — never guess.

## Rules:
1. NEVER fabricate evidence. Only reference the analysis results provided to you.
2. Always default to "inconclusive" when evidence is insufficient or conflicting.
3. Weigh signals from all four agents, but note that some may be more reliable than others:
   - Visual analysis and audio sync are strong indicators of deepfakes/manipulation
   - Metadata absence alone is not conclusive (social media strips metadata)
   - Reverse search is strongest for establishing provenance
4. Write explanations in BOTH English and Urdu. The Urdu explanation should be natural,
   not a word-for-word translation. Use clear, simple language accessible to a general
   Pakistani audience.
5. List each significant signal as a structured entry in the signals array.
6. authenticity_score is 0-100 (100 = definitely authentic, 0 = definitely manipulated).
7. confidence is 0-100 reflecting how confident you are in this verdict.

## Signal Categories:
- metadata: Signals from metadata analysis (EXIF, compression, dates)
- visual: Signals from visual analysis (face artifacts, lighting, GAN detection)
- audio: Signals from audio analysis (sync, splicing, voice consistency)
- provenance: Signals from reverse search (original source, prior fact-checks)

## Return ONLY valid JSON (no markdown fences):
{
  "verdict": "likely_authentic | likely_manipulated | inconclusive",
  "confidence": 75,
  "explanation_en": "Detailed English explanation referencing specific signals...",
  "explanation_ur": "تفصیلی اردو وضاحت...",
  "signals": [
    {
      "category": "metadata | visual | audio | provenance",
      "type": "signal type description",
      "severity": "high | medium | low",
      "description": "Detailed description of the signal",
      "supports_authenticity": true
    }
  ],
  "authenticity_score": 72
}
"""


# ---------------------------------------------------------------------------
# Agent implementation
# ---------------------------------------------------------------------------

class MediaVerdictSynthesisAgent(BaseAgent):
    """Synthesize a media authenticity verdict from all sub-agent results.

    This is the final step in the media-check pipeline. It uses Sonnet (the
    reasoning model) to combine metadata, visual, audio, and reverse search
    data into a coherent, bilingual verdict with signal transparency.
    """

    name: str = "media_verdict"
    model_tier: str = "sonnet"
    timeout: float = 30.0

    async def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Produce a media authenticity verdict.

        Args:
            input_data: Dict with keys:
                - metadata (dict): Output from MetadataExtractAgent.
                - visual (dict): Output from VisualAnalysisAgent.
                - audio (dict): Output from AudioSyncAgent.
                - reverse_search (dict): Output from ReverseSearchAgent.
                - media_url (str): The original media URL.

        Returns:
            Dict with keys:
                - verdict (str): One of three verdict categories.
                - confidence (float): 0–100 confidence score.
                - explanation_en (str): English explanation.
                - explanation_ur (str): Urdu explanation.
                - signals (list): Structured signal entries.
                - authenticity_score (int): 0–100 authenticity score.
        """
        metadata = input_data.get("metadata", {})
        visual = input_data.get("visual", {})
        audio = input_data.get("audio", {})
        reverse_search = input_data.get("reverse_search", {})
        media_url = input_data.get("media_url", "")

        # Build the user message
        user_content = (
            f"## Media URL\n{media_url}\n\n"
            f"## Metadata Analysis\n{json.dumps(metadata, indent=2, default=str)}\n\n"
            f"## Visual Analysis\n{json.dumps(visual, indent=2, default=str)}\n\n"
            f"## Audio Analysis\n{json.dumps(audio, indent=2, default=str)}\n\n"
            f"## Reverse Search Results\n{json.dumps(reverse_search, indent=2, default=str)}\n\n"
            "Synthesize all analysis results into a final media authenticity verdict."
        )

        try:
            response = await self.call_llm(
                system_prompt=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_content}],
                max_tokens=2048,
            )

            parsed = response.get("json")
            if parsed and isinstance(parsed, dict):
                return self._normalize_verdict(parsed)

            # Fallback: parse from raw text
            raw_text = response.get("text", "")
            try:
                parsed = json.loads(raw_text)
                if isinstance(parsed, dict):
                    return self._normalize_verdict(parsed)
            except (json.JSONDecodeError, ValueError):
                pass

            # Last resort: derive verdict from individual agent scores
            logger.warning("MediaVerdictSynthesisAgent: could not parse LLM output as JSON")
            return self._fallback_verdict(metadata, visual, audio, reverse_search)

        except Exception:
            logger.exception("MediaVerdictSynthesisAgent failed")
            return {
                "verdict": "inconclusive",
                "confidence": 0.0,
                "explanation_en": "An error occurred during media verdict synthesis.",
                "explanation_ur": "میڈیا فیصلے کی تیاری میں خرابی پیش آئی۔",
                "signals": [],
                "authenticity_score": 50,
                "sources": [],
            }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_verdict(parsed: dict[str, Any]) -> dict[str, Any]:
        """Ensure the parsed LLM output conforms to the expected schema."""
        valid_verdicts = {"likely_authentic", "likely_manipulated", "inconclusive"}

        verdict = str(parsed.get("verdict", "inconclusive")).lower().strip()
        if verdict not in valid_verdicts:
            verdict = "inconclusive"

        conf = parsed.get("confidence", 50)
        if isinstance(conf, float) and conf <= 1.0:
            conf = int(conf * 100)
        confidence = max(0, min(100, int(conf)))

        auth_score = parsed.get("authenticity_score", 50)
        if isinstance(auth_score, float) and auth_score <= 1.0:
            auth_score = int(auth_score * 100)
        authenticity_score = max(0, min(100, int(auth_score)))

        signals = parsed.get("signals", [])
        if not isinstance(signals, list):
            signals = []
        # Validate each signal
        valid_categories = {"metadata", "visual", "audio", "provenance"}
        valid_severities = {"high", "medium", "low"}
        validated_signals = []
        for signal in signals:
            if isinstance(signal, dict):
                category = str(signal.get("category", "other")).lower().strip()
                if category not in valid_categories:
                    category = "other"
                severity = str(signal.get("severity", "low")).lower().strip()
                if severity not in valid_severities:
                    severity = "low"
                validated_signals.append({
                    "category": category,
                    "type": str(signal.get("type", "unknown")),
                    "severity": severity,
                    "description": str(signal.get("description", "")),
                    "supports_authenticity": bool(signal.get("supports_authenticity", True)),
                })
        signals = validated_signals

        return {
            "verdict": verdict,
            "confidence": float(confidence),
            "explanation_en": str(parsed.get("explanation_en", "")),
            "explanation_ur": str(parsed.get("explanation_ur", "")),
            "signals": signals,
            "authenticity_score": authenticity_score,
            "sources": [],
        }

    @staticmethod
    def _fallback_verdict(
        metadata: dict[str, Any],
        visual: dict[str, Any],
        audio: dict[str, Any],
        reverse_search: dict[str, Any],
    ) -> dict[str, Any]:
        """Derive a verdict from individual agent scores when LLM parsing fails."""
        # Collect integrity/authenticity scores from each agent
        scores = []

        meta_score = metadata.get("metadata_integrity_score", 50)
        if isinstance(meta_score, (int, float)):
            scores.append(float(meta_score))

        visual_score = visual.get("visual_integrity_score", 50)
        if isinstance(visual_score, (int, float)):
            scores.append(float(visual_score))

        audio_score = audio.get("audio_integrity_score", 50)
        if isinstance(audio_score, (int, float)):
            scores.append(float(audio_score))

        # Reverse search contribution
        if reverse_search.get("original_found"):
            scores.append(70.0)  # Having an original source is a positive signal
        elif reverse_search.get("match_confidence", 0) > 0.5:
            scores.append(50.0)

        if not scores:
            avg_score = 50.0
        else:
            avg_score = sum(scores) / len(scores)

        # Determine verdict
        manipulation_signals = 0
        if visual.get("face_artifacts_detected"):
            manipulation_signals += 1
        if visual.get("gan_probability", 0) > 0.7:
            manipulation_signals += 1
        if audio.get("audio_splicing_detected"):
            manipulation_signals += 1
        if not metadata.get("has_exif", True) and metadata.get("suspicious_metadata"):
            manipulation_signals += 1

        if manipulation_signals >= 2 or avg_score < 35:
            verdict = "likely_manipulated"
        elif manipulation_signals == 0 and avg_score >= 65:
            verdict = "likely_authentic"
        else:
            verdict = "inconclusive"

        return {
            "verdict": verdict,
            "confidence": 30.0,  # Low confidence — no LLM synthesis
            "explanation_en": (
                f"Based on automated analysis (average integrity score: {avg_score:.0f}/100), "
                f"this media is assessed as '{verdict}'. "
                f"{manipulation_signals} manipulation signal(s) were detected across "
                f"metadata, visual, and audio analysis."
            ),
            "explanation_ur": (
                f"خودکار تجزیہ کی بنیاد پر (اوسط سالمیت اسکور: {avg_score:.0f}/100)، "
                f"یہ میڈیا '{verdict}' کے طور پر جانچا گیا ہے۔ "
                f"{manipulation_signals} مینوپولیشن سگنل پائے گئے۔"
            ),
            "signals": [],
            "authenticity_score": int(avg_score),
            "sources": [],
        }
