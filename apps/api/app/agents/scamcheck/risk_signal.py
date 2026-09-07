"""RiskSignalAgent — detect scam red flags via rule-based heuristics and LLM analysis."""

import logging
import re
from typing import Any

from app.agents.base import BaseAgent

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompt for LLM-based contextual red flag detection
# ---------------------------------------------------------------------------

LLM_ANALYSIS_PROMPT = """\
You are a scam detection analyst for Nigehban, a Pakistani anti-fraud platform.

Analyze the following message for contextual red flags that rule-based systems might miss.
Consider:
- Social engineering tactics (authority impersonation, emotional manipulation)
- Inconsistencies in the narrative
- Language patterns typical of known scam categories (advance fee, phishing, romance,
  investment fraud, lottery/prize scams)
- Cultural context specific to Pakistan (fake SBP/FIA/SECP notices, NADRA scams,
  Ehsaas/Benazir Income Support fraud, fake job offers)

Return ONLY valid JSON (no markdown fences):
{
  "contextual_flags": [
    {
      "type": "Category of the red flag",
      "severity": "high | medium | low",
      "description": "Brief explanation of why this is suspicious"
    }
  ],
  "scam_likelihood": "high | medium | low",
  "scam_type_guess": "Most likely scam category or null",
  "analysis_notes": "Brief overall assessment"
}

If the message appears legitimate, return empty contextual_flags and "low" scam_likelihood.
"""


# ---------------------------------------------------------------------------
# Rule-based detection patterns
# ---------------------------------------------------------------------------

# Urgency language patterns (English + Urdu Roman + Urdu script)
URGENCY_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\burgent(ly)?\b", re.IGNORECASE),
    re.compile(r"\blast chance\b", re.IGNORECASE),
    re.compile(r"\blimited (time|offer|period)\b", re.IGNORECASE),
    re.compile(r"\bact(ion)? (required|needed|now|immediately)\b", re.IGNORECASE),
    re.compile(r"\bexpire[sd]?\b", re.IGNORECASE),
    re.compile(r"\bimmediate(ly)?\b", re.IGNORECASE),
    re.compile(r"\bdeadline\b", re.IGNORECASE),
    re.compile(r"\bforfeit(ure)?\b", re.IGNORECASE),
    # Urdu Roman
    re.compile(r"\bforan\b", re.IGNORECASE),
    re.compile(r"\bjaldi\b", re.IGNORECASE),
    re.compile(r"\bfouri\b", re.IGNORECASE),
    re.compile(r"\baakhir(?:i)? (?:mauka|chance)\b", re.IGNORECASE),
    # Urdu script
    re.compile(r"فوری"),
    re.compile(r"جلدی"),
    re.compile(r"آخری موقع"),
    re.compile(r"فوراً"),
]

# Money request patterns
MONEY_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bsend (me |us )?money\b", re.IGNORECASE),
    re.compile(r"\btransfer (the )?(fund|amount|money)\b", re.IGNORECASE),
    re.compile(r"\bOTP\b"),
    re.compile(r"\bPIN (code|number)?\b", re.IGNORECASE),
    re.compile(r"\bbank (account|detail|information)\b", re.IGNORECASE),
    re.compile(r"\badvance (payment|fee|charge)\b", re.IGNORECASE),
    re.compile(r"\bprocessing fee\b", re.IGNORECASE),
    re.compile(r"\bregistration fee\b", re.IGNORECASE),
    re.compile(r"\bpay(ment)? (of |to )?(\d+|Rs|PKR|USD|\$)\b", re.IGNORECASE),
    re.compile(r"\b(?:Rs|PKR|پاکستانی روپے)\s*\d{3,}\b", re.IGNORECASE),
    re.compile(r"\beasy(?:paisa|paisa)\b", re.IGNORECASE),
    re.compile(r"\bjazzcash\b", re.IGNORECASE),
    # Urdu
    re.compile(r"پیسے بھیج"),
    re.compile(r"بینک اکاؤنٹ"),
    re.compile(r"ایڈوانس فیس"),
]

# Impersonation patterns
IMPERSONATION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bSBP\b"),
    re.compile(r"\bState Bank (of Pakistan)?\b", re.IGNORECASE),
    re.compile(r"\bFIA\b"),
    re.compile(r"\bNADRA\b"),
    re.compile(r"\bSECP\b"),
    re.compile(r"\bFBR\b"),
    re.compile(r"\b政府|government (official|officer|department)\b", re.IGNORECASE),
    re.compile(r"\bbank (manager|officer|representative|official)\b", re.IGNORECASE),
    re.compile(r"\b(?:chairman|director|CEO) (?:of|from)\b", re.IGNORECASE),
    re.compile(r"\b(?:Ehsaas|Benazir|BISP)\b", re.IGNORECASE),
    re.compile(r"\b(?:Prime Minister|PM) (?:fund|scheme|program)\b", re.IGNORECASE),
    re.compile(r"\b(?:army|military|ISI|police) (?:officer|official|headquarters)\b", re.IGNORECASE),
    # Urdu
    re.compile(r"اسٹیٹ بینک"),
    re.compile(r"حکومت"),
    re.compile(r"بینک مینیجر"),
]

# Suspicious link patterns
LINK_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"https?://bit\.ly/"),
    re.compile(r"https?://tinyurl\.com/"),
    re.compile(r"https?://t\.co/"),
    re.compile(r"https?://(?:goo\.gl|is\.gd|ow\.ly|buff\.ly)/"),
    re.compile(r"https?://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"),  # IP-based URLs
    re.compile(r"https?://[^\s]*\.(xyz|tk|ml|ga|cf|gq|buzz|top|click)\b"),  # Suspicious TLDs
]

# Pressure / secrecy tactics
PRESSURE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bdon'?t tell (anyone|anybody|your family|your parents)\b", re.IGNORECASE),
    re.compile(r"\bkeep (this |it )?secret\b", re.IGNORECASE),
    re.compile(r"\bonly for you\b", re.IGNORECASE),
    re.compile(r"\bspecial (offer|deal|opportunity)\b", re.IGNORECASE),
    re.compile(r"\bexclusive(ly)?\b", re.IGNORECASE),
    re.compile(r"\bdo not share\b", re.IGNORECASE),
    re.compile(r"\bconfidential\b", re.IGNORECASE),
    # Urdu
    re.compile(r"کسی کو نہ بتائ"),
    re.compile(r"خفیہ"),
    re.compile(r"صرف آپ کے لیے"),
]


# ---------------------------------------------------------------------------
# Helper: run a set of regex patterns against text
# ---------------------------------------------------------------------------

def _detect_patterns(
    text: str,
    patterns: list[re.Pattern[str]],
    flag_type: str,
    severity: str,
) -> list[dict[str, str]]:
    """Return a list of red-flag dicts for each pattern that matches."""
    flags: list[dict[str, str]] = []
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            flags.append({
                "type": flag_type,
                "severity": severity,
                "description": f"Detected '{match.group()}' — matches {flag_type} pattern.",
            })
            break  # One match per category is enough
    return flags


# ---------------------------------------------------------------------------
# Agent implementation
# ---------------------------------------------------------------------------

class RiskSignalAgent(BaseAgent):
    """Detect scam red flags using rule-based heuristics and LLM analysis.

    Combines fast regex-based detection with contextual LLM analysis to produce
    a comprehensive risk assessment of the input text.
    """

    name: str = "risk_signal"
    model_tier: str = "haiku"
    timeout: float = 20.0

    async def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Analyze text for scam risk signals.

        Args:
            input_data: Dict with keys:
                - text (str): The text to analyze.
                - language (str): Language code.

        Returns:
            Dict with keys:
                - red_flags (list): Red flag objects with type, severity, description.
                - risk_score (int): Overall risk score 0–100.
                - confidence (int): Analysis confidence 0–100.
        """
        text = input_data.get("text", "")
        language = input_data.get("language", "en")

        if not text or not text.strip():
            return {
                "red_flags": [],
                "risk_score": 0,
                "confidence": 0,
            }

        try:
            # Step 1: Rule-based detection
            rule_flags = self._rule_based_detection(text)

            # Step 2: LLM contextual analysis
            llm_flags, scam_type_guess = await self._llm_analysis(text, language)

            # Step 3: Combine and deduplicate
            all_flags = rule_flags + llm_flags
            all_flags = self._deduplicate_flags(all_flags)

            # Step 4: Calculate risk score
            risk_score = self._calculate_risk_score(all_flags)

            # Confidence based on signal density
            confidence = min(95, 40 + len(all_flags) * 10 + (risk_score // 5))
            confidence = max(0, min(100, confidence))

            return {
                "red_flags": all_flags,
                "risk_score": risk_score,
                "confidence": confidence,
                "scam_type_guess": scam_type_guess,
            }

        except Exception:
            logger.exception("RiskSignalAgent failed")
            return {
                "red_flags": [],
                "risk_score": 0,
                "confidence": 0,
                "error": "Risk signal analysis failed",
            }

    # ------------------------------------------------------------------
    # Rule-based detection
    # ------------------------------------------------------------------

    @staticmethod
    def _rule_based_detection(text: str) -> list[dict[str, str]]:
        """Run all rule-based pattern checks against the text."""
        flags: list[dict[str, str]] = []

        flags.extend(
            _detect_patterns(text, URGENCY_PATTERNS, "urgency_language", "high")
        )
        flags.extend(
            _detect_patterns(text, MONEY_PATTERNS, "money_request", "high")
        )
        flags.extend(
            _detect_patterns(text, IMPERSONATION_PATTERNS, "impersonation", "high")
        )
        flags.extend(
            _detect_patterns(text, LINK_PATTERNS, "suspicious_links", "medium")
        )
        flags.extend(
            _detect_patterns(text, PRESSURE_PATTERNS, "pressure_tactics", "high")
        )

        return flags

    # ------------------------------------------------------------------
    # LLM analysis
    # ------------------------------------------------------------------

    async def _llm_analysis(
        self, text: str, language: str,
    ) -> tuple[list[dict[str, str]], str | None]:
        """Use Haiku to detect contextual red flags not caught by rules."""
        try:
            response = await self.call_llm(
                system_prompt=LLM_ANALYSIS_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": (
                            f"Analyze this message for scam indicators. "
                            f"Language: {language}\n\n"
                            f"Message: {text}"
                        ),
                    },
                ],
                max_tokens=1024,
            )

            parsed = response.get("json")
            if parsed and isinstance(parsed, dict):
                flags = parsed.get("contextual_flags", [])
                scam_type = parsed.get("scam_type_guess")
                return flags, scam_type

            return [], None

        except Exception:
            logger.warning("LLM contextual analysis failed, continuing with rule-based only")
            return [], None

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------

    @staticmethod
    def _calculate_risk_score(flags: list[dict[str, str]]) -> int:
        """Calculate a 0–100 risk score from the detected red flags."""
        if not flags:
            return 0

        score = 0
        severity_weights = {"high": 25, "medium": 15, "low": 5}

        for flag in flags:
            severity = flag.get("severity", "low")
            score += severity_weights.get(severity, 5)

        return max(0, min(100, score))

    @staticmethod
    def _deduplicate_flags(flags: list[dict[str, str]]) -> list[dict[str, str]]:
        """Remove duplicate red flags based on type."""
        seen_types: set[str] = set()
        unique: list[dict[str, str]] = []
        for flag in flags:
            key = flag.get("type", "")
            if key not in seen_types:
                seen_types.add(key)
                unique.append(flag)
        return unique
