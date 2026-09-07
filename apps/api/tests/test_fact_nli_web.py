"""Unit tests for web dispute consensus + factcheck lock."""

from __future__ import annotations

from app.engines.base import EngineResult
from app.engines.fact_nli import score_web_dispute
from app.engines.meta import lock_verdict


def test_single_strong_falsely_claims_is_enough():
    """One Boom/AltNews-style headline must not be drowned by soft news/TikTok noise."""
    snippets = [
        {"title": "Imran Khan - Wikipedia", "url": "https://en.wikipedia.org/wiki/Imran_Khan", "body": ""},
        {
            "title": "Supporters Shower Flower Petals Along Roads As Imran Khan's Convoy Passes",
            "url": "https://www.tiktok.com/@x",
            "body": "Supporters shower petals",
        },
        {
            "title": "Reel falsely claims Imran Khan was taken to Shifa Hospital",
            "url": "https://www.boomlive.in/fact-check/imran-khan",
            "body": "The viral Instagram reel is false.",
        },
        {
            "title": "Reportedly, supporters shower Imran Khan's convoy with flower petals",
            "url": "https://www.geo.tv/latest/news",
            "body": "Crowds gathered near the hospital.",
        },
    ]
    web = score_web_dispute(snippets)
    assert web["nli_label"] == "REFUTES"
    assert web["abstain"] is False
    assert web["strong_refute"] >= 1
    assert web["probability"] >= 0.78

    snippets = [
        {
            "title": "Reel falsely claims Imran Khan was taken to Shifa Hospital",
            "url": "https://www.boomlive.in/fact-check/imran-khan",
            "body": "The viral Instagram reel is false.",
        },
        {
            "title": "Viral clip does not show convoy transporting Imran Khan to hospital",
            "url": "https://www.altnews.in/fact-check/imran",
            "body": "Footage is from a different event.",
        },
        {
            "title": "Fact check: Viral visuals of Imran Khan from recent Islamabad hospital visit",
            "url": "https://example-factcheck.org/article",
            "body": "The visuals are misleading and do not depict the claimed convoy.",
        },
        {
            "title": "Former Pakistan PM Imran Khan moved to hospital after court order",
            "url": "https://www.reuters.com/world/asia-pacific/imran",
            "body": "Court ordered medical treatment.",
        },
    ]
    web = score_web_dispute(snippets)
    assert web["nli_label"] == "REFUTES"
    assert web["abstain"] is False
    assert web["probability"] >= 0.72
    assert web["refute_hits"] >= 1.5


def test_web_support_consensus():
    snippets = [
        {
            "title": "Fact check: Claim is true — official confirms statement",
            "url": "https://www.fullfact.org/article",
            "body": "Verified as true by the ministry.",
        },
        {
            "title": "Official confirms the announcement is accurate",
            "url": "https://www.reuters.com/article",
            "body": "The claim is authentic.",
        },
    ]
    web = score_web_dispute(snippets)
    assert web["nli_label"] == "SUPPORTS"
    assert web["abstain"] is False
    assert web["support_p"] >= 0.70


def test_weak_news_only_stays_nei():
    snippets = [
        {
            "title": "Imran Khan shifted to hospital amid tight security",
            "url": "https://www.geo.tv/latest/news",
            "body": "Security was tight around the facility.",
        },
        {
            "title": "Court hearing continues in Islamabad",
            "url": "https://www.dawn.com/news/1",
            "body": "Proceedings adjourned until Monday.",
        },
    ]
    web = score_web_dispute(snippets)
    assert web["nli_label"] == "NEI"
    assert web["abstain"] is True


def test_lock_verdict_false_from_web_dispute():
    nli = EngineResult(
        engine_id="fact_nli",
        probability=0.84,
        abstain=False,
        evidence=[],
        features={"nli_label": "REFUTES", "support_p": 0.1, "backend": "web_dispute_consensus"},
    )
    locked = lock_verdict("factcheck", [nli])
    assert locked.verdict == "false"
    assert locked.abstain is False
    assert locked.confidence >= 55.0


def test_lock_verdict_misleading():
    nli = EngineResult(
        engine_id="fact_nli",
        probability=0.70,
        abstain=False,
        features={"nli_label": "MISLEADING", "support_p": 0.2},
    )
    locked = lock_verdict("factcheck", [nli])
    assert locked.verdict == "misleading"
    assert locked.confidence >= 55.0


def test_lock_verdict_nei_still_unverified():
    nli = EngineResult(
        engine_id="fact_nli",
        probability=0.35,
        abstain=True,
        features={"nli_label": "NEI"},
    )
    locked = lock_verdict("factcheck", [nli])
    assert locked.verdict == "unverified"
    assert locked.abstain is True
    assert 20.0 <= locked.confidence <= 45.0


def test_year_mismatch_blocks_soft_support():
    snippets = [
        {
            "title": "Landslide victory for Imran Khan's party in Pakistan elections",
            "url": "https://www.bbc.com/news",
            "body": "Party wins seats",
        },
    ]
    # Claim year 2023; title has no 2023 → must not auto-SUPPORT.
    web = score_web_dispute(snippets, claim="imran khan wins 2023 elections")
    assert web["nli_label"] != "SUPPORTS"


def test_normalize_year_typo():
    from app.engines.fact_nli import _normalize_claim_years

    fixed, years = _normalize_claim_years("imran khan wins 20223 elections")
    assert "2023" in fixed
    assert "2023" in years
