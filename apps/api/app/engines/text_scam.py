"""Text scam classifier — rules features + optional ONNX multilingual head."""

from __future__ import annotations

import re
from typing import Any

from app.engines.artifacts import load_onnx_session
from app.engines.base import EngineResult, Evidence
from app.engines.rules_pk import run_pk_rules


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[\w\u0600-\u06FF]+", (text or "").lower())


def run_text_scam_engine(text: str) -> EngineResult:
    text = text or ""
    rules = run_pk_rules(text)

    # Prefer TF-IDF pipeline from Colab
    from app.engines.artifacts import load_joblib

    pipe = load_joblib("text_scam_tfidf.joblib")
    if pipe is not None and text.strip():
        try:
            p = float(pipe.predict_proba([text])[0][1])
            evidence = list(rules.evidence)
            return EngineResult(
                engine_id="text_scam",
                probability=p,
                evidence=evidence,
                features={"backend": "tfidf_joblib"},
                abstain=False,
            )
        except Exception:
            pass

    head = load_joblib("text_scam_lgbm_head.joblib")
    if head is not None and text.strip():
        try:
            import numpy as np

            toks = _tokenize(text)
            feat = np.array([[
                float(len(text)),
                float(len(toks)),
                float(rules.probability),
                float(rules.features.get("flag_count", 0)),
                1.0 if "otp" in text.lower() else 0.0,
                1.0 if re.search(r"03\d{9}", text.replace(" ", "")) else 0.0,
            ]])
            p = float(head.predict_proba(feat)[0][1])
            return EngineResult(
                engine_id="text_scam",
                probability=p,
                evidence=list(rules.evidence),
                features={"backend": "lgbm_head"},
            )
        except Exception:
            pass

    # Optional ONNX text model (6-feature head)
    session = load_onnx_session("text_scam.onnx")
    if session is not None:
        try:
            import numpy as np

            toks = _tokenize(text)
            feat = np.array(
                [[
                    float(len(text)),
                    float(len(toks)),
                    float(rules.probability),
                    float(rules.features.get("flag_count", 0)),
                    1.0 if "otp" in text.lower() else 0.0,
                    1.0 if re.search(r"03\d{9}", text.replace(" ", "")) else 0.0,
                ]],
                dtype=np.float32,
            )
            inputs = {session.get_inputs()[0].name: feat}
            outs = session.run(None, inputs)
            p = float(outs[0].ravel()[0])
            p = max(0.0, min(1.0, p))
            return EngineResult(
                engine_id="text_scam",
                probability=p,
                evidence=list(rules.evidence),
                features={"backend": "onnx", "tokens": len(toks)},
                note="ONNX text_scam",
            )
        except Exception:
            pass

    # Fallback: blend rule score with lexical density of scam lexicon
    lexicon = {
        "otp", "cnic", "jazzcash", "easypaisa", "loan", "prize", "lottery",
        "arrest", "fine", "verify", "account", "blocked", "urgent", "foran",
    }
    toks = set(_tokenize(text))
    hit = len(toks & lexicon)
    lex_p = min(0.95, 0.1 + hit * 0.12)
    p = max(rules.probability, lex_p) if rules.evidence or hit else 0.1
    if not text.strip():
        return EngineResult(
            engine_id="text_scam",
            probability=0.0,
            abstain=True,
            note="Empty text",
        )

    evidence = list(rules.evidence)
    if hit:
        evidence.append(
            Evidence(type="text", value=str(hit), signal="scam_lexicon_hits", detail=f"{hit} lexicon hits")
        )

    return EngineResult(
        engine_id="text_scam",
        probability=float(p),
        evidence=evidence,
        features={"backend": "rules_lexicon", "lexicon_hits": hit},
        abstain=not bool(evidence) and hit == 0,
    )
