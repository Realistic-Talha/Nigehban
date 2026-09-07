"""Artifact loader — ONNX / joblib calibrators pinned by manifest."""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_ARTIFACTS_DIR = Path(__file__).resolve().parents[2] / "models" / "artifacts"
_MANIFEST_PATH = _ARTIFACTS_DIR / "manifest.json"


def artifacts_dir() -> Path:
    _ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    return _ARTIFACTS_DIR


def load_manifest() -> dict[str, Any]:
    if not _MANIFEST_PATH.exists():
        return {"artifacts": {}}
    try:
        return json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
    except Exception:
        logger.warning("Failed to read artifact manifest", exc_info=True)
        return {"artifacts": {}}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def resolve_artifact(name: str) -> Path | None:
    """Return path if artifact exists (hash check when manifest lists one)."""
    manifest = load_manifest()
    meta = (manifest.get("artifacts") or {}).get(name)
    path = artifacts_dir() / (meta["file"] if meta and meta.get("file") else name)
    if not path.exists():
        # Also try bare name under artifacts/
        alt = artifacts_dir() / name
        if alt.exists():
            path = alt
        else:
            return None
    if meta and meta.get("sha256"):
        digest = sha256_file(path)
        if digest != meta["sha256"]:
            logger.error(
                "Artifact hash mismatch for %s: expected %s got %s",
                name,
                meta["sha256"],
                digest,
            )
            return None
    return path


def load_onnx_session(name: str):  # noqa: ANN201
    path = resolve_artifact(name)
    if path is None:
        return None
    try:
        import onnxruntime as ort

        return ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
    except Exception:
        logger.warning("Could not load ONNX artifact %s", name, exc_info=True)
        return None


def load_joblib(name: str) -> Any | None:
    path = resolve_artifact(name)
    if path is None:
        return None
    try:
        import joblib

        return joblib.load(path)
    except Exception:
        logger.warning("Could not load joblib artifact %s", name, exc_info=True)
        return None
