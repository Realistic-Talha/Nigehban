"""JSON parsing helpers for LLM structured output."""

import json
import re
from typing import Any


_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def parse_json_from_text(text: str) -> Any | None:
    """Extract and parse JSON from LLM text, stripping markdown fences."""
    if not text:
        return None
    cleaned = _FENCE_RE.sub("", text.strip()).strip()
    try:
        return json.loads(cleaned)
    except (json.JSONDecodeError, ValueError):
        # Try to find first JSON object in text
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(cleaned[start:end + 1])
            except (json.JSONDecodeError, ValueError):
                return None
    return None


def build_llm_response(text: str) -> dict[str, Any]:
    """Build standard response dict with parsed JSON."""
    return {
        "text": text,
        "json": parse_json_from_text(text),
        "tool_calls": [],
        "stop_reason": "end_turn",
    }
