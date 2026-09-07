"""Media fingerprint utilities."""

import hashlib
import io
import logging

import imagehash
from PIL import Image

from app.services.storage import storage

logger = logging.getLogger(__name__)


async def compute_image_fingerprint(url: str) -> dict[str, str] | None:
    """Download image and compute phash + sha256."""
    try:
        data = await storage.download_file(url)
        file_hash = hashlib.sha256(data).hexdigest()
        image = Image.open(io.BytesIO(data))
        phash = str(imagehash.phash(image))
        return {"file_hash": file_hash, "phash": phash}
    except Exception:
        logger.warning("Could not fingerprint media at %s", url, exc_info=True)
        return None
