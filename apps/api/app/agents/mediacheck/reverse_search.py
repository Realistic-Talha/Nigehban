"""ReverseSearchAgent — Hamming near-dupe provenance."""

from typing import Any

from app.agents.base import BaseAgent
from app.engines.provenance import run_provenance_engine


class ReverseSearchAgent(BaseAgent):
    name: str = "reverse_search"
    model_tier: str = "haiku"
    timeout: float = 30.0

    async def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        result = await run_provenance_engine(input_data.get("media_url", ""))
        out = {
            "matches": result.features.get("matches") or [],
            "match_found": bool(result.features.get("match_found")),
            "phash": result.features.get("phash"),
            "file_hash": result.features.get("file_hash"),
            "engine": result.to_dict(),
        }
        return {"output": out, "confidence": 80 if out["match_found"] else 50}
