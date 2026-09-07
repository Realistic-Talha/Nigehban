"""ClaimExtractionAgent — extract structured claims from user input."""

import json
import logging
from typing import Any

from app.agents.base import BaseAgent

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are a claim extraction specialist for Nigehban, a Pakistani fact-checking platform.

Your job: Extract the core factual claim(s) from the user's message. The input may be in
English, Urdu (Roman or script), or a mix. Focus on verifiable factual assertions —
ignore opinions, questions, and commentary.

Return ONLY valid JSON (no markdown fences) with this exact structure:
{
  "claims": [
    {
      "claim_text": "The extracted claim in English (translate if needed)",
      "original_text": "The claim as written in the original language",
      "entities": ["list of named entities: people, organizations, places"],
      "date_references": ["any dates or time periods mentioned"],
      "location_references": ["geographic locations mentioned"],
      "claim_type": "statistic | policy | event | quote | other"
    }
  ],
  "primary_claim": "The single most important/verifiable claim",
  "language_detected": "en | ur | mixed",
  "confidence": 85
}

Rules:
- If no verifiable claim is found, return empty claims list and confidence 0.
- Always translate Urdu claims to English in claim_text, preserve original in original_text.
- Extract ALL distinct claims, not just the first one.
- Entities should be specific: "Imran Khan" not "politician".
- confidence should reflect how clearly the claim can be fact-checked (0-100).
"""


# ---------------------------------------------------------------------------
# Agent implementation
# ---------------------------------------------------------------------------

class ClaimExtractionAgent(BaseAgent):
    """Extract structured factual claims from free-text user input.

    This is the first step in the fact-check pipeline. It parses the user's
    message and returns a structured representation of each verifiable claim
    found, including entities, dates, and locations.
    """

    name: str = "claim_extraction"
    model_tier: str = "haiku"
    timeout: float = 15.0

    async def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Extract claims from the provided text.

        Args:
            input_data: Dict with keys:
                - text (str): The user message to analyze.
                - language (str): Detected language code ("en", "ur", "mixed").

        Returns:
            Dict with keys:
                - claims (list): Extracted claim objects.
                - primary_claim (str): The most verifiable claim.
                - confidence (int): Extraction confidence 0–100.
                - language_detected (str): Detected language.
        """
        text = input_data.get("text", "")
        language = input_data.get("language", "en")

        if not text or not text.strip():
            logger.warning("ClaimExtractionAgent received empty text")
            return {
                "claims": [],
                "primary_claim": "",
                "confidence": 0,
                "language_detected": language,
            }

        try:
            response = await self.call_llm(
                system_prompt=SYSTEM_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": (
                            f"Extract the factual claim(s) from this message. "
                            f"Language context: {language}\n\n"
                            f"Message: {text}"
                        ),
                    },
                ],
                max_tokens=1024,
            )

            parsed = response.get("json")
            if parsed and isinstance(parsed, dict):
                # Normalize confidence to int 0-100
                conf = parsed.get("confidence", 50)
                if isinstance(conf, float):
                    conf = int(conf) if conf <= 100 else int(conf / 100 * 100)
                parsed["confidence"] = max(0, min(100, conf))
                return parsed

            # Fallback: try to extract JSON from raw text
            raw_text = response.get("text", "")
            try:
                parsed = json.loads(raw_text)
                if isinstance(parsed, dict):
                    return parsed
            except (json.JSONDecodeError, ValueError):
                pass

            logger.warning("LLM returned non-JSON response; using fallback extraction")
            return {
                "claims": [{"claim_text": text[:500], "entities": [], "date_references": [],
                            "location_references": [], "claim_type": "other"}],
                "primary_claim": text[:500],
                "confidence": 30,
                "language_detected": language,
            }

        except Exception:
            logger.exception("ClaimExtractionAgent failed")
            return {
                "claims": [],
                "primary_claim": "",
                "confidence": 0,
                "language_detected": language,
                "error": "Extraction failed",
            }
