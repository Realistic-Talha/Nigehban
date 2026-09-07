"""WhatsApp webhook endpoints — verification and message handling.

Handles inbound messages from the Meta WhatsApp Cloud API and routes
them to the appropriate analysis pipeline for internal analysts.
"""

import hashlib
import logging
import uuid
from typing import Any

from fastapi import APIRouter, Query, Request, Response

from app.core.config import settings
from app.core.redis import redis_pool
from app.services.ocr import ocr_service
from app.services.storage import storage
from app.services.whatsapp import whatsapp_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook/whatsapp")


# ---------------------------------------------------------------------------
# Webhook verification (Meta GET callback)
# ---------------------------------------------------------------------------

@router.get("")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
) -> Response:
    """Meta webhook verification callback.

    Meta sends a GET request with hub.mode, hub.verify_token, and hub.challenge.
    We must return the challenge string if the token matches.
    """
    if hub_mode == "subscribe" and hub_token == settings.WHATSAPP_VERIFY_TOKEN:
        logger.info("WhatsApp webhook verified successfully")
        return Response(content=hub_challenge, media_type="text/plain")
    return Response(status_code=403, content="Forbidden")


# ---------------------------------------------------------------------------
# Inbound message processing (Meta POST callback)
# ---------------------------------------------------------------------------

@router.post("")
async def receive_message(request: Request) -> dict:
    """Process inbound WhatsApp messages from the Meta Cloud API.

    Parses the webhook payload, extracts sender and message details,
    and routes to the appropriate pipeline.
    """
    payload = await request.json()

    try:
        entries = _parse_entries(payload)
    except Exception:
        logger.error("Failed to parse WhatsApp webhook payload", exc_info=True)
        return {"status": "error", "detail": "parse_error"}

    for entry in entries:
        for change in entry.get("changes", []):
            value = change.get("value", {})
            messages = value.get("messages", [])

            for message in messages:
                try:
                    await _handle_message(message, value)
                except Exception:
                    logger.error(
                        "Failed to handle WhatsApp message %s",
                        message.get("id", "unknown"),
                        exc_info=True,
                    )

    # Always return 200 quickly — Meta retries on non-200
    return {"status": "received"}


# ---------------------------------------------------------------------------
# Payload parsing
# ---------------------------------------------------------------------------

def _parse_entries(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract the entry list from the Meta webhook payload.

    Meta Cloud API payload structure:
    {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "<waba_id>",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": { "display_phone_number": "...", "phone_number_id": "..." },
                    "contacts": [{ "profile": { "name": "..." }, "wa_id": "..." }],
                    "messages": [{ ... }]
                },
                "field": "messages"
            }]
        }]
    }
    """
    if payload.get("object") != "whatsapp_business_account":
        logger.debug("Ignoring non-WhatsApp webhook event: %s", payload.get("object"))
        return []

    return payload.get("entry", [])


# ---------------------------------------------------------------------------
# Message handler
# ---------------------------------------------------------------------------

async def _handle_message(message: dict[str, Any], value: dict[str, Any]) -> None:
    """Route a single inbound message to the correct pipeline."""
    sender_phone = message.get("from", "")
    message_type = message.get("type", "text")
    message_id = message.get("id", "")

    logger.info(
        "WhatsApp message received | sender=%s type=%s msg_id=%s",
        sender_phone, message_type, message_id,
    )

    # Check if this is a first-time analyst → send welcome
    is_new = await _check_first_contact(sender_phone)
    if is_new:
        await whatsapp_client.send_text_message(
            sender_phone,
            whatsapp_client.format_welcome_message(),
        )

    # Route by message type
    match message_type:
        case "text":
            text_body = message.get("text", {}).get("body", "")
            if text_body:
                await _route_text_message(sender_phone, text_body)

        case "image":
            media_id = message.get("image", {}).get("id", "")
            caption = message.get("image", {}).get("caption", "")
            if media_id:
                await _route_image_message(sender_phone, media_id, caption)

        case "video":
            media_id = message.get("video", {}).get("id", "")
            caption = message.get("video", {}).get("caption", "")
            if media_id:
                await _route_video_message(sender_phone, media_id, caption)

        case "document":
            # Analysts might send documents/PDFs for analysis
            media_id = message.get("document", {}).get("id", "")
            filename = message.get("document", {}).get("filename", "")
            if media_id:
                await whatsapp_client.send_text_message(
                    sender_phone,
                    f"📄 Document received: *{filename}*\n"
                    "Document analysis is queued. You'll be notified when results are ready.",
                )

        case "interactive":
            # Handle button replies from interactive messages
            button_reply = message.get("interactive", {}).get("button_reply", {})
            button_id = button_reply.get("id", "")
            await _handle_button_reply(sender_phone, button_id)

        case _:
            await whatsapp_client.send_text_message(
                sender_phone,
                f"⚠️ Message type '{message_type}' is not yet supported for analysis.\n"
                "Please send text, image, or video.",
            )


# ---------------------------------------------------------------------------
# Routing helpers
# ---------------------------------------------------------------------------

async def _route_text_message(phone: str, text: str) -> None:
    """Auto-detect language and route text to scamcheck or factcheck."""
    from app.agents.orchestrator import pipeline
    from app.workers.tasks import run_pipeline_task

    import asyncio

    # Language detection
    language = ocr_service.detect_language(text)

    # Simple heuristic to decide routing:
    # - Short texts with URLs or money amounts → likely scam
    # - Longer declarative statements → likely fact-check claim
    is_scam_suspect = _looks_like_scam(text)
    check_type = "scam_report" if is_scam_suspect else "claim"
    check_id = str(uuid.uuid4())

    # Acknowledge immediately
    route_label = "Scam Analysis" if is_scam_suspect else "Fact-Check"
    await whatsapp_client.send_text_message(
        phone,
        f"🔄 Received — routing to *{route_label}* pipeline.\n"
        f"Language detected: {'Urdu' if language == 'ur' else 'English'}\n"
        "Results will follow shortly.",
    )

    input_data = {
        "text": text,
        "language": language,
        "source": "whatsapp",
        "reporter_phone": phone,
    }

    # Run pipeline in background
    asyncio.create_task(run_pipeline_task(check_id, check_type, input_data))

    # Wait briefly and try to send result (pipeline may still be running)
    asyncio.create_task(_send_result_when_ready(phone, check_id, check_type, language))


async def _route_image_message(phone: str, media_id: str, caption: str) -> None:
    """Download image, store, and route to mediacheck + scamcheck (if text present)."""
    from app.workers.tasks import run_pipeline_task

    import asyncio

    # Download the media
    try:
        image_bytes = await whatsapp_client.download_media(media_id)
    except Exception:
        logger.error("Failed to download WhatsApp media %s", media_id, exc_info=True)
        await whatsapp_client.send_text_message(phone, "❌ Failed to download the image. Please try again.")
        return

    # Upload to storage
    media_url = await storage.upload_file(image_bytes, f"wa_{media_id}.jpg", "image/jpeg")

    # OCR extraction
    extracted_text = await ocr_service.extract_text(image_bytes)
    language = ocr_service.detect_language(extracted_text or caption)

    # If there's meaningful text (caption + OCR), also run scamcheck
    text_content = caption or extracted_text
    has_text = bool(text_content and len(text_content.strip()) > 10)

    check_id = str(uuid.uuid4())
    check_type = "media_check"

    await whatsapp_client.send_text_message(
        phone,
        f"🖼️ Image received — starting *Media Analysis*.\n"
        f"OCR extracted: {'Yes (' + str(len(extracted_text)) + ' chars)' if extracted_text else 'No text found'}\n"
        f"Language: {'Urdu' if language == 'ur' else 'English'}\n"
        "Results will follow shortly.",
    )

    input_data = {
        "text": text_content,
        "media_url": media_url,
        "media_type": "image",
        "language": language,
        "source": "whatsapp",
        "reporter_phone": phone,
        "extracted_text": extracted_text,
    }

    asyncio.create_task(run_pipeline_task(check_id, check_type, input_data))
    asyncio.create_task(_send_result_when_ready(phone, check_id, check_type, language))

    # If significant text found, also run a parallel scamcheck
    if has_text:
        scam_check_id = str(uuid.uuid4())
        scam_input = {
            "text": text_content,
            "language": language,
            "source": "whatsapp_ocr",
            "reporter_phone": phone,
        }
        asyncio.create_task(run_pipeline_task(scam_check_id, "scam_report", scam_input))


async def _route_video_message(phone: str, media_id: str, caption: str) -> None:
    """Download video and route to mediacheck for deepfake/manipulation analysis."""
    from app.workers.tasks import run_pipeline_task

    import asyncio

    await whatsapp_client.send_text_message(
        phone,
        "🎬 Video received — downloading and queuing for *Deepfake / Manipulation Analysis*.\n"
        "This may take a few minutes depending on file size.",
    )

    try:
        video_bytes = await whatsapp_client.download_media(media_id)
    except Exception:
        logger.error("Failed to download WhatsApp video %s", media_id, exc_info=True)
        await whatsapp_client.send_text_message(phone, "❌ Failed to download the video. Please try a smaller file.")
        return

    media_url = await storage.upload_file(video_bytes, f"wa_{media_id}.mp4", "video/mp4")

    check_id = str(uuid.uuid4())
    input_data = {
        "text": caption,
        "media_url": media_url,
        "media_type": "video",
        "language": ocr_service.detect_language(caption),
        "source": "whatsapp",
        "reporter_phone": phone,
    }

    asyncio.create_task(run_pipeline_task(check_id, "media_check", input_data))
    asyncio.create_task(
        _send_result_when_ready(phone, check_id, "media_check", input_data["language"])
    )


# ---------------------------------------------------------------------------
# Button / interactive reply handler
# ---------------------------------------------------------------------------

async def _handle_button_reply(phone: str, button_id: str) -> None:
    """Handle replies from interactive button messages."""
    match button_id:
        case "more_details":
            await whatsapp_client.send_text_message(
                phone,
                "📋 Fetching additional details…\n"
                "Full analysis report is available on the Nigehban dashboard.",
            )
        case "mark_false_positive":
            await whatsapp_client.send_text_message(
                phone,
                "✓ Flagged as false positive. The team will review this during the next audit cycle.",
            )
        case "escalate":
            await whatsapp_client.send_text_message(
                phone,
                "🔺 Escalated to senior analysts. You'll be notified when someone picks this up.",
            )
        case _:
            logger.debug("Unknown button reply: %s", button_id)


# ---------------------------------------------------------------------------
# Result delivery
# ---------------------------------------------------------------------------

async def _send_result_when_ready(
    phone: str,
    check_id: str,
    check_type: str,
    language: str,
    max_wait_seconds: int = 120,
    poll_interval: int = 5,
) -> None:
    """Poll Redis for the pipeline result and send it when ready.

    The pipeline publishes to ``pipeline:{check_id}`` when complete.
    We subscribe and wait for the ``pipeline_complete`` event.
    """
    import asyncio
    import json

    try:
        client = redis_pool.client
        pubsub = client.pubsub()
        channel = f"pipeline:{check_id}"
        await pubsub.subscribe(channel)

        elapsed = 0
        async for msg in pubsub.listen():
            if msg["type"] != "message":
                continue

            data = json.loads(msg["data"])
            if data.get("status") == "pipeline_complete":
                # Fetch the full verdict from the database
                verdict = await _fetch_verdict(check_id, check_type)
                if verdict:
                    formatted = whatsapp_client.format_verdict_message(verdict, language)
                    await whatsapp_client.send_text_message(phone, formatted)

                    # Send action buttons for analysts
                    await whatsapp_client.send_interactive_buttons(
                        phone,
                        "What would you like to do?",
                        [
                            {"id": "more_details", "title": "📋 Details"},
                            {"id": "mark_false_positive", "title": "✓ False Positive"},
                            {"id": "escalate", "title": "🔺 Escalate"},
                        ],
                    )
                else:
                    await whatsapp_client.send_text_message(
                        phone,
                        "⚠️ Analysis complete but results could not be retrieved. "
                        "Check the Nigehban dashboard.",
                    )
                break

            elapsed += poll_interval
            if elapsed >= max_wait_seconds:
                await whatsapp_client.send_text_message(
                    phone,
                    "⏳ Analysis is still running. You'll be notified when results are ready. "
                    "You can also check the Nigehban dashboard for updates.",
                )
                break

        await pubsub.unsubscribe(channel)
        await pubsub.aclose()
    except Exception:
        logger.error("Failed to deliver result for %s", check_id, exc_info=True)


async def _fetch_verdict(check_id: str, check_type: str) -> dict[str, Any] | None:
    """Fetch the completed verdict from the database."""
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        if check_type == "claim":
            from app.models.claim import Claim
            stmt = select(Claim).where(Claim.id == check_id)
            record = (await session.execute(stmt)).scalar_one_or_none()
            if record:
                return {
                    "id": str(record.id),
                    "type": "claim",
                    "verdict": record.verdict,
                    "confidence": record.confidence_score or 0,
                    "explanation_en": record.explanation_en,
                    "explanation_ur": record.explanation_ur,
                    "sources": record.sources or [],
                }
        elif check_type == "scam_report":
            from app.models.scam_report import ScamReport
            stmt = select(ScamReport).where(ScamReport.id == check_id)
            record = (await session.execute(stmt)).scalar_one_or_none()
            if record:
                return {
                    "id": str(record.id),
                    "type": "scam_report",
                    "verdict": record.risk_verdict,
                    "confidence": record.confidence_score or 0,
                    "explanation_en": record.explanation_en,
                    "explanation_ur": record.explanation_ur,
                    "sources": [],
                }
        elif check_type == "media_check":
            from app.models.media_check import MediaCheck
            stmt = select(MediaCheck).where(MediaCheck.id == check_id)
            record = (await session.execute(stmt)).scalar_one_or_none()
            if record:
                return {
                    "id": str(record.id),
                    "type": "media_check",
                    "verdict": record.verdict,
                    "confidence": record.authenticity_score or 0,
                    "explanation_en": record.explanation_en,
                    "explanation_ur": record.explanation_ur,
                    "sources": [],
                }
    return None


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

async def _check_first_contact(phone: str) -> bool:
    """Check if this phone number is contacting us for the first time.

    Uses Redis to track known analyst phone numbers.
    """
    try:
        client = redis_pool.client
        key = f"wa:known:{phone}"
        exists = await client.exists(key)
        if not exists:
            # Mark as known with 30-day TTL
            await client.setex(key, 30 * 24 * 3600, "1")
            return True
        return False
    except Exception:
        logger.warning("Redis check failed for %s", phone, exc_info=True)
        return False


def _looks_like_scam(text: str) -> bool:
    """Heuristic to decide if a text message looks more like a scam than a claim.

    Checks for common scam indicators:
    - URLs / links
    - Money amounts or financial terms
    - Urgency language
    - Phone numbers in text
    - Short messages (< 50 chars are more likely forwarded scam messages)
    """
    text_lower = text.lower()

    scam_signals = [
        "http://" in text_lower or "https://" in text_lower or "www." in text_lower,
        any(kw in text_lower for kw in [
            "rs ", "pkr ", "rs.", "lac", "lakh", "crore", "crores",
            "bank account", "cnic", "nadra", "prize", "lottery",
            "click here", "click now", "urgent", "immediately",
            "verify your", "confirm your", "suspicious activity",
        ]),
        any(kw in text_lower for kw in [
            "free ", "winner", "congratulations", "selected",
            "limited time", "offer ends",
        ]),
        # Phone number pattern in text
        bool(__import__("re").search(r"\b0?3\d{2}[- ]?\d{7}\b", text)),
        len(text.strip()) < 50,
    ]

    # If 2+ signals fire, classify as scam-suspect
    return sum(scAM for scAM in scam_signals) >= 2
