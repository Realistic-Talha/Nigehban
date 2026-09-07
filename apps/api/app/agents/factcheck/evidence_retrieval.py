"""EvidenceRetrievalAgent — gather web evidence for a claim."""

import json
import logging
from typing import Any

from app.agents.base import BaseAgent
from app.services.search import search_service

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompt for relevance ranking
# ---------------------------------------------------------------------------

RANKING_PROMPT = """\
You are an evidence relevance assessor for Nigehban, a Pakistani fact-checking platform.

Given a claim and a list of web search results, rank each result by relevance to verifying
the claim. Assign a relevance_score from 0.0 (completely irrelevant) to 1.0 (directly
addresses the claim).

Return ONLY valid JSON (no markdown fences):
{
  "ranked_sources": [
    {
      "title": "source title",
      "url": "source URL",
      "snippet": "source snippet",
      "relevance_score": 0.85,
      "relevance_reason": "Brief reason why this score was assigned"
    }
  ],
  "summary": "One-sentence summary of what the evidence collectively suggests"
}

Rules:
- Higher score = more directly relevant to verifying the specific claim.
- Prefer sources from reputable fact-checking organizations, government data, and major news outlets.
- Penalize sources that only tangentially mention the claim's entities.
"""


# ---------------------------------------------------------------------------
# Agent implementation
# ---------------------------------------------------------------------------

class EvidenceRetrievalAgent(BaseAgent):
    """Retrieve and rank web evidence relevant to a factual claim.

    This agent:
    1. Formulates search queries from the claim and its entities.
    2. Executes web searches via the search service.
    3. Uses Haiku to rank and summarize the relevance of results.
    """

    name: str = "evidence_retrieval"
    model_tier: str = "haiku"
    timeout: float = 30.0

    async def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Gather and rank evidence for the given claim.

        Args:
            input_data: Dict with keys:
                - claim (str | dict): The claim text or claim extraction output.
                - language (str): Language code.

        Returns:
            Dict with keys:
                - sources (list): Ranked source objects with relevance scores.
                - evidence_summary (str): Summary of evidence.
                - confidence (int): Retrieval confidence 0–100.
        """
        # Normalize claim input — may be a string or a dict from ClaimExtractionAgent
        claim_input = input_data.get("claim", "")
        language = input_data.get("language", "en")

        if isinstance(claim_input, dict):
            primary_claim = claim_input.get("primary_claim", "")
            claims_list = claim_input.get("claims", [])
            entities: list[str] = []
            for c in claims_list:
                if isinstance(c, dict):
                    entities.extend(c.get("entities", []))
        else:
            primary_claim = str(claim_input)
            claims_list = [{"claim_text": primary_claim}]
            entities = []

        if not primary_claim:
            return {
                "sources": [],
                "evidence_summary": "No claim provided for evidence retrieval.",
                "confidence": 0,
            }

        try:
            # L3 evidence cache
            from app.cache.layers import content_hash, evidence_cache
            claim_hash = content_hash(primary_claim)
            cached_evidence = await evidence_cache.get(claim_hash)
            if cached_evidence:
                return cached_evidence

            # Step 1: Build search queries
            queries = self._build_queries(primary_claim, entities, claims_list)

            # Step 2: Execute searches (deduplicate by URL)
            all_results = []
            seen_urls: set[str] = set()

            for query in queries[:3]:  # Limit to 3 queries to stay within budget
                results = await search_service.search(query, num_results=5)
                for r in results:
                    if r.url not in seen_urls:
                        seen_urls.add(r.url)
                        all_results.append(r.to_dict())

            if not all_results:
                return {
                    "sources": [],
                    "evidence_summary": "No search results found.",
                    "confidence": 10,
                }

            # Step 3: Use Haiku to rank and summarize relevance
            ranking_response = await self.call_llm(
                system_prompt=RANKING_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": (
                            f"Claim: {primary_claim}\n\n"
                            f"Search results:\n{json.dumps(all_results, indent=2)}\n\n"
                            f"Rank these results by relevance to verifying the claim."
                        ),
                    },
                ],
                max_tokens=1536,
            )

            ranked = ranking_response.get("json")
            if ranked and isinstance(ranked, dict):
                sources = ranked.get("ranked_sources", all_results)
                summary = ranked.get("summary", "")
            else:
                # Fallback: use raw results without LLM ranking
                sources = all_results
                summary = f"Found {len(sources)} sources (unranked due to LLM parsing failure)."

            # Ensure each source has relevance_score
            for src in sources:
                if "relevance_score" not in src:
                    src["relevance_score"] = 0.5

            # Sort by relevance descending
            sources.sort(key=lambda s: s.get("relevance_score", 0), reverse=True)

            # Confidence based on number and quality of sources
            top_scores = [s.get("relevance_score", 0) for s in sources[:5]]
            avg_relevance = sum(top_scores) / max(len(top_scores), 1)
            confidence = int(min(95, avg_relevance * 60 + len(sources) * 5))

            result_payload = {
                "sources": sources[:10],
                "evidence_summary": summary,
                "confidence": max(0, min(100, confidence)),
            }
            await evidence_cache.set(claim_hash, result_payload)
            return result_payload

        except Exception:
            logger.exception("EvidenceRetrievalAgent failed")
            return {
                "sources": [],
                "evidence_summary": "Evidence retrieval failed.",
                "confidence": 0,
            }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_queries(
        primary_claim: str,
        entities: list[str],
        claims_list: list[dict],
    ) -> list[str]:
        """Build search queries from the claim and its entities."""
        queries: list[str] = []

        # Query 1: The claim itself (truncated for search engine limits)
        claim_query = primary_claim[:200]
        queries.append(claim_query)

        # Query 2: Claim + key entity
        if entities:
            top_entities = entities[:3]
            queries.append(f"{claim_query[:100]} {' '.join(top_entities)}")

        # Query 3: Fact-check oriented query
        queries.append(f"fact check: {claim_query[:150]}")

        # Query 4: Individual claim texts if multiple claims
        for claim_obj in claims_list[1:3]:
            if isinstance(claim_obj, dict) and claim_obj.get("claim_text"):
                queries.append(claim_obj["claim_text"][:200])

        return queries
