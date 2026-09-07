"""Base agent abstract class for the multi-agent pipeline."""

import abc
import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from app.core.database import AsyncSessionLocal
from app.core.redis import redis_pool
from app.models.agent_log import AgentLog
from app.services.llm import llm_service

logger = logging.getLogger(__name__)


class BaseAgent(abc.ABC):
    """Abstract base for all Nigehban AI agents.

    Each agent performs a single specialized task (claim extraction, evidence
    retrieval, risk scoring, etc.) and publishes status events to Redis Pub/Sub
    for SSE streaming to the frontend.
    """

    # Override in subclass
    name: str = "base_agent"
    model_tier: str = "haiku"          # "haiku" | "sonnet"
    timeout: float = 30.0              # seconds

    def __init__(self) -> None:
        pass

    # ------------------------------------------------------------------
    # Abstract — implement in subclass
    # ------------------------------------------------------------------

    @abc.abstractmethod
    async def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Execute the agent's core logic.

        Must return a dict with at least ``output`` and ``confidence`` keys.

        Args:
            input_data: Agent-specific input payload.

        Returns:
            Agent-specific output payload.
        """
        ...

    # ------------------------------------------------------------------
    # Public execution wrapper
    # ------------------------------------------------------------------

    async def execute(
        self,
        input_data: dict[str, Any],
        parent_check_id: str,
        parent_check_type: str,
    ) -> dict[str, Any]:
        """Run the agent with timing, Redis status publishing, and logging.

        Parameters
        ----------
        input_data          : agent-specific payload
        parent_check_id     : UUID of the parent check (claim/scam/media)
        parent_check_type   : "claim" | "scam_report" | "media_check"

        Returns
        -------
        dict with keys:
            output     : dict   – the agent's result payload
            confidence : float  – 0-100 confidence score
            _meta      : dict   – latency_ms, agent_name, status, timestamp
        """
        start = time.monotonic()
        logger.info("Agent '%s' started | check=%s", self.name, parent_check_id)

        # 1. Publish "running" status
        await self._publish_status(parent_check_id, status="running")

        try:
            # 2. Execute with timeout enforcement
            result = await asyncio.wait_for(
                self.run(input_data),
                timeout=self.timeout,
            )

            elapsed_ms = int((time.monotonic() - start) * 1000)
            confidence = float(result.get("confidence", 0.0))
            output = result.get("output", result)
            summary = self._summarize_output(output)

            logger.info(
                "Agent '%s' completed in %d ms | confidence=%.1f",
                self.name, elapsed_ms, confidence,
            )

            # 3. Publish "complete" status
            await self._publish_status(parent_check_id, status="complete", output_summary=summary)

            result_payload = {
                "output": output,
                "confidence": confidence,
                "_meta": {
                    "agent_name": self.name,
                    "status": "complete",
                    "latency_ms": elapsed_ms,
                    "parent_check_id": parent_check_id,
                    "parent_check_type": parent_check_type,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            }
            await self._persist_agent_log(parent_check_id, parent_check_type, input_data, result_payload)
            return result_payload

        except asyncio.TimeoutError:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            msg = f"Timeout after {self.timeout}s"
            logger.error("Agent '%s' timed out after %d ms", self.name, elapsed_ms)
            await self._publish_status(parent_check_id, status="error", output_summary=msg)
            err = self._error_result(elapsed_ms, msg, parent_check_id, parent_check_type)
            await self._persist_agent_log(parent_check_id, parent_check_type, input_data, err)
            return err

        except Exception as exc:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            msg = f"{type(exc).__name__}: {exc}"
            logger.exception("Agent '%s' failed after %d ms", self.name, elapsed_ms)
            await self._publish_status(parent_check_id, status="error", output_summary=msg)
            err = self._error_result(elapsed_ms, msg, parent_check_id, parent_check_type)
            await self._persist_agent_log(parent_check_id, parent_check_type, input_data, err)
            return err

    async def _persist_agent_log(
        self,
        parent_check_id: str,
        parent_check_type: str,
        input_data: dict[str, Any],
        result: dict[str, Any],
    ) -> None:
        """Write agent execution record to agent_logs table."""
        meta = result.get("_meta", {})
        output = result.get("output", {})
        input_summary = str(input_data.get("text", ""))[:1024] if input_data else ""
        try:
            async with AsyncSessionLocal() as session:
                log = AgentLog(
                    id=uuid.uuid4(),
                    parent_check_id=uuid.UUID(parent_check_id),
                    parent_check_type=parent_check_type,
                    agent_name=self.name,
                    input_summary=input_summary or None,
                    output_summary=self._summarize_output(output),
                    confidence=float(result.get("confidence", 0)),
                    latency_ms=meta.get("latency_ms"),
                    raw_output=output if isinstance(output, dict) else {"value": str(output)},
                )
                session.add(log)
                await session.commit()
        except Exception:
            logger.warning("Failed to persist agent log for %s", self.name, exc_info=True)


    async def call_llm(
        self,
        system_prompt: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        """Route to the correct model tier (haiku or sonnet)."""
        if self.model_tier == "haiku":
            return await llm_service.call_haiku(
                system_prompt, messages, tools,
                max_tokens=max_tokens or 1024,
            )
        return await llm_service.call_sonnet(
            system_prompt, messages, tools,
            max_tokens=max_tokens or 2048,
        )

    # ------------------------------------------------------------------
    # Redis Pub/Sub helpers
    # ------------------------------------------------------------------

    async def _publish_status(
        self,
        check_id: str,
        status: str,
        output_summary: str = "",
    ) -> None:
        """Publish an agent status event to Redis Pub/Sub for SSE streaming.

        Channel: ``pipeline:{check_id}``
        Payload matches :class:`app.schemas.responses.PipelineEvent`.
        """
        channel = f"pipeline:{check_id}"
        payload = json.dumps({
            "agent_name": self.name,
            "status": status,
            "output_summary": output_summary,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        try:
            client = redis_pool.client
            await client.publish(channel, payload)
        except Exception:
            # Never let a Redis pub/sub failure crash the pipeline
            logger.warning(
                "Failed to publish status to %s (agent=%s, status=%s)",
                channel, self.name, status, exc_info=True,
            )

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def _error_result(
        self,
        elapsed_ms: int,
        error_msg: str,
        parent_check_id: str,
        parent_check_type: str,
    ) -> dict[str, Any]:
        """Return a graceful degradation result when the agent fails."""
        return {
            "output": {"error": error_msg},
            "confidence": 0.0,
            "_meta": {
                "agent_name": self.name,
                "status": "error",
                "latency_ms": elapsed_ms,
                "parent_check_id": parent_check_id,
                "parent_check_type": parent_check_type,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }

    @staticmethod
    def _summarize_output(output: Any, max_len: int = 200) -> str:
        """Create a short human-readable summary of the agent output."""
        if isinstance(output, dict):
            # Prefer explanation fields if present
            for key in ("explanation_en", "explanation", "summary", "verdict"):
                if key in output and isinstance(output[key], str):
                    text = output[key]
                    return text[:max_len] + ("…" if len(text) > max_len else "")
            return str(output)[:max_len]
        return str(output)[:max_len]
