"""MetadataExtractAgent — EXIF-based metadata forensics."""

import io
import logging
from datetime import datetime
from typing import Any

from PIL import Image

from app.agents.base import BaseAgent
from app.services.storage import storage

logger = logging.getLogger(__name__)

try:
    import exifread
    _HAS_EXIFREAD = True
except ImportError:
    _HAS_EXIFREAD = False


class MetadataExtractAgent(BaseAgent):
    """Extract EXIF/metadata from image files."""

    name: str = "metadata_extract"
    model_tier: str = "haiku"
    timeout: float = 20.0

    async def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        media_url = input_data.get("media_url", "")
        if not media_url:
            return self._empty_output("No media URL provided")

        try:
            data = await storage.download_file(media_url)
        except Exception as exc:
            return self._empty_output(f"Could not download media: {exc}")

        suspicious: list[str] = []
        has_exif = False
        software = None
        creation_date = None
        gps_data = None

        if _HAS_EXIFREAD:
            tags = exifread.process_file(io.BytesIO(data), details=False)
            if tags:
                has_exif = True
                if "Image Software" in tags:
                    software = str(tags["Image Software"])
                    if any(s in software.lower() for s in ("photoshop", "gimp", "lightroom")):
                        suspicious.append(f"Editing software in metadata: {software}")
                if "EXIF DateTimeOriginal" in tags:
                    creation_date = str(tags["EXIF DateTimeOriginal"])
                if "GPS GPSLatitude" in tags and "GPS GPSLongitude" in tags:
                    gps_data = {
                        "latitude": str(tags.get("GPS GPSLatitude")),
                        "longitude": str(tags.get("GPS GPSLongitude")),
                    }
            else:
                suspicious.append("EXIF data missing or stripped")
        else:
            suspicious.append("exifread not installed")

        try:
            img = Image.open(io.BytesIO(data))
            if img.format and "JPEG" in img.format:
                pass  # normal
        except Exception:
            suspicious.append("Could not parse image with Pillow")

        integrity = 85 if has_exif and not suspicious else 45 if suspicious else 60
        confidence = 70 if has_exif else 40

        output = {
            "has_exif": has_exif,
            "creation_date": creation_date,
            "software": software,
            "gps_data": gps_data,
            "compression_level": "unknown",
            "suspicious_metadata": suspicious,
            "metadata_integrity_score": integrity,
        }
        return {"output": output, "confidence": confidence}

    @staticmethod
    def _empty_output(reason: str) -> dict[str, Any]:
        return {
            "output": {
                "has_exif": False,
                "suspicious_metadata": [reason],
                "metadata_integrity_score": 50,
            },
            "confidence": 20,
        }
