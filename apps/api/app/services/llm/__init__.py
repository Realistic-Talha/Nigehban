"""LLM service factory and backward-compatible facade."""

from typing import Any

from app.core.config import settings
from app.services.llm.base import LLMProvider

_provider: LLMProvider | None = None


def get_llm_provider() -> LLMProvider:
    """Return configured LLM provider singleton."""
    global _provider
    if _provider is None:
        provider = settings.LLM_PROVIDER.lower().strip()
        if provider == "mock" and settings.ENVIRONMENT.lower() == "prod":
            raise RuntimeError(
                "LLM_PROVIDER=mock is banned in ENVIRONMENT=prod. "
                "Use groq, anthropic, or ollama."
            )
        match provider:
            case "ollama":
                from app.services.llm.ollama import OllamaProvider

                _provider = OllamaProvider()
            case "groq":
                from app.services.llm.groq import GroqProvider

                _provider = GroqProvider()
            case "anthropic":
                from app.services.llm.anthropic import AnthropicProvider

                _provider = AnthropicProvider()
            case "mock":
                from app.services.llm.mock import MockLLMProvider

                _provider = MockLLMProvider()
            case _:
                from app.services.llm.ollama import OllamaProvider

                _provider = OllamaProvider()
    return _provider


class LLMService:
    """Facade matching original llm_service interface for BaseAgent."""

    async def call_haiku(
        self,
        system_prompt: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        return await get_llm_provider().call_haiku(
            system_prompt, messages, tools, max_tokens, temperature
        )

    async def call_sonnet(
        self,
        system_prompt: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 2048,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        return await get_llm_provider().call_sonnet(
            system_prompt, messages, tools, max_tokens, temperature
        )


llm_service = LLMService()
