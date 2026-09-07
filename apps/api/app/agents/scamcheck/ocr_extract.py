"""OCRExtractAgent — extract text from images using Tesseract OCR."""

import io
import logging
from typing import Any

from app.agents.base import BaseAgent

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompt for OCR cleanup
# ---------------------------------------------------------------------------

CLEANUP_PROMPT = """\
You are an OCR text cleanup specialist for Nigehban, a Pakistani scam-detection platform.

You will receive raw OCR output extracted from an image. The text may contain:
- Encoding artifacts (mojibake, garbled characters)
- OCR misrecognitions (e.g., '0' vs 'O', '1' vs 'l')
- Mixed English and Urdu text
- Noise from image backgrounds or watermarks

Your job:
1. Clean up the OCR output — fix encoding issues, normalize whitespace, correct obvious
   OCR errors based on context.
2. Detect the primary language of the text.
3. Preserve the original meaning — do NOT add, remove, or paraphrase content.

Return ONLY valid JSON (no markdown fences):
{
  "cleaned_text": "The cleaned and normalized text",
  "language_detected": "en | ur | mixed",
  "cleanup_notes": "Brief notes on what was corrected"
}
"""


# ---------------------------------------------------------------------------
# Agent implementation
# ---------------------------------------------------------------------------

class OCRExtractAgent(BaseAgent):
    """Extract text from images using Tesseract OCR with bilingual support.

    Processes images with both English (eng) and Urdu (urd) Tesseract language
    packs, then uses Haiku to clean up the raw OCR output.
    """

    name: str = "ocr_extraction"
    model_tier: str = "haiku"
    timeout: float = 30.0

    async def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Extract and clean text from an image.

        Args:
            input_data: Dict with keys:
                - image_path (str, optional): Filesystem path to the image.
                - image_bytes (bytes, optional): Raw image bytes.
                - media_url (str, optional): URL of the image (for future use).

        Returns:
            Dict with keys:
                - extracted_text (str): Cleaned OCR text.
                - language_detected (str): "en", "ur", or "mixed".
                - ocr_confidence (float): Raw OCR confidence 0.0–1.0.
                - confidence (int): Overall confidence 0–100.
        """
        image_path = input_data.get("image_path")
        image_bytes = input_data.get("image_bytes")
        media_url = input_data.get("media_url")

        if not image_path and not image_bytes and media_url:
            try:
                from app.services.ocr import ocr_service
                from app.services.storage import storage

                if str(media_url).startswith("http://") or str(media_url).startswith("https://"):
                    raw_from_url = await ocr_service.extract_text_from_url(str(media_url))
                    return {
                        "extracted_text": raw_from_url,
                        "language_detected": "mixed" if raw_from_url else "unknown",
                        "ocr_confidence": 0.7 if raw_from_url else 0.0,
                        "confidence": 60 if raw_from_url else 10,
                    }
                data = await storage.download_file(str(media_url))
                image_bytes = data
            except Exception:
                logger.exception("OCR media_url fetch failed")

        if not image_path and not image_bytes:
            logger.warning("OCRExtractAgent: no image_path, image_bytes, or media_url provided")
            return {
                "extracted_text": "",
                "language_detected": "unknown",
                "ocr_confidence": 0.0,
                "confidence": 0,
            }

        try:
            raw_text, ocr_confidence = await self._run_tesseract(image_path, image_bytes)

            if not raw_text or not raw_text.strip():
                return {
                    "extracted_text": "",
                    "language_detected": "unknown",
                    "ocr_confidence": ocr_confidence,
                    "confidence": 10,
                }

            # Use Haiku to clean up OCR output
            cleanup_response = await self.call_llm(
                system_prompt=CLEANUP_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": f"Clean up this OCR output:\n\n{raw_text}",
                    },
                ],
                max_tokens=2048,
            )

            parsed = cleanup_response.get("json")
            if parsed and isinstance(parsed, dict):
                cleaned_text = parsed.get("cleaned_text", raw_text)
                language = parsed.get("language_detected", "en")
            else:
                cleaned_text = raw_text
                language = "en"

            # Blend OCR confidence with cleanup confidence
            confidence = int(ocr_confidence * 70 + 20)  # Scale 0-100
            confidence = max(0, min(100, confidence))

            return {
                "extracted_text": cleaned_text,
                "language_detected": language,
                "ocr_confidence": round(ocr_confidence, 3),
                "confidence": confidence,
            }

        except ImportError as exc:
            logger.error("OCR dependencies not installed: %s", exc)
            return {
                "extracted_text": "",
                "language_detected": "unknown",
                "ocr_confidence": 0.0,
                "confidence": 0,
                "error": f"OCR dependencies missing: {exc}",
            }

        except Exception:
            logger.exception("OCRExtractAgent failed")
            return {
                "extracted_text": "",
                "language_detected": "unknown",
                "ocr_confidence": 0.0,
                "confidence": 0,
                "error": "OCR extraction failed",
            }

    # ------------------------------------------------------------------
    # Tesseract integration
    # ------------------------------------------------------------------

    @staticmethod
    async def _run_tesseract(
        image_path: str | None,
        image_bytes: bytes | None,
    ) -> tuple[str, float]:
        """Run Tesseract OCR on the given image.

        Returns:
            Tuple of (raw_text, confidence_score).
        """
        try:
            import pytesseract
            from PIL import Image
        except ImportError as exc:
            raise ImportError(
                "pytesseract and Pillow are required for OCR. "
                "Install with: pip install pytesseract Pillow"
            ) from exc

        # Load image
        if image_bytes:
            image = Image.open(io.BytesIO(image_bytes))
        elif image_path:
            image = Image.open(image_path)
        else:
            return "", 0.0

        # Run OCR with English + Urdu
        try:
            raw_text = pytesseract.image_to_string(image, lang="eng+urd")
        except pytesseract.TesseractError:
            # Fallback: English only if Urdu language pack is not installed
            logger.warning("Urdu Tesseract language pack not available, using English only")
            raw_text = pytesseract.image_to_string(image, lang="eng")

        # Estimate confidence from Tesseract data
        try:
            data = pytesseract.image_to_data(image, lang="eng+urd", output_type=pytesseract.Output.DICT)
            confidences = [int(c) for c in data.get("conf", []) if str(c).lstrip("-").isdigit() and int(c) >= 0]
            avg_confidence = sum(confidences) / max(len(confidences), 1) / 100.0
        except Exception:
            avg_confidence = 0.5  # Default if confidence data unavailable

        return raw_text.strip(), avg_confidence
