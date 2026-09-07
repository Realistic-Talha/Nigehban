"""OCR service with English + Urdu (Nastaliq) text extraction."""

import io
import logging
import re
import unicodedata

import httpx
from PIL import Image

logger = logging.getLogger(__name__)

# Lazy/soft import — pytesseract may pull pandas and break on numpy ABI mismatches.
_HAS_TESSERACT = False
pytesseract = None  # type: ignore
try:
    import pytesseract as _pt

    pytesseract = _pt
    _HAS_TESSERACT = True
except Exception:
    logger.warning("pytesseract unavailable — OCR will return empty results")


class OCRService:
    """Extract text from images with support for English and Urdu scripts.

    Uses Tesseract OCR when available. Falls back to an empty result with
    a warning if Tesseract is not installed (useful during development).
    """

    # Tesseract language codes
    LANG_ENGLISH = "eng"
    LANG_URDU = "urd"
    LANG_BOTH = "eng+urd"

    async def extract_text(
        self,
        image_bytes: bytes,
        language: str = "eng+urd",
    ) -> str:
        """Extract text from raw image bytes.

        Parameters
        ----------
        image_bytes : Raw image data (JPEG, PNG, etc.).
        language    : Tesseract language code(s), e.g. "eng", "urd", "eng+urd".

        Returns
        -------
        Cleaned and normalized extracted text.
        """
        if not _HAS_TESSERACT:
            logger.warning("Tesseract not available — returning empty OCR result")
            return ""

        try:
            image = Image.open(io.BytesIO(image_bytes))
            image = self._preprocess_image(image)

            # Run OCR
            raw_text = pytesseract.image_to_string(image, lang=language)

            return self._clean_text(raw_text)
        except Exception:
            logger.error("OCR extraction failed", exc_info=True)
            return ""

    async def extract_text_from_url(self, url: str, language: str = "eng+urd") -> str:
        """Download an image from a URL and extract text from it.

        Parameters
        ----------
        url      : HTTP(S) URL of the image.
        language : Tesseract language code(s).

        Returns
        -------
        Cleaned and normalized extracted text.
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                return await self.extract_text(resp.content, language=language)
        except httpx.HTTPError:
            logger.error("Failed to download image from %s", url, exc_info=True)
            return ""

    # ------------------------------------------------------------------
    # Image preprocessing
    # ------------------------------------------------------------------

    @staticmethod
    def _preprocess_image(image: Image.Image) -> Image.Image:
        """Apply basic preprocessing to improve OCR accuracy.

        - Convert to RGB if needed
        - Resize very small images up
        - Convert to grayscale for better Tesseract performance
        """
        # Ensure RGB mode
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")

        # Upscale tiny images (< 200px on shortest side)
        w, h = image.size
        min_dim = min(w, h)
        if min_dim < 200:
            scale = 200 / min_dim
            image = image.resize(
                (int(w * scale), int(h * scale)),
                Image.Resampling.LANCZOS,
            )

        # Convert to grayscale — usually improves Tesseract accuracy
        image = image.convert("L")

        return image

    # ------------------------------------------------------------------
    # Text cleaning
    # ------------------------------------------------------------------

    @staticmethod
    def _clean_text(text: str) -> str:
        """Clean and normalize OCR output text.

        - Unicode normalization (NFC for Urdu compatibility)
        - Collapse excessive whitespace
        - Strip control characters (but keep newlines and Urdu marks)
        - Remove common Tesseract artifacts
        """
        if not text:
            return ""

        # Unicode normalization
        text = unicodedata.normalize("NFC", text)

        # Remove null bytes and other control chars except \n, \r, \t
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

        # Collapse multiple spaces into one (preserve newlines)
        text = re.sub(r"[^\S\n]+", " ", text)

        # Collapse 3+ consecutive newlines into 2
        text = re.sub(r"\n{3,}", "\n\n", text)

        # Remove common Tesseract noise patterns
        text = re.sub(r"^\s*[-=_]{3,}\s*$", "", text, flags=re.MULTILINE)

        return text.strip()

    @staticmethod
    def detect_language(text: str) -> str:
        """Simple heuristic to detect if text is primarily Urdu or English.

        Returns "ur" or "en".
        """
        if not text:
            return "en"

        # Count Urdu/Arabic script characters (Unicode range 0x0600–0x06FF, 0x0750–0x077F, 0xFB50–0xFDFF, 0xFE70–0xFEFF)
        urdu_chars = sum(
            1 for ch in text
            if "\u0600" <= ch <= "\u06ff"
            or "\u0750" <= ch <= "\u077f"
            or "\ufb50" <= ch <= "\ufdff"
            or "\ufe70" <= ch <= "\ufeff"
        )
        latin_chars = sum(1 for ch in text if ch.isascii() and ch.isalpha())

        total = urdu_chars + latin_chars
        if total == 0:
            return "en"

        return "ur" if (urdu_chars / total) > 0.3 else "en"


# Module-level singleton
ocr_service = OCRService()
