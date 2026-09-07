"""LLM result and provider interface."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class LLMResult:
    """Normalized LLM response."""

    text: str = ""
    json: Any = None
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    stop_reason: str = "unknown"


class LLMProvider:
    """Abstract LLM provider."""

    async def call_haiku(
        self,
        system_prompt: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        raise NotImplementedError

    async def call_sonnet(
        self,
        system_prompt: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 2048,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        raise NotImplementedError

    def _to_dict(self, result: LLMResult) -> dict[str, Any]:
        return {
            "text": result.text,
            "json": result.json,
            "tool_calls": result.tool_calls,
            "stop_reason": result.stop_reason,
        }
