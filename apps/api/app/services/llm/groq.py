"""Groq cloud LLM provider (free tier dev fallback)."""

import asyncio
import logging
from typing import Any

import httpx

from app.core.config import settings
from app.services.llm.base import LLMProvider
from app.services.llm.parsing import build_llm_response

logger = logging.getLogger(__name__)

_GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
# Model IDs must match the live Groq catalog for this account (deprecated Llama 3.x → 404).
_MODEL_FAST = "openai/gpt-oss-20b"
_MODEL_REASONING = "qwen/qwen3.8-27b"
_MAX_RETRIES = 4


class GroqProvider(LLMProvider):
    """OpenAI-compatible Groq API."""

    async def call_haiku(
        self,
        system_prompt: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        return await self._complete(_MODEL_FAST, system_prompt, messages, max_tokens, temperature)

    async def call_sonnet(
        self,
        system_prompt: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 2048,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        try:
            return await self._complete(
                _MODEL_REASONING, system_prompt, messages, max_tokens, temperature
            )
        except httpx.HTTPStatusError as exc:
            # Free-tier rate limits on the reasoning model — fall back to fast tier.
            if exc.response is not None and exc.response.status_code == 429:
                logger.warning("Groq reasoning model rate-limited; falling back to %s", _MODEL_FAST)
                return await self._complete(
                    _MODEL_FAST, system_prompt, messages, max_tokens, temperature
                )
            raise

    async def _complete(
        self,
        model: str,
        system_prompt: str,
        messages: list[dict[str, Any]],
        max_tokens: int,
        temperature: float,
    ) -> dict[str, Any]:
        payload = {
            "model": model,
            "messages": [{"role": "system", "content": system_prompt}, *messages],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        headers = {
            "Authorization": f"Bearer {settings.GROQ_API_KEY}",
            "Content-Type": "application/json",
        }
        last_exc: Exception | None = None
        async with httpx.AsyncClient(timeout=60.0) as client:
            for attempt in range(_MAX_RETRIES):
                try:
                    resp = await client.post(_GROQ_URL, json=payload, headers=headers)
                    if resp.status_code == 429:
                        retry_after = resp.headers.get("retry-after")
                        delay = float(retry_after) if retry_after and retry_after.isdigit() else (2 ** attempt)
                        logger.warning(
                            "Groq 429 on %s (attempt %d/%d); sleeping %.1fs",
                            model,
                            attempt + 1,
                            _MAX_RETRIES,
                            delay,
                        )
                        await asyncio.sleep(delay)
                        continue
                    resp.raise_for_status()
                    data = resp.json()
                    text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    return build_llm_response(text)
                except httpx.HTTPStatusError as exc:
                    last_exc = exc
                    if exc.response is not None and exc.response.status_code == 429:
                        continue
                    raise
            if last_exc:
                raise last_exc
            raise httpx.HTTPStatusError(
                "Groq rate limited after retries",
                request=httpx.Request("POST", _GROQ_URL),
                response=httpx.Response(429),
            )
