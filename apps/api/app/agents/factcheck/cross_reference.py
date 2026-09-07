"""CrossReferenceAgent — find previously verified claims via embedding similarity."""

import logging
from typing import Any

from app.agents.base import BaseAgent
from app.services.embeddings import embedding_service

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Similarity threshold — claims above this are considered matches
# ---------------------------------------------------------------------------
SIMILARITY_THRESHOLD = 0.90


class CrossReferenceAgent(BaseAgent):
    """Cross-reference a claim against the database of previously verified claims.

    Uses embedding similarity (pgvector cosine distance) to find near-duplicate
    or closely related claims that have already been fact-checked. When a high-
    similarity match is found, the existing verdict can be reused directly.
    """

    name: str = "cross_reference"
    model_tier: str = "haiku"
    timeout: float = 15.0

    async def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Search for similar previously-verified claims.

        Args:
            input_data: Dict with keys:
                - claim (str | dict): The claim text or claim extraction output.
                - language (str): Language code (unused here but accepted for consistency).

        Returns:
            Dict with keys:
                - match_found (bool): Whether a high-similarity match was found.
                - similar_claims (list): List of similar claim records.
                - prior_verdict (str | None): Verdict of the best match, if any.
                - similarity_score (float): Best match similarity (0.0–1.0).
                - confidence (int): Cross-reference confidence 0–100.
        """
        # Normalize claim input
        claim_input = input_data.get("claim", "")
        if isinstance(claim_input, dict):
            claim_text = claim_input.get("primary_claim", "")
        else:
            claim_text = str(claim_input)

        if not claim_text:
            return {
                "match_found": False,
                "similar_claims": [],
                "prior_verdict": None,
                "similarity_score": 0.0,
                "confidence": 0,
            }

        try:
            # Step 1: Generate embedding for the claim
            embedding = await embedding_service.generate_embedding(claim_text)

            # Step 2: Query the claims table for similar entries
            similar_rows = await embedding_service.similarity_search(
                embedding,
                "claims",
                limit=5,
                threshold=0.7,  # Lower threshold for retrieval; we filter strictly below
            )

            if not similar_rows:
                return {
                    "match_found": False,
                    "similar_claims": [],
                    "prior_verdict": None,
                    "similarity_score": 0.0,
                    "confidence": 60,  # Confident that no match exists
                }

            # Step 3: Process results
            similar_claims: list[dict[str, Any]] = []
            best_similarity = 0.0
            best_verdict: str | None = None

            for row in similar_rows:
                similarity = float(row.get("similarity", 0.0))
                claim_record = {
                    "id": str(row.get("id", "")),
                    "title": row.get("title", ""),
                    "verdict": row.get("verdict"),
                    "confidence_score": row.get("confidence_score"),
                    "explanation_en": row.get("explanation_en"),
                    "similarity": round(similarity, 4),
                }
                similar_claims.append(claim_record)

                if similarity > best_similarity:
                    best_similarity = similarity
                    best_verdict = row.get("verdict")

            match_found = best_similarity >= SIMILARITY_THRESHOLD

            # If we have a strong match and a verdict, confidence is high
            if match_found and best_verdict:
                confidence = int(min(95, best_similarity * 100))
            elif match_found:
                # Match found but no prior verdict stored
                confidence = int(best_similarity * 70)
            else:
                # No strong match — moderate confidence in the "no match" conclusion
                confidence = 50

            return {
                "match_found": match_found,
                "similar_claims": similar_claims,
                "prior_verdict": best_verdict if match_found else None,
                "similarity_score": round(best_similarity, 4),
                "confidence": max(0, min(100, confidence)),
            }

        except Exception:
            logger.exception("CrossReferenceAgent failed")
            return {
                "match_found": False,
                "similar_claims": [],
                "prior_verdict": None,
                "similarity_score": 0.0,
                "confidence": 0,
                "error": "Cross-reference search failed",
            }
