"""AudioSyncAgent — librosa spectral analysis for video audio integrity."""

import asyncio
import io
import logging
import tempfile
from pathlib import Path
from typing import Any

from app.agents.base import BaseAgent
from app.services.storage import storage

logger = logging.getLogger(__name__)

try:
    import librosa
    import numpy as np

    _HAS_LIBROSA = True
except ImportError:
    _HAS_LIBROSA = False


class AudioSyncAgent(BaseAgent):
    """Analyze video audio tracks with librosa spectral statistics."""

    name: str = "audio_sync"
    model_tier: str = "haiku"
    timeout: float = 30.0

    async def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        media_url = input_data.get("media_url", "")
        if not media_url or not media_url.strip():
            return self._result(False, note="No media URL")

        is_video, media_type_hint = self._infer_media_type(media_url)
        if not is_video:
            return self._result(
                False,
                integrity=50,
                confidence=60,
                note=f"Audio analysis not applicable for {media_type_hint}",
            )

        if not _HAS_LIBROSA:
            return self._result(True, integrity=50, confidence=30, note="librosa not installed")

        try:
            data = await storage.download_file(media_url)
        except Exception as exc:
            logger.warning("AudioSyncAgent download failed: %s", exc)
            return self._result(False, note=f"Download failed: {exc}")

        suffix = self._suffix_from_url(media_url)
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(data)
            tmp_path = tmp.name

        try:
            analysis = await asyncio.to_thread(self._analyze_file, tmp_path)
            return self._result(True, **analysis)
        except Exception as exc:
            logger.warning("AudioSyncAgent analysis failed: %s", exc)
            return self._result(True, integrity=45, confidence=25, note=str(exc))
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    @staticmethod
    def _analyze_file(path: str) -> dict[str, Any]:
        y, sr = librosa.load(path, sr=None, mono=True)
        if y.size == 0:
            return {
                "integrity": 40,
                "confidence": 40,
                "sync_score": 0.0,
                "lip_sync_match": None,
                "voice_consistency": 0.0,
                "audio_splicing_detected": False,
                "note": "Empty audio track",
            }

        rms = librosa.feature.rms(y=y)[0]
        flatness = float(np.mean(librosa.feature.spectral_flatness(y=y)))
        centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
        zcr = librosa.feature.zero_crossing_rate(y)[0]

        centroid_std = float(np.std(centroid))
        centroid_mean = float(np.mean(centroid))
        voice_consistency = max(
            0.0,
            min(1.0, 1.0 - (centroid_std / (centroid_mean + 1e-6))),
        )

        # Detect abrupt RMS drops (possible splices)
        diffs = np.diff(rms)
        splice_threshold = float(np.std(diffs) * 2.5 + 0.01)
        splice_count = int(np.sum(diffs < -splice_threshold))
        audio_splicing_detected = splice_count >= 3

        sync_score = max(0.0, min(1.0, 1.0 - flatness * 0.5))
        integrity = int(max(0, min(100, 70 - splice_count * 8 + voice_consistency * 20)))
        confidence = 65 if y.size > sr else 40

        return {
            "integrity": integrity,
            "confidence": confidence,
            "sync_score": round(sync_score, 3),
            "lip_sync_match": None,
            "voice_consistency": round(voice_consistency, 3),
            "audio_splicing_detected": audio_splicing_detected,
            "note": f"frames={len(rms)}, zcr_mean={float(np.mean(zcr)):.3f}",
        }

    @staticmethod
    def _result(
        has_audio: bool,
        integrity: int = 0,
        confidence: float = 0,
        sync_score: float = 0.0,
        lip_sync_match: float | None = None,
        voice_consistency: float = 0.0,
        audio_splicing_detected: bool = False,
        note: str = "",
    ) -> dict[str, Any]:
        return {
            "output": {
                "has_audio": has_audio,
                "sync_score": sync_score,
                "lip_sync_match": lip_sync_match,
                "audio_splicing_detected": audio_splicing_detected,
                "voice_consistency": voice_consistency,
                "audio_integrity_score": integrity,
                "note": note,
            },
            "confidence": float(confidence),
        }

    @staticmethod
    def _infer_media_type(media_url: str) -> tuple[bool, str]:
        url_lower = media_url.lower()
        video_extensions = {".mp4", ".webm", ".mov", ".avi", ".mkv"}
        image_extensions = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".heic", ".gif"}

        for ext in video_extensions:
            if url_lower.endswith(ext) or f"{ext}?" in url_lower:
                return True, f"Video file ({ext})"
        for ext in image_extensions:
            if url_lower.endswith(ext) or f"{ext}?" in url_lower:
                return False, f"Image file ({ext})"

        video_platforms = ("youtube", "youtu.be", "tiktok", "vimeo", "dailymotion")
        for platform in video_platforms:
            if platform in url_lower:
                return True, f"Video (streaming: {platform})"

        social_platforms = ("instagram", "twitter.com", "x.com", "facebook", "reddit")
        for platform in social_platforms:
            if platform in url_lower:
                return True, f"Social media ({platform})"

        return True, "Unknown (assuming video)"

    @staticmethod
    def _suffix_from_url(media_url: str) -> str:
        lower = media_url.lower().split("?")[0]
        for ext in (".mp4", ".webm", ".mov", ".avi", ".mkv", ".m4a", ".wav"):
            if lower.endswith(ext):
                return ext
        return ".mp4"
