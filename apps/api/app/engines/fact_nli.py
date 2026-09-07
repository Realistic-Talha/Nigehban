"""Fact verification engine — ClaimReview + web dispute consensus + NLI."""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

import httpx

from app.core.config import settings
from app.engines.base import EngineResult, Evidence

logger = logging.getLogger(__name__)

_nli_bundle: tuple[Any, Any] | None = None  # (tokenizer, model)
_nli_load_failed = False
_NLI_LOAD_TIMEOUT_S = 45.0
_DDG_TIMEOUT_S = 22.0

# Strong refute / support cues in fact-check headlines and snippets.
# Titles like "Reel falsely claims…" must drive a conclusive verdict — not NEI abstain.
_REFUTE_STRONG: list[re.Pattern[str]] = [
    re.compile(p, re.I)
    for p in (
        r"\bfalsely\s+claims?\b",
        r"\bfalse\s+claim\b",
        r"\bdebunked\b",
        r"\bhoax\b",
        r"\bfabricated\b",
        r"\bdoes\s+not\s+show\b",
        r"\bdid\s+not\s+show\b",
        r"\bclaim\s+is\s+false\b",
        r"\brating:\s*false\b",
        r"\bfake\s+(news|video|clip|reel|image|photo|visuals?)\b",
    )
]
_REFUTE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(p, re.I)
    for p in (
        r"\bfalsehood\b",
        r"\bdoctored\b",
        r"\baltered\s+(video|clip|image|photo)\b",
        r"\bnot\s+(show|showing)\b",
        r"\bno\s+evidence\b",
        r"\binaccurate\b",
        r"\bincorrect\b",
        r"\bmisleading\b",
        r"\bpants\s+on\s+fire\b",
        r"\bfact[\s-]*check[:\s].*\b(false|fake|falsehood|misleading|debunk)\b",
        r"\bviral\s+.+\b(false|fake|misleading)\b",
    )
]
_SUPPORT_PATTERNS: list[re.Pattern[str]] = [
    re.compile(p, re.I)
    for p in (
        r"\bconfirms?\b",
        r"\bverified\s+(as\s+)?true\b",
        r"\btrue\s+that\b",
        r"\baccurate(ly)?\b",
        r"\bauthentic\b",
        r"\bfact[\s-]*check[:\s].*\b(true|correct|accurate)\b",
        r"\brating:\s*true\b",
        r"\bclaim\s+is\s+true\b",
    )
]

_YEAR_RE = re.compile(r"\b(20\d{2})\b")
_ODD_YEAR_RE = re.compile(r"\b(20\d{3,})\b")  # typos like 20223

_JUDGE_PROMPT = """\
You are Nigehban's fact-check adjudicator for Pakistan-facing claims.
You receive a CLAIM and web SEARCH SNIPPETS (title + body + url). Decide the claim's veracity.

Rules:
- Prefer a conclusive label: false, misleading, or true.
- Use unverified ONLY when snippets are irrelevant biographies/generic pages that neither
  support nor refute the specific claim (who/what/when).
- If the claim names a year/event and snippets describe a different year/event or only a
  related person/party without confirming the claim as stated → false or misleading, not true.
- If fact-check headlines say falsely/debunked/does not show → false (or misleading if they say so).
- If multiple independent news titles clearly affirm the claim as stated → true.
- Do not invent facts beyond the snippets; you may note mismatches between claim wording and titles.
- Confidence 55-95 for conclusive labels; <=45 only for unverified.

Return ONLY JSON:
{"label":"true"|"false"|"misleading"|"unverified","confidence":75,"reason_en":"2-4 sentences citing snippet titles"}
"""


def _normalize_claim_years(claim: str) -> tuple[str, list[str]]:
    """Fix obvious year typos (20223→2023) and return search-friendly claim + years."""
    years: list[str] = []
    fixed = claim
    for m in _ODD_YEAR_RE.finditer(claim):
        raw = m.group(1)
        if len(raw) == 5 and raw.startswith("20"):
            # 20223 → drop the extra middle digit → 2023
            cand = raw[:2] + raw[3:]
            fixed = fixed.replace(raw, cand)
            years.append(cand)
    for m in _YEAR_RE.finditer(fixed):
        y = m.group(1)
        if y not in years:
            years.append(y)
    return fixed, years


def _years_in_text(text: str) -> set[str]:
    return set(_YEAR_RE.findall(text or ""))

_FACTCHECK_HOST_HINTS = (
    "factcheck",
    "altnews",
    "boomlive",
    "boom-",
    "snopes",
    "politifact",
    "fullfact",
    "afp.com",
    "reuters.com",
    "apnews.com",
    "factly",
    "thequint",
    "indiatoday",
    "geo.tv",
    "dawn.com",
    "arynews",
    "samaa",
    "checkyourfact",
    "leadstories",
    "misbar",
    "logically",
)

_CLAIMREVIEW_REFUTE = (
    "false",
    "fake",
    "pants",
    "incorrect",
    "misleading",
    "debunked",
    "hoax",
    "baseless",
    "fabricated",
    "altered",
    "doctored",
    "inaccurate",
)
_CLAIMREVIEW_SUPPORT = ("true", "correct", "accurate", "verified")


async def _factcheck_tools_search(query: str) -> list[dict[str, Any]]:
    key = getattr(settings, "GOOGLE_FACTCHECK_API_KEY", "") or ""
    if not key or not query.strip():
        return []
    url = "https://factchecktools.googleapis.com/v1alpha1/claims:search"
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(url, params={"query": query[:256], "key": key, "languageCode": "en"})
            if resp.status_code != 200:
                logger.warning("Fact Check Tools API status %s", resp.status_code)
                return []
            data = resp.json()
            return data.get("claims") or []
    except Exception:
        logger.warning("Fact Check Tools search failed", exc_info=True)
        return []


def _normalize_hit(r: dict[str, Any]) -> dict[str, str]:
    return {
        "title": r.get("title") or "",
        "url": r.get("href") or r.get("link") or r.get("url") or "",
        "body": r.get("body") or r.get("snippet") or "",
    }


def _web_search_sync(query: str, n: int = 6) -> list[dict[str, str]]:
    """Metasearch via ddgs (Bing/Brave/Google/…) — plain DuckDuckGo alone is often rate-limited."""
    fixed, years = _normalize_claim_years(query)
    queries = [fixed.strip()]
    q_low = fixed.lower()
    if "fact check" not in q_low and "fact-check" not in q_low:
        short = " ".join(fixed.split()[:14])
        queries.append(f"{short} fact check")
    if years:
        queries.append(f"{fixed} {years[0]} election")

    seen: set[str] = set()
    out: list[dict[str, str]] = []

    def _ingest(rows: list[Any]) -> None:
        for r in rows:
            if not isinstance(r, dict):
                continue
            hit = _normalize_hit(r)
            key = (hit["url"] or hit["title"]).lower()
            if not key or key in seen:
                continue
            seen.add(key)
            out.append(hit)

    try:
        try:
            from ddgs import DDGS  # type: ignore
        except ImportError:
            from duckduckgo_search import DDGS  # type: ignore

        backends = ("auto", "bing,brave,yahoo", "google")
        with DDGS() as client:
            for q in queries:
                if len(out) >= n:
                    break
                for backend in backends:
                    try:
                        rows = list(
                            client.text(
                                q,
                                region="pk-en",
                                max_results=n,
                                backend=backend,
                            )
                        )
                    except TypeError:
                        rows = list(client.text(q, region="pk-en", max_results=n))
                    except Exception:
                        logger.debug("search backend %s failed for %r", backend, q[:60], exc_info=True)
                        continue
                    _ingest(rows)
                    if len(out) >= n:
                        break
                # Keep going across query variants to diversify evidence.
        return out[:n]
    except Exception:
        logger.warning("Web evidence search failed", exc_info=True)
        return []


async def _duckduckgo_snippets(query: str, n: int = 6) -> list[dict[str, str]]:
    """Non-blocking web search with hard timeout — sync client must not freeze the API."""
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(_web_search_sync, query, n),
            timeout=_DDG_TIMEOUT_S,
        )
    except asyncio.TimeoutError:
        logger.warning("Web evidence timed out after %.0fs", _DDG_TIMEOUT_S)
        return []
    except Exception:
        logger.warning("Web evidence search failed", exc_info=True)
        return []


def _is_factcheck_host(url: str) -> bool:
    host = (url or "").lower()
    return any(h in host for h in _FACTCHECK_HOST_HINTS)


def score_web_dispute(snippets: list[dict[str, str]], claim: str = "") -> dict[str, Any]:
    """Score search titles/bodies for refute vs support consensus.

    Modern AFC practice: evidence retrieval drives veracity; title-level fact-check
    language (e.g. 'falsely claims') is a first-class signal when NLI is NEI or offline.
    A single strong refute headline from search is enough for a conclusive REFUTES.
    SUPPORTS requires year alignment when the claim names a year.
    """
    refute_hits = 0.0
    support_hits = 0.0
    misleading_hits = 0.0
    strong_refute = 0
    matched: list[str] = []
    _, claim_years = _normalize_claim_years(claim)

    for s in snippets[:8]:
        title = (s.get("title") or "").strip()
        body = (s.get("body") or "").strip()
        url = s.get("url") or ""
        text = f"{title}. {body}"
        weight = 1.35 if _is_factcheck_host(url) else 1.0
        if re.search(r"\bfact[\s-]*check\b", title, re.I):
            weight += 0.35
        # Generic encyclopedia pages rarely decide a specific claim.
        if "wikipedia.org" in (url or "").lower():
            weight *= 0.35

        is_strong = any(p.search(text) for p in _REFUTE_STRONG)
        is_ref = is_strong or any(p.search(text) for p in _REFUTE_PATTERNS)
        is_sup = any(p.search(text) for p in _SUPPORT_PATTERNS)
        snip_years = _years_in_text(text)
        if claim_years and is_sup and not snip_years.intersection(claim_years):
            # "Landslide victory" about another year must not support "wins 2023".
            is_sup = False
            if snip_years and not is_ref:
                misleading_hits += weight * 0.8

        if re.search(r"\bmisleading\b", text, re.I) and not re.search(
            r"\b(false|fake|debunked|hoax|falsely)\b", text, re.I
        ):
            misleading_hits += weight
            matched.append(title[:100] or url)
        if is_ref and not (is_sup and not is_strong):
            w = weight + (0.9 if is_strong else 0.0)
            refute_hits += w
            if is_strong:
                strong_refute += 1
            matched.append(title[:100] or url)
        elif is_sup and not is_ref:
            support_hits += weight
            matched.append(title[:100] or url)

    label = "NEI"
    probability = 0.35
    support_p = 0.35
    abstain = True

    if strong_refute >= 1 and refute_hits >= support_hits:
        label = "REFUTES"
        probability = min(0.94, 0.78 + 0.05 * strong_refute + 0.03 * max(0, refute_hits - 1))
        support_p = max(0.05, 1.0 - probability)
        abstain = False
    elif refute_hits >= 1.0 and refute_hits > support_hits + 0.25:
        label = "REFUTES"
        probability = min(0.92, 0.72 + 0.06 * refute_hits)
        support_p = max(0.05, 1.0 - probability)
        abstain = False
        if misleading_hits >= refute_hits and strong_refute == 0 and refute_hits < 2.0:
            label = "MISLEADING"
            probability = min(0.85, 0.65 + 0.05 * misleading_hits)
    elif support_hits >= 1.5 and support_hits > refute_hits + 0.4:
        label = "SUPPORTS"
        support_p = min(0.90, 0.70 + 0.06 * support_hits)
        probability = max(0.08, 1.0 - support_p)
        abstain = False
    elif misleading_hits >= 1.25 and refute_hits < 1.0 and strong_refute == 0:
        label = "MISLEADING"
        probability = min(0.82, 0.62 + 0.06 * misleading_hits)
        support_p = max(0.08, 1.0 - probability)
        abstain = False

    return {
        "nli_label": label,
        "probability": round(probability, 3),
        "support_p": round(support_p, 3),
        "abstain": abstain,
        "refute_hits": round(refute_hits, 2),
        "support_hits": round(support_hits, 2),
        "misleading_hits": round(misleading_hits, 2),
        "strong_refute": strong_refute,
        "matched_titles": matched[:6],
        "claim_years": claim_years,
        "backend": "web_dispute_consensus",
    }


async def _llm_evidence_judge(claim: str, snippets: list[dict[str, str]]) -> dict[str, Any] | None:
    """Force a conclusive label from retrieved snippets when lexicon/NLI abstain."""
    if not snippets:
        return None
    lines = []
    for i, s in enumerate(snippets[:6], 1):
        lines.append(
            f"{i}. title={s.get('title','')}\n   url={s.get('url','')}\n   body={s.get('body','')[:240]}"
        )
    user = f"CLAIM:\n{claim}\n\nSEARCH SNIPPETS:\n" + "\n".join(lines)
    try:
        from app.services.llm import llm_service

        result = await asyncio.wait_for(
            llm_service.call_haiku(
                _JUDGE_PROMPT,
                [{"role": "user", "content": user}],
                max_tokens=500,
            ),
            timeout=25.0,
        )
        parsed = result.get("json") if isinstance(result, dict) else None
        if not isinstance(parsed, dict):
            return None
        raw = str(parsed.get("label") or "unverified").strip().lower()
        label_map = {
            "true": "SUPPORTS",
            "supports": "SUPPORTS",
            "false": "REFUTES",
            "refutes": "REFUTES",
            "misleading": "MISLEADING",
            "unverified": "NEI",
            "nei": "NEI",
        }
        label = label_map.get(raw, "NEI")
        try:
            conf = float(parsed.get("confidence") or 0)
        except (TypeError, ValueError):
            conf = 0.0
        conf = max(0.0, min(95.0, conf))
        if label == "NEI":
            return {
                "nli_label": "NEI",
                "probability": 0.35,
                "support_p": 0.35,
                "abstain": True,
                "confidence": conf or 35.0,
                "reason_en": str(parsed.get("reason_en") or ""),
                "backend": "llm_evidence_judge",
            }
        if label == "SUPPORTS":
            sp = max(0.55, conf / 100.0)
            return {
                "nli_label": "SUPPORTS",
                "probability": max(0.08, 1.0 - sp),
                "support_p": sp,
                "abstain": False,
                "confidence": max(55.0, conf),
                "reason_en": str(parsed.get("reason_en") or ""),
                "backend": "llm_evidence_judge",
            }
        # REFUTES / MISLEADING
        p = max(0.55, conf / 100.0)
        return {
            "nli_label": label,
            "probability": p,
            "support_p": max(0.05, 1.0 - p),
            "abstain": False,
            "confidence": max(55.0, conf),
            "reason_en": str(parsed.get("reason_en") or ""),
            "backend": "llm_evidence_judge",
        }
    except Exception:
        logger.warning("LLM evidence judge failed", exc_info=True)
        return None



def _load_nli_hf() -> tuple[Any, Any] | None:
    """Load DeBERTa-NLI from artifacts, or auto-download pretrained cross-encoder."""
    global _nli_bundle, _nli_load_failed
    if _nli_bundle is not None:
        return _nli_bundle
    if _nli_load_failed:
        return None
    from app.engines.artifacts import artifacts_dir

    model_dir = artifacts_dir() / "fact_nli" / "model"
    model_id = "cross-encoder/nli-deberta-v3-xsmall"
    try:
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        if (model_dir / "config.json").exists():
            tok = AutoTokenizer.from_pretrained(str(model_dir), local_files_only=True)
            model = AutoModelForSequenceClassification.from_pretrained(
                str(model_dir), local_files_only=True
            )
        else:
            logger.info("fact_nli model missing locally — downloading %s", model_id)
            model_dir.mkdir(parents=True, exist_ok=True)
            tok = AutoTokenizer.from_pretrained(model_id)
            model = AutoModelForSequenceClassification.from_pretrained(model_id)
            model.save_pretrained(model_dir)
            tok.save_pretrained(model_dir)

        model.eval()
        _nli_bundle = (tok, model)
        return _nli_bundle
    except Exception:
        _nli_load_failed = True
        logger.warning("Could not load fact_nli HF model", exc_info=True)
        return None


def _nli_predict_sync(claim: str, evidence: str) -> tuple[str, float, float] | None:
    """Return (label, p_refutes, p_supports) from vendored NLI."""
    bundle = _load_nli_hf()
    if bundle is None or not evidence.strip():
        return None

    tok, model = bundle
    try:
        import torch.nn.functional as F

        inputs = tok(
            claim[:512],
            evidence[:512],
            return_tensors="pt",
            truncation=True,
            max_length=256,
            padding=True,
        )
        with __import__("torch").no_grad():
            logits = model(**inputs).logits[0]
            probs = F.softmax(logits, dim=-1).cpu().tolist()
        id2label = {int(k): str(v).lower() for k, v in (model.config.id2label or {}).items()}
        by_name = {id2label.get(i, str(i)): float(p) for i, p in enumerate(probs)}
        p_ref = by_name.get("contradiction", by_name.get("refutes", 0.0))
        p_sup = by_name.get("entailment", by_name.get("supports", 0.0))
        p_neu = by_name.get("neutral", by_name.get("nei", 0.0))
        if p_neu >= max(p_ref, p_sup) and p_neu >= 0.45:
            label = "NEI"
        elif p_ref >= p_sup:
            label = "REFUTES"
        else:
            label = "SUPPORTS"
        return label, p_ref, p_sup
    except Exception:
        logger.warning("NLI predict failed", exc_info=True)
        return None


async def _nli_predict(claim: str, evidence: str) -> tuple[str, float, float] | None:
    global _nli_load_failed
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(_nli_predict_sync, claim, evidence),
            timeout=_NLI_LOAD_TIMEOUT_S,
        )
    except asyncio.TimeoutError:
        _nli_load_failed = True
        logger.warning("NLI timed out after %.0fs — abstaining NEI", _NLI_LOAD_TIMEOUT_S)
        return None
    except Exception:
        logger.warning("NLI predict failed", exc_info=True)
        return None


def _claimreview_label(rating: str) -> str | None:
    r = (rating or "").lower()
    if any(x in r for x in _CLAIMREVIEW_REFUTE):
        if "misleading" in r and not any(
            x in r for x in ("false", "fake", "hoax", "debunked", "fabricated")
        ):
            return "MISLEADING"
        return "REFUTES"
    if any(x in r for x in _CLAIMREVIEW_SUPPORT):
        return "SUPPORTS"
    return None


async def run_fact_nli_engine(claim_text: str) -> EngineResult:
    claim_raw = (claim_text or "").strip()
    if not claim_raw:
        return EngineResult(
            engine_id="fact_nli",
            probability=0.0,
            abstain=True,
            note="Empty claim",
            features={"nli_label": "NEI"},
        )

    claim, _years = _normalize_claim_years(claim_raw)
    claims = await _factcheck_tools_search(claim)
    snippets = await _duckduckgo_snippets(claim)
    evidence_items: list[Evidence] = []
    sources: list[dict[str, Any]] = []

    for c in claims[:5]:
        reviews = c.get("claimReview") or []
        for rev in reviews[:2]:
            rating = ((rev.get("textualRating") or "") + " " + (rev.get("title") or "")).lower()
            url = rev.get("url") or ""
            publisher = (rev.get("publisher") or {}).get("name") or "FactCheck"
            sources.append({"url": url, "title": rev.get("title"), "publisher": publisher})
            evidence_items.append(
                Evidence(type="claimreview", value=url, signal="factcheck_api", detail=rating[:120])
            )
            cr = _claimreview_label(rating)
            if cr == "REFUTES":
                return EngineResult(
                    engine_id="fact_nli",
                    probability=0.88,
                    evidence=evidence_items,
                    features={
                        "nli_label": "REFUTES",
                        "support_p": 0.08,
                        "sources": sources,
                        "backend": "factcheck_tools",
                    },
                )
            if cr == "MISLEADING":
                return EngineResult(
                    engine_id="fact_nli",
                    probability=0.78,
                    evidence=evidence_items,
                    features={
                        "nli_label": "MISLEADING",
                        "support_p": 0.15,
                        "sources": sources,
                        "backend": "factcheck_tools",
                    },
                )
            if cr == "SUPPORTS":
                return EngineResult(
                    engine_id="fact_nli",
                    probability=0.15,
                    evidence=evidence_items,
                    features={
                        "nli_label": "SUPPORTS",
                        "support_p": 0.85,
                        "sources": sources,
                        "backend": "factcheck_tools",
                    },
                )

    for s in snippets[:5]:
        sources.append({"url": s["url"], "title": s["title"], "publisher": "web"})
        evidence_items.append(
            Evidence(type="web", value=s["url"], signal="search_snippet", detail=s["title"][:80])
        )

    web = score_web_dispute(snippets, claim=claim)

    async def _maybe_llm_judge() -> EngineResult | None:
        if not snippets:
            return None
        judged = await _llm_evidence_judge(claim, snippets)
        if not judged or judged.get("abstain"):
            return None
        return EngineResult(
            engine_id="fact_nli",
            probability=float(judged["probability"]),
            abstain=False,
            evidence=evidence_items,
            features={
                "nli_label": judged["nli_label"],
                "support_p": judged["support_p"],
                "sources": sources,
                "backend": judged["backend"],
                "web_dispute": web,
                "judge_reason": judged.get("reason_en"),
                "judge_confidence": judged.get("confidence"),
            },
            note=(judged.get("reason_en") or "LLM evidence judge")[:240],
        )

    # NLI premise: titles carry the verdict language; bodies alone often look neutral.
    premise_parts = []
    for s in snippets[:4]:
        t = (s.get("title") or "").strip()
        b = (s.get("body") or "").strip()
        if t:
            premise_parts.append(t)
        if b:
            premise_parts.append(b)
    nli = None
    if premise_parts and not _nli_load_failed:
        nli = await _nli_predict(claim, " ".join(premise_parts)[:900])
    elif _nli_load_failed:
        logger.info("Skipping NLI (prior load/timeout failure) — using web/LLM judge")

    if nli:
        label, p_ref, p_sup = nli
        if (label == "NEI" or (label == "SUPPORTS" and p_sup < 0.55)) and not web["abstain"]:
            if web["nli_label"] in ("REFUTES", "MISLEADING") or (
                web["nli_label"] == "SUPPORTS" and label == "NEI"
            ):
                return EngineResult(
                    engine_id="fact_nli",
                    probability=float(web["probability"]),
                    abstain=False,
                    evidence=evidence_items,
                    features={
                        "nli_label": web["nli_label"],
                        "support_p": web["support_p"],
                        "sources": sources,
                        "backend": web["backend"],
                        "web_dispute": web,
                        "nli_raw": {"label": label, "p_ref": p_ref, "p_sup": p_sup},
                    },
                    note="Web fact-check consensus overrode weak/NEI NLI",
                )
        if web.get("strong_refute", 0) >= 1 and web["nli_label"] == "REFUTES":
            return EngineResult(
                engine_id="fact_nli",
                probability=float(web["probability"]),
                abstain=False,
                evidence=evidence_items,
                features={
                    "nli_label": "REFUTES",
                    "support_p": web["support_p"],
                    "sources": sources,
                    "backend": web["backend"],
                    "web_dispute": web,
                    "nli_raw": {"label": label, "p_ref": p_ref, "p_sup": p_sup},
                },
                note="Strong web refute headline consensus",
            )
        if label == "REFUTES" and web["nli_label"] in ("REFUTES", "MISLEADING"):
            p = max(p_ref, float(web["probability"]))
            return EngineResult(
                engine_id="fact_nli",
                probability=min(0.95, p),
                abstain=False,
                evidence=evidence_items,
                features={
                    "nli_label": "REFUTES" if web["nli_label"] == "REFUTES" else "MISLEADING",
                    "support_p": p_sup,
                    "sources": sources,
                    "backend": "hf_deberta_nli+web",
                    "web_dispute": web,
                },
            )
        if label == "SUPPORTS" and web["nli_label"] == "SUPPORTS":
            return EngineResult(
                engine_id="fact_nli",
                probability=0.15,
                abstain=False,
                evidence=evidence_items,
                features={
                    "nli_label": "SUPPORTS",
                    "support_p": max(p_sup, float(web["support_p"])),
                    "sources": sources,
                    "backend": "hf_deberta_nli+web",
                    "web_dispute": web,
                },
            )
        if label == "NEI" or (label == "SUPPORTS" and p_sup < 0.55 and web["abstain"]):
            judged = await _maybe_llm_judge()
            if judged is not None:
                return judged
        abstain = label == "NEI"
        return EngineResult(
            engine_id="fact_nli",
            probability=p_ref if label == "REFUTES" else (0.2 if label == "SUPPORTS" else 0.35),
            abstain=abstain,
            evidence=evidence_items,
            features={
                "nli_label": label,
                "support_p": p_sup,
                "sources": sources,
                "backend": "hf_deberta_nli",
                "web_dispute": web,
            },
        )

    if not web["abstain"]:
        return EngineResult(
            engine_id="fact_nli",
            probability=float(web["probability"]),
            abstain=False,
            evidence=evidence_items,
            features={
                "nli_label": web["nli_label"],
                "support_p": web["support_p"],
                "sources": sources,
                "backend": web["backend"],
                "web_dispute": web,
            },
            note="Conclusive from web fact-check headlines (NLI offline)",
        )

    judged = await _maybe_llm_judge()
    if judged is not None:
        return judged

    if not claims:
        return EngineResult(
            engine_id="fact_nli",
            probability=0.35,
            abstain=True,
            evidence=evidence_items,
            features={
                "nli_label": "NEI",
                "support_p": 0.35,
                "sources": sources,
                "backend": "retrieval_only",
                "web_dispute": web,
            },
            note="No ClaimReview or conclusive web dispute — abstaining (NEI)",
        )

    return EngineResult(
        engine_id="fact_nli",
        probability=0.40,
        abstain=True,
        evidence=evidence_items,
        features={
            "nli_label": "NEI",
            "support_p": 0.4,
            "sources": sources,
            "backend": "claimreview_inconclusive",
            "web_dispute": web,
        },
        note="ClaimReview present but rating inconclusive",
    )
