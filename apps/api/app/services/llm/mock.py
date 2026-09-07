"""Mock LLM provider for CI and offline development."""

import json
from typing import Any

from app.services.llm.base import LLMProvider


class MockLLMProvider(LLMProvider):
    """Deterministic responses without external API calls."""

    async def call_haiku(
        self,
        system_prompt: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        return self._mock_response(system_prompt, messages, fast=True)

    async def call_sonnet(
        self,
        system_prompt: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 2048,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        return self._mock_response(system_prompt, messages, fast=False)

    def _mock_response(
        self,
        system_prompt: str,
        messages: list[dict[str, Any]],
        fast: bool,
    ) -> dict[str, Any]:
        user_text = ""
        for msg in messages:
            if msg.get("role") == "user":
                user_text = str(msg.get("content", ""))

        # Intake classifier
        if "intake classifier" in system_prompt.lower():
            payload = {
                "input_type": "text",
                "language": "en",
                "path": "scamcheck" if "otp" in user_text.lower() or "loan" in user_text.lower() else "factcheck",
                "extracted_text": None,
            }
        elif "judge" in system_prompt.lower():
            payload = {
                "verdict": "needs_caution",
                "confidence": 55,
                "explanation_en": "Mock judge explanation for testing.",
                "explanation_ur": "ٹیسٹ کے لیے مک جج کی وضاحت۔",
                "sources": [],
                "sensitive_topic": False,
                "caution_note": None,
            }
        elif "scam" in system_prompt.lower() or "risk" in system_prompt.lower():
            payload = {
                "verdict": "likely_scam",
                "confidence": 75,
                "explanation_en": "Mock scam analysis detected common red flags.",
                "explanation_ur": "مک تجزیہ میں عام سرخ نشانات پائے گئے۔",
                "red_flags": ["urgency_language"],
            }
        elif "fact" in system_prompt.lower() or "claim" in system_prompt.lower():
            payload = {
                "verdict": "unverified",
                "confidence": 45,
                "explanation_en": "Mock fact-check: insufficient evidence in test mode.",
                "explanation_ur": "مک فیکٹ چیک: ٹیسٹ موڈ میں ناکافی شواہد۔",
                "sources": [],
                "category": "other",
            }
        else:
            payload = {"summary": "mock", "confidence": 50}

        text = json.dumps(payload)
        return {
            "text": text,
            "json": payload,
            "tool_calls": [],
            "stop_reason": "end_turn",
        }
