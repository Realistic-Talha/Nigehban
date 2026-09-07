"""Pakistan deterministic scam rules — feature source for meta-learner."""

from __future__ import annotations

import re
from typing import Any

from app.engines.base import EngineResult, Evidence

# Reuse patterns conceptually; keep self-contained for engine isolation.
URGENCY = [
    re.compile(r"\burgent(ly)?\b", re.I),
    re.compile(r"\bforan\b", re.I),
    re.compile(r"\bjaldi\b", re.I),
    re.compile(r"فوری"),
    re.compile(r"جلدی"),
]
MONEY = [
    re.compile(r"\bOTP\b"),
    re.compile(r"\bjazzcash\b", re.I),
    re.compile(r"\beasypaisa\b", re.I),
    re.compile(r"\bPIN\b"),
    re.compile(r"پیسے بھیج"),
]
IMPERSONATION = [
    re.compile(r"\bSBP\b"),
    re.compile(r"\bFIA\b"),
    re.compile(r"\bNADRA\b"),
    re.compile(r"\bBISP\b", re.I),
    re.compile(r"\bEhsaas\b", re.I),
]
LINKS = [
    re.compile(r"https?://bit\.ly/"),
    re.compile(r"https?://tinyurl\.com/"),
    re.compile(r"https?://\d{1,3}(?:\.\d{1,3}){3}"),
    re.compile(r"\.(xyz|tk|ml|ga|cf|gq|click)\b", re.I),
]
PRESSURE = [
    re.compile(r"\bdon'?t tell\b", re.I),
    re.compile(r"\bkeep (this |it )?secret\b", re.I),
    re.compile(r"کسی کو نہ بتائ"),
]


def _hits(text: str, patterns: list[re.Pattern[str]], flag: str, severity: str) -> list[Evidence]:
    out: list[Evidence] = []
    for p in patterns:
        m = p.search(text)
        if m:
            out.append(
                Evidence(
                    type="rule",
                    value=m.group(),
                    signal=flag,
                    detail=f"{severity} severity {flag}",
                )
            )
    return out


def run_pk_rules(text: str) -> EngineResult:
    text = text or ""
    evidence: list[Evidence] = []
    evidence.extend(_hits(text, URGENCY, "urgency_language", "high"))
    evidence.extend(_hits(text, MONEY, "money_otp_request", "high"))
    evidence.extend(_hits(text, IMPERSONATION, "authority_impersonation", "high"))
    evidence.extend(_hits(text, LINKS, "suspicious_link", "medium"))
    evidence.extend(_hits(text, PRESSURE, "secrecy_pressure", "medium"))

    # Score: each high +0.18, medium +0.10, cap 0.98
    score = 0.05
    for e in evidence:
        score += 0.18 if "high" in (e.detail or "") else 0.10
    score = min(0.98, score)
    if not evidence:
        score = 0.08
        return EngineResult(
            engine_id="rules_pk",
            probability=score,
            abstain=True,
            evidence=[],
            features={"flag_count": 0},
            note="No deterministic PK red flags",
        )

    return EngineResult(
        engine_id="rules_pk",
        probability=score,
        evidence=evidence,
        features={"flag_count": len(evidence)},
    )
