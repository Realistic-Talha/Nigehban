"""Tests for LLM JSON parsing."""

from app.services.llm.parsing import parse_json_from_text


def test_parse_json_fences():
    raw = '```json\n{"verdict": "false", "confidence": 80}\n```'
    parsed = parse_json_from_text(raw)
    assert parsed["verdict"] == "false"
    assert parsed["confidence"] == 80
