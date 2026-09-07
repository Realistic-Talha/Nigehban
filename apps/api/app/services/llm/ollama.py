"""Ollama local LLM provider."""

import logging
from typing import Any

import httpx

from app.core.config import settings
from app.services.llm.base import LLMProvider
from app.services.llm.parsing import build_llm_response

logger = logging.getLogger(__name__)


class OllamaProvider(LLMProvider):
    """Chat completions via Ollama HTTP API."""

    def __init__(self) -> None:
        self.base_url = settings.OLLAMA_BASE_URL.rstrip("/")

    async def call_haiku(
        self,
        system_prompt: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        return await self._chat(
            settings.OLLAMA_MODEL_FAST,
            system_prompt,
            messages,
            max_tokens,
            temperature,
        )

    async def call_sonnet(
        self,
        system_prompt: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 2048,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        return await self._chat(
            settings.OLLAMA_MODEL_REASONING,
            system_prompt,
            messages,
            max_tokens,
            temperature,
        )

    async def _chat(
        self,
        model: str,
        system_prompt: str,
        messages: list[dict[str, Any]],
        max_tokens: int,
        temperature: float,
    ) -> dict[str, Any]:
        ollama_messages = [{"role": "system", "content": system_prompt}]
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if isinstance(content, list):
                content = str(content)
            ollama_messages.append({"role": role, "content": content})

        payload = {
            "model": model,
            "messages": ollama_messages,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(f"{self.base_url}/api/chat", json=payload)
                resp.raise_for_status()
                data = resp.json()
                text = data.get("message", {}).get("content", "")
                return build_llm_response(text)
        except Exception as exc:
            logger.error("Ollama call failed for model %s: %s", model, exc)
            raise

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                return resp.status_code == 200
        except Exception:
            return False
