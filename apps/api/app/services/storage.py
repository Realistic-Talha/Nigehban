"""File storage service — S3/R2 compatible with local filesystem fallback."""

import logging
import uuid
from pathlib import Path

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class StorageService:
    """Upload and download files using S3-compatible storage (Cloudflare R2,
    AWS S3, MinIO) with an automatic fallback to local filesystem storage
    when no S3 credentials are configured.
    """

    def __init__(self) -> None:
        # Prefer explicit S3_* settings, then R2_* settings, then local fallback
        self._endpoint = settings.S3_ENDPOINT or settings.R2_ENDPOINT_URL
        self._bucket = settings.S3_BUCKET or settings.R2_BUCKET_NAME
        self._access_key = settings.S3_ACCESS_KEY or settings.R2_ACCESS_KEY_ID
        self._secret_key = settings.S3_SECRET_KEY or settings.R2_SECRET_ACCESS_KEY
        self._local_dir = Path(settings.LOCAL_STORAGE_DIR)

        self._use_s3 = bool(self._endpoint and self._access_key and self._secret_key)

        if not self._use_s3:
            logger.info("S3/R2 not configured — using local storage at %s", self._local_dir)
            self._local_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def upload_file(
        self,
        file_bytes: bytes,
        filename: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload a file and return its accessible URL.

        Parameters
        ----------
        file_bytes   : Raw bytes of the file.
        filename     : Original or desired filename.
        content_type : MIME type of the file.

        Returns
        -------
        URL string where the file can be retrieved.
        """
        # Generate a unique key to avoid collisions
        unique_key = f"{uuid.uuid4().hex[:12]}_{filename}"

        if self._use_s3:
            try:
                return await self._s3_upload(file_bytes, unique_key, content_type)
            except Exception:
                logger.warning("S3/R2 upload failed — falling back to local storage", exc_info=True)
        return await self._local_upload(file_bytes, unique_key)

    async def download_file(self, url: str) -> bytes:
        """Download a file by URL and return its raw bytes.

        Works for both S3-hosted and locally-stored files.
        """
        # If the URL points to our local storage, read from disk
        local_marker = f"/{self._local_dir}/"
        if local_marker in url or url.startswith(str(self._local_dir)):
            return self._local_download(url)

        # Otherwise fetch via HTTP
        async with httpx.AsyncClient(timeout=60.0) as client:
            headers: dict[str, str] = {}
            if self._use_s3:
                headers = self._s3_auth_headers("GET", url)
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            return resp.content

    # ------------------------------------------------------------------
    # S3 / R2 helpers
    # ------------------------------------------------------------------

    async def _s3_upload(
        self,
        file_bytes: bytes,
        key: str,
        content_type: str,
    ) -> str:
        """Upload to S3-compatible endpoint using a signed PUT request."""
        object_url = f"{self._endpoint}/{self._bucket}/{key}"

        headers = {
            "Content-Type": content_type,
            **self._s3_auth_headers("PUT", object_url, content_type=content_type),
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.put(object_url, content=file_bytes, headers=headers)
            resp.raise_for_status()

        logger.info("Uploaded to S3: %s (%d bytes)", key, len(file_bytes))
        return object_url

    def _s3_auth_headers(
        self,
        method: str,
        url: str,
        content_type: str = "",
    ) -> dict[str, str]:
        """Build minimal S3-compatible authorization headers.

        Uses the legacy S3 authorization header format. For production
        deployments, consider switching to AWS SigV4 via boto3.
        """
        import hashlib
        import hmac
        from datetime import datetime, timezone

        date_str = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")

        # Build the string-to-sign for S3 legacy auth
        content_md5 = ""
        string_to_sign = (
            f"{method}\n"
            f"{content_md5}\n"
            f"{content_type}\n"
            f"{date_str}\n"
            f"/{self._bucket}/{url.split('/')[-1]}"
        )

        signature = hmac.new(
            self._secret_key.encode(),
            string_to_sign.encode(),
            hashlib.sha1,
        ).digest()

        import base64
        sig_b64 = base64.b64encode(signature).decode()

        return {
            "Authorization": f"AWS {self._access_key}:{sig_b64}",
            "Date": date_str,
        }

    # ------------------------------------------------------------------
    # Local filesystem fallback
    # ------------------------------------------------------------------

    async def _local_upload(self, file_bytes: bytes, filename: str) -> str:
        """Save to local filesystem and return a relative path."""
        file_path = self._local_dir / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(file_bytes)
        logger.info("Saved locally: %s (%d bytes)", file_path, len(file_bytes))
        return str(file_path)

    def _local_download(self, url_or_path: str) -> bytes:
        """Read a file from local storage."""
        # Extract filename from URL path
        path = Path(url_or_path.split("?")[0])
        if not path.is_absolute():
            path = self._local_dir / path.name
        if not path.exists():
            raise FileNotFoundError(f"Local file not found: {path}")
        return path.read_bytes()


# Module-level singleton
storage = StorageService()
