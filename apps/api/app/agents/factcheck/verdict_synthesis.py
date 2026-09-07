"""FactCheckVerdictAgent — synthesize a final fact-check verdict from evidence and cross-references."""

import json
import logging
from typing import Any

from app.agents.base import BaseAgent

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are the verdict synthesis engine for Nigehban, a Pakistani fact-checking platform.

Your task: Produce a fact-check verdict based on the claim, gathered evidence, and
cross-reference data. You must be rigorous, transparent, and bilingual.

## Verdict Categories (choose exactly one):
- **true**: The claim is fully supported by credible evidence.
- **false**: The claim is directly contradicted by credible evidence.
- **misleading**: The claim contains elements of truth but omits critical context or
  presents facts in a way that creates a false impression.
- **satire**: The claim originates from a satirical source and was not intended as factual.
- **unverified**: Insufficient credible evidence to confirm or refute the claim. DEFAULT
  when uncertain — never guess.

## Rules:
1. NEVER fabricate sources, statistics, or quotes. Only reference the evidence provided.
2. Always default to "unverified" when evidence is insufficient or conflicting.
3. Cite the sources provided in the evidence. Reference them by title and URL.
4. Write explanations in BOTH English and Urdu. The Urdu explanation should be natural,
   not a word-for-word translation. Use clear, simple language accessible to a general
   Pakistani audience.
5. Assign a category from: politics, health, economy, technology, religion, social,
   crime, education, environment, other.
6. confidence must be 0-100 reflecting how confident you are in this verdict.

## Return ONLY valid JSON (no markdown fences):
{
  "verdict": "true | false | misleading | satire | unverified",
  "confidence": 75,
  "explanation_en": "Detailed English explanation with source citations...",
  "explanation_ur": "تفصیلی اردو وضاحت...",
  "sources": [
    {"title": "Source Title", "url": "https://...", "snippet": "Relevant excerpt"}
  ],
  "category": "politics | health | economy | technology | religion | social | crime | education | environment | other"
}
"""


# ---------------------------------------------------------------------------
# Agent implementation
# ---------------------------------------------------------------------------

class FactVerdictSynthesisAgent(BaseAgent):
    """Synthesize a fact-check verdict from claim, evidence, and cross-reference data.

    This is the final step in the fact-check pipeline. It uses Sonnet (the
    reasoning model) to weigh evidence, check for contradictions, and produce
    a transparent, bilingual verdict.
    """

    name: str = "factcheck_verdict"
    model_tier: str = "sonnet"
    timeout: float = 30.0

    async def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Produce a fact-check verdict.

        Args:
            input_data: Dict with keys:
                - claim (str | dict): The claim text or claim extraction output.
                - evidence (dict): Output from EvidenceRetrievalAgent.
                - cross_reference (dict): Output from CrossReferenceAgent.
                - language (str): Language code for the user's original message.

        Returns:
            Dict with keys:
                - verdict (str): One of the five verdict categories.
                - confidence (int): 0–100.
                - explanation_en (str): English explanation.
                - explanation_ur (str): Urdu explanation.
                - sources (list): Cited sources.
                - category (str): Claim category.
        """
        # Normalize claim
        claim_input = input_data.get("claim", "")
        if isinstance(claim_input, dict):
            claim_text = claim_input.get("primary_claim", "")
        else:
            claim_text = str(claim_input)

        evidence = input_data.get("evidence", {})
        cross_ref = input_data.get("cross_reference", {})
        language = input_data.get("language", "en")

        # ------------------------------------------------------------------
        # Fast path: if cross-reference found a strong match with a verdict
        # ------------------------------------------------------------------
        if cross_ref.get("match_found") and cross_ref.get("prior_verdict"):
            logger.info(
                "Cross-reference match found (similarity=%.3f), reusing verdict: %s",
                cross_ref.get("similarity_score", 0),
                cross_ref.get("prior_verdict"),
            )
            # Still run LLM for bilingual explanation, but strongly weight the prior verdict
            prompt_addendum = (
                "IMPORTANT: A near-identical claim was previously verified with verdict: "
                f"'{cross_ref['prior_verdict']}' (similarity: {cross_ref.get('similarity_score', 0):.3f}). "
                "Strongly consider reusing this verdict unless the new evidence contradicts it."
            )
        else:
            prompt_addendum = "No prior matching claim was found in the database."

        # Build the user message
        user_content = (
            f"## Claim\n{claim_text}\n\n"
            f"## Language\n{language}\n\n"
            f"## Cross-Reference\n{prompt_addendum}\n\n"
            f"## Evidence\n{json.dumps(evidence, indent=2, default=str)}\n\n"
            f"## Cross-Reference Data\n{json.dumps(cross_ref, indent=2, default=str)}\n\n"
            "Produce your verdict based on the above information."
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

            # Last resort: unverified with LLM raw text as explanation
            logger.warning("VerdictSynthesis could not parse LLM output as JSON")
            return {
                "verdict": "unverified",
                "confidence": 20,
                "explanation_en": raw_text[:500] if raw_text else "Verdict synthesis failed.",
                "explanation_ur": "فیصلہ تیار کرنے میں ناکامی۔",
                "sources": evidence.get("sources", [])[:5],
                "category": "other",
            }

        except Exception:
            logger.exception("FactVerdictSynthesisAgent failed")
            return {
                "verdict": "unverified",
                "confidence": 0,
                "explanation_en": "An error occurred during verdict synthesis.",
                "explanation_ur": "فیصلے کی تیاری میں خرابی پیش آئی۔",
                "sources": [],
                "category": "other",
            }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_verdict(parsed: dict[str, Any]) -> dict[str, Any]:
        """Ensure the parsed LLM output conforms to the expected schema."""
        valid_verdicts = {"true", "false", "misleading", "satire", "unverified"}
        valid_categories = {
            "politics", "health", "economy", "technology", "religion",
            "social", "crime", "education", "environment", "other",
        }

        verdict = str(parsed.get("verdict", "unverified")).lower().strip()
        if verdict not in valid_verdicts:
            verdict = "unverified"

        conf = parsed.get("confidence", 50)
        if isinstance(conf, float) and conf <= 1.0:
            conf = int(conf * 100)
        confidence = max(0, min(100, int(conf)))

        category = str(parsed.get("category", "other")).lower().strip()
        if category not in valid_categories:
            category = "other"

        sources = parsed.get("sources", [])
        if not isinstance(sources, list):
            sources = []

        return {
            "verdict": verdict,
            "confidence": confidence,
            "explanation_en": str(parsed.get("explanation_en", "")),
            "explanation_ur": str(parsed.get("explanation_ur", "")),
            "sources": sources,
            "category": category,
        }
