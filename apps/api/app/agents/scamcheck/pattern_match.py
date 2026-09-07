"""PatternMatchAgent — match input against known scam patterns via embedding similarity."""

import logging
from typing import Any

from app.agents.base import BaseAgent
from app.services.embeddings import embedding_service

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_TOP_K = 5
SIMILARITY_THRESHOLD = 0.82


class PatternMatchAgent(BaseAgent):
    """Match input text against a database of known scam patterns.

    Uses embedding similarity (pgvector cosine distance) to find the most
    similar known scam patterns. This is primarily an embedding-based agent
    with minimal LLM usage.
    """

    name: str = "pattern_match"
    model_tier: str = "haiku"
    timeout: float = 15.0

    async def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Find similar known scam patterns for the given text.

        Args:
            input_data: Dict with keys:
                - text (str): The text to match against scam patterns.
                - language (str): Language code (for future filtering).

        Returns:
            Dict with keys:
                - matches (list): List of matching pattern objects.
                - best_match_similarity (float): Highest similarity score.
                - confidence (int): Match confidence 0–100.
        """
        text = input_data.get("text", "")

        if not text or not text.strip():
            return {
                "matches": [],
                "best_match_similarity": 0.0,
                "confidence": 0,
            }

        try:
            # Step 1: Generate embedding for the input text
            embedding = await embedding_service.generate_embedding(text)

            # Step 2: Query scam_patterns table
            similar_rows = await embedding_service.similarity_search(
                embedding,
                "scam_patterns",
                limit=DEFAULT_TOP_K,
                threshold=0.5,  # Broad retrieval; we filter below
            )

            if not similar_rows:
                return {
                    "matches": [],
                    "best_match_similarity": 0.0,
                    "confidence": 40,  # Moderately confident no match exists
                }

            # Step 3: Process and filter results
            matches: list[dict[str, Any]] = []
            best_similarity = 0.0

            for row in similar_rows:
                similarity = float(row.get("similarity", 0.0))

                match_record = {
                    "pattern_id": str(row.get("id", "")),
                    "scam_type": row.get("scam_type", "unknown"),
                    "description": row.get("description_en", ""),
                    "description_ur": row.get("description_ur", ""),
                    "similarity": round(similarity, 4),
                    "times_reported": row.get("times_reported", 0),
                }
                matches.append(match_record)

                if similarity > best_similarity:
                    best_similarity = similarity

            # Sort by similarity descending
            matches.sort(key=lambda m: m["similarity"], reverse=True)

            # Determine confidence
            if best_similarity >= SIMILARITY_THRESHOLD:
                confidence = int(min(95, best_similarity * 100))
            elif best_similarity >= 0.6:
                confidence = int(best_similarity * 70)
            else:
                confidence = int(best_similarity * 40)

            return {
                "matches": matches,
                "best_match_similarity": round(best_similarity, 4),
                "confidence": max(0, min(100, confidence)),
            }

        except Exception:
            logger.exception("PatternMatchAgent failed")
            return {
                "matches": [],
                "best_match_similarity": 0.0,
                "confidence": 0,
                "error": "Pattern matching failed",
            }
