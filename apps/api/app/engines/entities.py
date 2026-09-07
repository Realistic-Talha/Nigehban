"""Deterministic entity extraction — URLs, PK phones, CNIC, brands."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

_URL_RE = re.compile(r"https?://[^\s<>\"']+|www\.[^\s<>\"']+", re.IGNORECASE)
_PHONE_RE = re.compile(
    r"(?:\+92[\s-]?)?0?3\d{2}[\s-]?\d{7}|\b0\d{2,4}[\s-]?\d{6,8}\b"
)
_CNIC_RE = re.compile(r"\b\d{5}[-\s]?\d{7}[-\s]?\d\b")

PK_BRANDS = [
    "jazzcash",
    "easypaisa",
    "jazz",
    "telenor",
    "ufone",
    "zong",
    "hbl",
    "meezan",
    "ubl",
    "mcb",
    "sbp",
    "fia",
    "nadra",
    "secp",
    "fbr",
    "bisp",
    "ehsaas",
    "benazir",
    "olx",
    "daraz",
]


def extract_entities(text: str) -> dict[str, Any]:
    text = text or ""
    urls = []
    for m in _URL_RE.findall(text):
        u = m if m.startswith("http") else f"http://{m}"
        urls.append(u.rstrip(").,;\"'"))

    phones = list({m.replace(" ", "").replace("-", "") for m in _PHONE_RE.findall(text)})
    cnics = list({re.sub(r"[-\s]", "", m) for m in _CNIC_RE.findall(text)})
    lower = text.lower()
    brands = [b for b in PK_BRANDS if b in lower]

    domains = []
    for u in urls:
        try:
            host = urlparse(u).hostname or ""
            if host:
                domains.append(host.lower())
        except Exception:
            pass

    return {
        "urls": urls,
        "domains": domains,
        "phones": phones,
        "cnics": cnics,
        "brands": brands,
        "text": text,
    }
