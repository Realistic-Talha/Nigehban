"""IntakeAgent — classifies input and routes to the correct pipeline path."""

from typing import Any

from app.agents.base import BaseAgent

# ---------------------------------------------------------------------------
# System prompt for the intake classifier
# ---------------------------------------------------------------------------
INTAKE_SYSTEM_PROMPT = """\
You are Nigehban's intake classifier. Your job is to analyze user-submitted content
and determine:

1. **input_type** — What kind of content was submitted?
   - "text"     : Plain text message (forwarded message, copied claim, etc.)
   - "image"    : A photo, screenshot, meme, or graphic
   - "video"    : A video file or video link
   - "url"      : A web URL / link (news article, social media post, etc.)

2. **language** — What language is the primary content in?
   - "en"         : English
   - "ur"         : Urdu (Urdu script / Nastaliq)
   - "roman_urdu" : Roman Urdu — Urdu written in Latin/English alphabet
                     (e.g. "yeh khabar jhooti hai", "kia yeh sach hai?")
   - "mixed"      : A significant mix of English and Urdu/Roman Urdu

3. **path** — Which specialized pipeline should handle this?
   - "factcheck"  : Factual claims, news stories, political statements,
                    health/science claims, viral forwards — anything where
                    the core question is "is this true?"
   - "scamcheck"  : Financial scams, phishing attempts, fake job offers,
                    investment schemes, lottery/prize scams, suspicious
                    messages asking for money/personal info, screenshots of
                    text messages (WhatsApp chats, SMS) that look scammy
   - "mediacheck" : Images or videos where the core question is about
                    authenticity — deepfakes, manipulated photos, misattributed
                    media, out-of-context images

**Routing rules (in priority order):**
- If the input is primarily an image or video → route to "mediacheck",
  UNLESS the image appears to be a screenshot of a text message / chat /
  SMS with scam indicators (money requests, prize claims, suspicious links)
  → route to "scamcheck" instead.
- If the text content contains money-related scam patterns (prize won,
  send money, urgent payment, account verification, job offer with salary,
  investment returns) → route to "scamcheck".
- Otherwise → route to "factcheck".

4. **extracted_text** — If the input is an image that contains visible text
   (screenshot, meme with text, document photo), provide the text you can
   read from the image. For plain text input, return null.

Respond in JSON with exactly these keys:
{
  "input_type": "text" | "image" | "video" | "url",
  "language": "en" | "ur" | "roman_urdu" | "mixed",
  "path": "factcheck" | "scamcheck" | "mediacheck",
  "extracted_text": "..." | null
}
"""


class IntakeAgent(BaseAgent):
    """Classifies user input and determines the processing pipeline path."""

    name: str = "intake"
    model_tier: str = "haiku"
    timeout: float = 10.0

    async def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Classify the input and return routing decision.

        Expected input_data keys:
            - text       : str  (optional) — user-submitted text
            - media_url  : str  (optional) — URL of uploaded media
            - media_type : str  (optional) — "image" | "video" | "audio"
            - source_url : str  (optional) — original source URL
        """
        # Build user message from input fields
        parts: list[str] = []

        if text := input_data.get("text"):
            parts.append(f"SUBMITTED TEXT:\n{text}")

        if source_url := input_data.get("source_url"):
            parts.append(f"SOURCE URL: {source_url}")

        if media_url := input_data.get("media_url"):
            media_type = input_data.get("media_type", "unknown")
            parts.append(f"MEDIA ({media_type}): {media_url}")

        if not parts:
            # Fallback for empty input
            return {
                "output": {
                    "input_type": "text",
                    "language": "en",
                    "path": "factcheck",
                    "extracted_text": None,
                },
                "confidence": 50.0,
            }

        user_message = "\n\n".join(parts)
        messages = [{"role": "user", "content": user_message}]

        # Call Haiku for fast classification
        llm_result = await self.call_llm(
            system_prompt=INTAKE_SYSTEM_PROMPT,
            messages=messages,
        )

        # Parse the JSON response
        parsed = llm_result.get("json")
        if parsed and isinstance(parsed, dict):
            routing = {
                "input_type": parsed.get("input_type", "text"),
                "language": parsed.get("language", "en"),
                "path": parsed.get("path", "factcheck"),
                "extracted_text": parsed.get("extracted_text"),
            }
            confidence = 85.0
        else:
            # Fallback: heuristic classification from text
            routing = self._heuristic_classify(input_data)
            confidence = 55.0

        # Validate path value
        valid_paths = {"factcheck", "scamcheck", "mediacheck"}
        if routing["path"] not in valid_paths:
            routing["path"] = "factcheck"

        return {
            "output": routing,
            "confidence": confidence,
        }

    @staticmethod
    def _heuristic_classify(input_data: dict[str, Any]) -> dict[str, Any]:
        """Rule-based fallback when LLM JSON parsing fails."""
        text = (input_data.get("text") or "").lower()
        media_type = input_data.get("media_type", "")
        source_url = input_data.get("source_url", "")

        # Determine input type
        if media_type == "video":
            input_type = "video"
        elif media_type == "image" or (source_url and any(
            ext in source_url.lower() for ext in (".jpg", ".png", ".jpeg", ".webp", ".gif")
        )):
            input_type = "image"
        elif source_url and not text:
            input_type = "url"
        else:
            input_type = "text"

        # Determine path
        scam_keywords = [
            "prize", "won", "winner", "lottery", "send money",
            "urgent", "account verify", "investment", "returns",
            "job offer", "salary", "click here", "free money",
            "rs.", "pkr", "easypaisa", "jazzcash", "bank account",
        ]
        if input_type in ("image", "video"):
            path = "mediacheck"
        elif any(kw in text for kw in scam_keywords):
            path = "scamcheck"
        else:
            path = "factcheck"

        return {
            "input_type": input_type,
            "language": "en",
            "path": path,
            "extracted_text": None,
        }
