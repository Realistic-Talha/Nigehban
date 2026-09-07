"""JudgeAgent — final quality gate that validates and refines draft verdicts."""

import json
from typing import Any

from app.agents.base import BaseAgent

# ---------------------------------------------------------------------------
# System prompt for the Judge
# ---------------------------------------------------------------------------
JUDGE_SYSTEM_PROMPT = """\
You are Nigehban's **Judge Agent** — the final quality gate before a verdict
reaches the user. You receive a draft verdict produced by specialized pipeline
agents and the original user input. Your responsibilities:

## Quality Checks (MUST perform all)

1. **Source Validation**
   - Every claim in the explanation MUST be backed by a cited source.
   - If sources appear fabricated (non-existent URLs, invented organization names,
     made-up studies), REMOVE them and flag the verdict as lower confidence.
   - If no sources are provided, the highest allowed verdict confidence is 60.

2. **Verdict-Explanation Alignment**
   - The verdict label MUST logically match the explanation.
   - e.g. a "true" verdict cannot have an explanation that mostly expresses doubt.
   - If misaligned, correct the verdict to match the explanation's actual conclusion.

3. **Unsupported Claims**
   - The explanation MUST NOT introduce new factual claims not present in the
     pipeline's evidence. If it does, remove or soften them.

4. **Confidence Floor**
   - If the reported confidence is below 50, FORCE the verdict to "unverified"
     (for fact-checks), "needs_caution" (for scam-checks), or "inconclusive"
     (for media-checks).
   - Adjust confidence to a realistic value based on the quality of evidence.

5. **Sensitive Topic Detection**
   - Detect if the content touches on: religion, ethnicity, sectarian issues,
     military/intelligence, political figures, blasphemy-adjacent topics.
   - If sensitive: add `"sensitive_topic": true` to output and reduce confidence
     by 10 points (floor at 20). Add a caution note in the explanation urging
     the user to verify through multiple independent sources.

## Output Format

Respond in **valid JSON** with EXACTLY these keys:

{
  "verdict": "<string — the corrected verdict label>",
  "confidence": <float 0-100>,
  "explanation_en": "<string — clear English explanation, 2-4 sentences>",
  "explanation_ur": "<string — Urdu translation of the explanation, 2-4 sentences>",
  "sources": [
    {"url": "...", "title": "...", "publisher": "..."}
  ],
  "sensitive_topic": <bool>,
  "caution_note": "<string | null — warning if sensitive topic detected>"
}

## Rules
- Never invent sources. If you cannot verify, say so.
- Keep explanations concise and accessible (non-technical language).
- Urdu explanation should be natural Urdu, not machine-translated-feeling.
- For scam verdicts, the explanation should warn about specific red flags.
- For media verdicts, explain what manipulation technique was detected (if any).
"""


class JudgeAgent(BaseAgent):
    """Final quality-control agent that validates, corrects, and formats verdicts."""

    name: str = "judge"
    model_tier: str = "sonnet"
    timeout: float = 60.0

    async def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Validate and refine a draft verdict.

        Expected input_data keys:
            - draft_verdict  : dict — output from the path-specific verdict synthesis
            - original_input : dict — the original user submission
        """
        draft = input_data.get("draft_verdict", {})
        original = input_data.get("original_input", {})

        # Build the judge prompt context
        user_message = self._build_judge_context(draft, original)
        messages = [{"role": "user", "content": user_message}]

        llm_result = await self.call_llm(
            system_prompt=JUDGE_SYSTEM_PROMPT,
            messages=messages,
        )

        # Parse response
        parsed = llm_result.get("json")
        if parsed and isinstance(parsed, dict):
            verdict_output = self._normalize_judge_output(parsed, draft)
            confidence = float(verdict_output.get("confidence", 50.0))
        else:
            # Fallback: pass through draft with minimal validation
            verdict_output = self._fallback_validate(draft)
            confidence = float(verdict_output.get("confidence", 40.0))

        # Enforce hard confidence floor
        if confidence < 50:
            verdict_output = self._apply_confidence_floor(verdict_output)
            confidence = verdict_output["confidence"]

        return {
            "output": verdict_output,
            "confidence": confidence,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_judge_context(draft: dict, original: dict) -> str:
        """Construct a detailed context block for the Judge LLM call."""
        parts: list[str] = []

        # Original input summary
        parts.append("## ORIGINAL USER INPUT")
        if text := original.get("text"):
            parts.append(f"Text: {text[:500]}")
        if url := original.get("source_url"):
            parts.append(f"URL: {url}")
        if media := original.get("media_url"):
            parts.append(f"Media: {media}")

        # Draft verdict
        parts.append("\n## DRAFT VERDICT FROM PIPELINE")
        parts.append(json.dumps(draft, indent=2, ensure_ascii=False, default=str))

        return "\n".join(parts)

    @staticmethod
    def _normalize_judge_output(parsed: dict, draft: dict) -> dict:
        """Ensure the judge output has all required fields."""
        # Inherit sources from draft if judge didn't modify them
        sources = parsed.get("sources")
        if not sources and draft.get("sources"):
            sources = draft["sources"]

        return {
            "verdict": parsed.get("verdict", draft.get("verdict", "unverified")),
            "confidence": float(parsed.get("confidence", draft.get("confidence", 50.0))),
            "explanation_en": parsed.get("explanation_en", draft.get("explanation_en", "")),
            "explanation_ur": parsed.get("explanation_ur", draft.get("explanation_ur", "")),
            "sources": sources or [],
            "sensitive_topic": parsed.get("sensitive_topic", False),
            "caution_note": parsed.get("caution_note"),
        }

    @staticmethod
    def _fallback_validate(draft: dict) -> dict:
        """Minimal validation when LLM JSON parse fails."""
        confidence = float(draft.get("confidence", 40.0))
        return {
            "verdict": draft.get("verdict", "unverified"),
            "confidence": confidence,
            "explanation_en": draft.get("explanation_en", draft.get("explanation", "")),
            "explanation_ur": draft.get("explanation_ur", ""),
            "sources": draft.get("sources", []),
            "sensitive_topic": False,
            "caution_note": None,
        }

    @staticmethod
    def _apply_confidence_floor(verdict_output: dict) -> dict:
        """Force 'unverified' / 'needs_caution' / 'inconclusive' when confidence < 50."""
        verdict = verdict_output.get("verdict", "")

        # Map to safe fallback verdicts by domain
        safe_verdicts = {
            # Fact-check verdicts
            "true": "unverified",
            "false": "unverified",
            "misleading": "unverified",
            "satire": "unverified",
            # Scam verdicts
            "likely_scam": "needs_caution",
            "likely_safe": "needs_caution",
            # Media verdicts
            "likely_authentic": "inconclusive",
            "likely_manipulated": "inconclusive",
        }

        if verdict in safe_verdicts:
            verdict_output["verdict"] = safe_verdicts[verdict]
        elif verdict not in ("unverified", "needs_caution", "inconclusive"):
            verdict_output["verdict"] = "unverified"

        # Cap confidence at 49
        verdict_output["confidence"] = min(float(verdict_output.get("confidence", 40.0)), 49.0)

        return verdict_output
