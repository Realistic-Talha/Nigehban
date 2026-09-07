"""URL phishing engine — lexical features + LightGBM ONNX or calibrated heuristic."""

from __future__ import annotations

import math
import re
from typing import Any
from urllib.parse import urlparse

from app.engines.artifacts import load_joblib, load_onnx_session
from app.engines.base import EngineResult, Evidence
from app.engines.entities import PK_BRANDS

FEATURE_NAMES = [
    "url_length",
    "host_length",
    "path_length",
    "num_digits",
    "num_dots",
    "num_hyphens",
    "num_at",
    "num_slash",
    "num_question",
    "num_equals",
    "num_percent",
    "has_ip",
    "has_https",
    "subdomain_depth",
    "has_punycode",
    "suspicious_tld",
    "brand_in_host",
    "brand_in_path",
    "brand_typosquat",
    "entropy",
    "digit_ratio",
    "uppercase_ratio",
    "has_shortener",
    "query_length",
    "max_label_len",
]


_SHORTENERS = {"bit.ly", "tinyurl.com", "t.co", "goo.gl", "is.gd", "ow.ly", "rb.gy"}
_BAD_TLDS = {".xyz", ".tk", ".ml", ".ga", ".cf", ".gq", ".buzz", ".top", ".click", ".loan"}


def _entropy(s: str) -> float:
    if not s:
        return 0.0
    from collections import Counter

    c = Counter(s)
    n = len(s)
    return -sum((v / n) * math.log2(v / n) for v in c.values())


def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def extract_url_features(url: str) -> dict[str, float]:
    raw = url.strip()
    if not raw.startswith("http"):
        raw = "http://" + raw
    parsed = urlparse(raw)
    host = (parsed.hostname or "").lower()
    path = parsed.path or ""
    query = parsed.query or ""
    full = raw.lower()

    labels = [x for x in host.split(".") if x]
    subdomain_depth = max(0, len(labels) - 2)

    brand_in_host = 1.0 if any(b in host for b in PK_BRANDS) else 0.0
    brand_in_path = 1.0 if any(b in path.lower() for b in PK_BRANDS) else 0.0

    typosquat = 0.0
    host_core = labels[-2] if len(labels) >= 2 else host
    for b in PK_BRANDS:
        if host_core == b:
            continue
        if 0 < _levenshtein(host_core, b) <= 2 and len(b) >= 4:
            typosquat = 1.0
            break

    has_ip = 1.0 if re.fullmatch(r"\d{1,3}(?:\.\d{1,3}){3}", host or "") else 0.0
    tld = "." + labels[-1] if labels else ""
    suspicious_tld = 1.0 if tld in _BAD_TLDS else 0.0
    has_shortener = 1.0 if host in _SHORTENERS else 0.0

    digits = sum(ch.isdigit() for ch in full)
    upper = sum(ch.isupper() for ch in url)

    feats = {
        "url_length": float(len(url)),
        "host_length": float(len(host)),
        "path_length": float(len(path)),
        "num_digits": float(digits),
        "num_dots": float(url.count(".")),
        "num_hyphens": float(url.count("-")),
        "num_at": float(url.count("@")),
        "num_slash": float(url.count("/")),
        "num_question": float(url.count("?")),
        "num_equals": float(url.count("=")),
        "num_percent": float(url.count("%")),
        "has_ip": has_ip,
        "has_https": 1.0 if parsed.scheme == "https" else 0.0,
        "subdomain_depth": float(subdomain_depth),
        "has_punycode": 1.0 if "xn--" in host else 0.0,
        "suspicious_tld": suspicious_tld,
        "brand_in_host": brand_in_host,
        "brand_in_path": brand_in_path,
        "brand_typosquat": typosquat,
        "entropy": _entropy(host),
        "digit_ratio": digits / max(1, len(full)),
        "uppercase_ratio": upper / max(1, len(url)),
        "has_shortener": has_shortener,
        "query_length": float(len(query)),
        "max_label_len": float(max((len(x) for x in labels), default=0)),
    }
    return feats


def _heuristic_score(feats: dict[str, float]) -> float:
    """Calibrated-ish fallback until Colab ONNX is present."""
    score = 0.05
    score += 0.25 * feats["has_ip"]
    score += 0.20 * feats["brand_typosquat"]
    score += 0.15 * feats["suspicious_tld"]
    score += 0.18 * feats["has_shortener"]
    score += 0.12 * min(1.0, feats["subdomain_depth"] / 3)
    score += 0.10 * (1.0 - feats["has_https"])
    score += 0.08 * min(1.0, feats["num_at"])
    score += 0.08 * min(1.0, feats["num_percent"] / 5)
    if feats["brand_in_path"] and not feats["brand_in_host"]:
        score += 0.22
    if feats["url_length"] > 75:
        score += 0.08
    return max(0.01, min(0.99, score))


def _predict_onnx(feats: dict[str, float]) -> float | None:
    session = load_onnx_session("url_lgbm.onnx")
    if session is None:
        return None
    import numpy as np

    vec = np.array([[feats[n] for n in FEATURE_NAMES]], dtype=np.float32)
    inputs = {session.get_inputs()[0].name: vec}
    outs = session.run(None, inputs)
    # LightGBM ONNX often returns labels + zipmap probabilities
    if len(outs) >= 2 and isinstance(outs[1], list) and outs[1]:
        prob_map = outs[1][0]
        if isinstance(prob_map, dict):
            # phishing class often labeled 1
            return float(prob_map.get(1, prob_map.get("1", list(prob_map.values())[-1])))
    arr = outs[0]
    try:
        return float(arr[0][1] if hasattr(arr[0], "__len__") else arr[0])
    except Exception:
        return None


def _predict_joblib(feats: dict[str, float]) -> float | None:
    model = load_joblib("url_lgbm.joblib")
    if model is None:
        return None
    if isinstance(model, dict) and "model" in model:
        model = model["model"]
    import numpy as np

    vec = np.array([[feats[n] for n in FEATURE_NAMES]], dtype=np.float64)
    if hasattr(model, "predict_proba"):
        return float(model.predict_proba(vec)[0][1])
    return float(model.predict(vec)[0])


_ALLOWLIST_SUFFIXES = (
    ".gov.pk",
    ".edu.pk",
    "sbp.org.pk",
    "fbr.gov.pk",
    "nadra.gov.pk",
    "jazzcash.com.pk",
    "easypaisa.com.pk",
)


def run_url_engine(urls: list[str]) -> EngineResult:
    if not urls:
        return EngineResult(
            engine_id="url_lgbm",
            probability=0.0,
            abstain=True,
            available=True,
            note="No URLs in input",
        )

    best_p = 0.0
    best_url = urls[0]
    best_feats: dict[str, Any] = {}
    evidence: list[Evidence] = []
    source = "heuristic"

    for url in urls[:5]:
        feats = extract_url_features(url)
        host = urlparse(url if url.startswith("http") else "http://" + url).hostname or ""
        if any(host.endswith(s) or host == s for s in _ALLOWLIST_SUFFIXES):
            p = 0.02
            source = "allowlist"
        else:
            p = _predict_onnx(feats)
            if p is not None:
                source = "onnx"
            else:
                p = _predict_joblib(feats)
                if p is not None:
                    source = "joblib"
                else:
                    p = _heuristic_score(feats)
                    source = "heuristic"
        if p > best_p:
            best_p = p
            best_url = url
            best_feats = feats

    if best_feats.get("brand_typosquat"):
        evidence.append(
            Evidence(type="url", value=best_url, signal="typosquat_brand", detail="Near-brand host")
        )
    if best_feats.get("has_ip"):
        evidence.append(Evidence(type="url", value=best_url, signal="ip_host"))
    if best_feats.get("has_shortener"):
        evidence.append(Evidence(type="url", value=best_url, signal="url_shortener"))
    if best_feats.get("suspicious_tld"):
        evidence.append(Evidence(type="url", value=best_url, signal="suspicious_tld"))

    return EngineResult(
        engine_id="url_lgbm",
        probability=float(best_p),
        evidence=evidence,
        features={**{k: best_feats.get(k) for k in FEATURE_NAMES}, "backend": source, "url": best_url},
        note=f"scored via {source}",
    )
