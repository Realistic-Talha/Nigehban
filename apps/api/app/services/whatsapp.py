"""WhatsApp Business Cloud API client for internal analyst communication."""

import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# Verdict emoji mapping used across the bot
VERDICT_EMOJI: dict[str, str] = {
    # Scam-check verdicts
    "safe": "✅",
    "low_risk": "✅",
    "needs_caution": "⚠️",
    "medium_risk": "⚠️",
    "scam": "🚨",
    "high_risk": "🚨",
    # Fact-check verdicts
    "true": "✓",
    "mostly_true": "✓",
    "partly_true": "⚠️",
    "misleading": "⚠️",
    "mostly_false": "✗",
    "false": "✗",
    # Media-check verdicts
    "authentic": "✅",
    "manipulated": "🚨",
    "deepfake": "🚨",
    "inconclusive": "⚠️",
    # Generic
    "unverified": "⚠️",
    "error": "❌",
}

_GRAPH_API_BASE = "https://graph.facebook.com/v19.0"


class WhatsAppClient:
    """Async client for the Meta WhatsApp Business Cloud API.

    Used to send analysis results and notifications to internal analysts
    via WhatsApp.
    """

    def __init__(self) -> None:
        self._token = settings.WHATSAPP_TOKEN
        self._phone_number_id = settings.WHATSAPP_PHONE_NUMBER_ID
        self._base_url = f"{_GRAPH_API_BASE}/{self._phone_number_id}"

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------------
    # Outbound messages
    # ------------------------------------------------------------------

    async def send_text_message(self, phone: str, text: str) -> dict[str, Any]:
        """Send a plain text message to an analyst's WhatsApp number.

        Parameters
        ----------
        phone : E.164 formatted phone number (e.g. "+923001234567")
        text  : Message body (max 4096 chars for text messages).
        """
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": phone,
            "type": "text",
            "text": {"preview_url": False, "body": text[:4096]},
        }
        return await self._post("messages", payload)

    async def send_template_message(
        self,
        phone: str,
        template_name: str,
        params: list[dict[str, str]],
        language_code: str = "en",
    ) -> dict[str, Any]:
        """Send a pre-approved template message.

        Parameters
        ----------
        phone         : E.164 formatted phone number.
        template_name : Name of the Meta-approved template.
        params        : List of component parameter dicts, e.g.
                        [{"type": "text", "text": "value"}].
        language_code : BCP-47 language code (default "en").
        """
        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language_code},
                "components": [
                    {
                        "type": "body",
                        "parameters": params,
                    }
                ],
            },
        }
        return await self._post("messages", payload)

    async def send_interactive_buttons(
        self,
        phone: str,
        body_text: str,
        buttons: list[dict[str, str]],
    ) -> dict[str, Any]:
        """Send an interactive message with up to 3 reply buttons.

        Parameters
        ----------
        body_text : Message body shown above the buttons.
        buttons   : List of {"id": "...", "title": "..."} dicts (max 3).
        """
        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": body_text[:1024]},
                "action": {
                    "buttons": [
                        {"type": "reply", "reply": {"id": b["id"], "title": b["title"][:20]}}
                        for b in buttons[:3]
                    ]
                },
            },
        }
        return await self._post("messages", payload)

    # ------------------------------------------------------------------
    # Media
    # ------------------------------------------------------------------

    async def download_media(self, media_id: str) -> bytes:
        """Download a media file (image/video/document) by its WhatsApp media ID.

        Returns the raw bytes of the media file.
        """
        # Step 1: get the media URL
        async with httpx.AsyncClient(timeout=30.0) as client:
            meta_resp = await client.get(
                f"{_GRAPH_API_BASE}/{media_id}",
                headers=self._headers,
            )
            meta_resp.raise_for_status()
            media_url = meta_resp.json().get("url", "")

            if not media_url:
                raise ValueError(f"No download URL for media_id={media_id}")

            # Step 2: download the actual file
            file_resp = await client.get(media_url, headers=self._headers)
            file_resp.raise_for_status()
            return file_resp.content

    # ------------------------------------------------------------------
    # Formatting helpers
    # ------------------------------------------------------------------

    @staticmethod
    def format_verdict_message(verdict: dict[str, Any], language: str = "en") -> str:
        """Format a pipeline verdict dict into a WhatsApp-friendly plain-text message.

        Uses emoji indicators for quick visual scanning by analysts.
        """
        verdict_label = verdict.get("verdict", "unverified").lower().replace("_", " ")
        emoji = VERDICT_EMOJI.get(verdict.get("verdict", ""), "⚠️")
        confidence = verdict.get("confidence", 0)

        explanation_key = "explanation_ur" if language == "ur" else "explanation_en"
        explanation = verdict.get(explanation_key) or verdict.get("explanation_en", "No details available.")

        sources = verdict.get("sources") or []
        source_lines = ""
        if sources:
            source_lines = "\n📎 Sources:\n" + "\n".join(
                f"  • {s}" if isinstance(s, str) else f"  • {s.get('url', s.get('title', str(s)))}"
                for s in sources[:5]
            )

        check_type = verdict.get("type", "check").replace("_", " ").title()

        lines = [
            f"{emoji} *Nigehban — {check_type} Result*",
            "",
            f"Verdict: *{verdict_label.upper()}*",
            f"Confidence: {confidence:.0f}%",
            "",
            explanation,
            source_lines,
            "",
            f"ID: `{verdict.get('id', 'N/A')}`",
        ]
        return "\n".join(lines)

    @staticmethod
    def format_welcome_message() -> str:
        """Welcome/onboarding message for internal analysts joining the WhatsApp channel."""
        return (
            "🛡️ *Nigehban Analyst Bot*\n\n"
            "Welcome to the internal analysis channel.\n\n"
            "*Commands:*\n"
            "• Send any *text* → auto-routed to scam-check or fact-check\n"
            "• Send an *image* → media analysis + OCR extraction\n"
            "• Send a *video link* → deepfake / manipulation check\n\n"
            "Results will be delivered here with verdict indicators:\n"
            "✅ Safe / Authentic / True\n"
            "⚠️ Caution / Unverified / Partly True\n"
            "🚨 Scam / Manipulated / Deepfake\n"
            "✗ False / Debunked\n\n"
            "All submissions are logged for team review."
        )

    # ------------------------------------------------------------------
    # Internal HTTP helper
    # ------------------------------------------------------------------

    async def _post(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        """POST to the WhatsApp Graph API and return the JSON response."""
        url = f"{self._base_url}/{endpoint}"
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url, json=payload, headers=self._headers)
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "WhatsApp API %s failed [%s]: %s",
                endpoint, exc.response.status_code, exc.response.text,
            )
            return {"error": exc.response.status_code, "detail": exc.response.text}
        except httpx.RequestError as exc:
            logger.error("WhatsApp API %s request error: %s", endpoint, exc)
            return {"error": "request_error", "detail": str(exc)}


# Module-level singleton
whatsapp_client = WhatsAppClient()
