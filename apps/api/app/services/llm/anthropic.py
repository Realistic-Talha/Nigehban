"""Anthropic Claude provider."""

import asyncio
import logging
from typing import Any

import anthropic
from anthropic import AsyncAnthropic

from app.core.config import settings
from app.services.llm.base import LLMProvider
from app.services.llm.parsing import parse_json_from_text

logger = logging.getLogger(__name__)

MODEL_HAIKU = "claude-3-5-haiku-20241022"
MODEL_SONNET = "claude-sonnet-4-20250514"
_MAX_RETRIES = 3
_BACKOFF_BASE = 1.0


class AnthropicProvider(LLMProvider):
    """Anthropic Messages API."""

    def __init__(self) -> None:
        self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    async def call_haiku(
        self,
        system_prompt: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        return await self._call_with_retry(
            MODEL_HAIKU, system_prompt, messages, tools, max_tokens, 10.0, temperature
        )

    async def call_sonnet(
        self,
        system_prompt: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 2048,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        return await self._call_with_retry(
            MODEL_SONNET, system_prompt, messages, tools, max_tokens, 15.0, temperature
        )

    async def _call_with_retry(
        self,
        model: str,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        max_tokens: int,
        timeout: float,
        temperature: float,
    ) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "model": model,
            "system": system,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if tools:
            kwargs["tools"] = tools

        last_error: Exception | None = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                response = await asyncio.wait_for(
                    self.client.messages.create(**kwargs),
                    timeout=timeout,
                )
                return self._parse_response(response)
            except Exception as exc:
                last_error = exc
                logger.warning("Anthropic attempt %d failed: %s", attempt, exc)
                if attempt < _MAX_RETRIES:
                    await asyncio.sleep(_BACKOFF_BASE * (2 ** (attempt - 1)))
        raise RuntimeError(f"Anthropic failed after {_MAX_RETRIES} attempts: {last_error}")

    @staticmethod
    def _parse_response(response: anthropic.types.Message) -> dict[str, Any]:
        text_parts: list[str] = []
        tool_calls: list[dict[str, Any]] = []
        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append({"id": block.id, "name": block.name, "input": block.input})
        text = "\n".join(text_parts).strip()
        return {
            "text": text,
            "json": parse_json_from_text(text),
            "tool_calls": tool_calls,
            "stop_reason": response.stop_reason or "unknown",
        }
