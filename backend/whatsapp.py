# Copyright (c) 2026 Smart Touch Infotech Private Limited. All rights reserved.
# SAM (Smart Analyst for Markets) — Proprietary Software

"""WhatsApp integration via Twilio — receive messages, route through SAM AI agent, reply."""
import os
import re
import logging
from twilio.rest import Client
from twilio.request_validator import RequestValidator

logger = logging.getLogger(__name__)

# Twilio config from environment
ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER", "")
ALLOWED_NUMBERS = [n.strip() for n in os.getenv("TWILIO_ALLOWED_NUMBERS", "").split(",") if n.strip()]

# Initialize Twilio client
client: Client | None = None
validator: RequestValidator | None = None

if ACCOUNT_SID and AUTH_TOKEN:
    client = Client(ACCOUNT_SID, AUTH_TOKEN)
    validator = RequestValidator(AUTH_TOKEN)
    logger.info("Twilio WhatsApp client initialized")
else:
    logger.warning("Twilio credentials not set — WhatsApp disabled")


# Per-user conversation history (keyed by phone number)
_conversations: dict[str, list[dict]] = {}
MAX_HISTORY = 20  # Keep last 20 messages per user


def is_enabled() -> bool:
    """Check if WhatsApp integration is configured."""
    return client is not None and bool(WHATSAPP_NUMBER)


def is_allowed(phone: str) -> bool:
    """Check if phone number is in allowlist. If no allowlist set, allow all (sandbox mode)."""
    if not ALLOWED_NUMBERS:
        return True  # No allowlist = sandbox mode, allow all
    return phone in ALLOWED_NUMBERS


def validate_request(url: str, params: dict, signature: str) -> bool:
    """Validate that the incoming webhook is from Twilio."""
    if not validator:
        return False
    return validator.validate(url, params, signature)


def get_conversation(phone: str) -> list[dict]:
    """Get or create conversation history for a phone number."""
    if phone not in _conversations:
        _conversations[phone] = []
    return _conversations[phone]


def add_message(phone: str, role: str, content: str):
    """Add a message to conversation history."""
    history = get_conversation(phone)
    history.append({"role": role, "content": content})
    # Trim to max history
    if len(history) > MAX_HISTORY:
        _conversations[phone] = history[-MAX_HISTORY:]


def send_message(to: str, body: str) -> str | None:
    """Send a WhatsApp message via Twilio. Returns message SID or None on error."""
    if not client or not WHATSAPP_NUMBER:
        logger.error("Twilio not configured — cannot send WhatsApp message")
        return None

    try:
        # Convert markdown to WhatsApp format
        body = md_to_whatsapp(body)

        # Truncate if over WhatsApp limit (1600 chars)
        if len(body) > 1600:
            body = body[:1570] + "\n\n_(truncated)_"

        message = client.messages.create(
            from_=f"whatsapp:{WHATSAPP_NUMBER}",
            to=f"whatsapp:{to}",
            body=body,
        )
        logger.info(f"WhatsApp sent to {to}: SID={message.sid}")
        return message.sid
    except Exception as e:
        logger.error(f"WhatsApp send error to {to}: {e}")
        return None


def md_to_whatsapp(text: str) -> str:
    """Convert markdown formatting to WhatsApp-compatible formatting.

    Markdown → WhatsApp:
      **bold** or __bold__  → *bold*
      *italic* or _italic_  → _italic_
      ~~strike~~            → ~strike~
      `code`                → `code`
      ```code block```      → ```code block```
      # Header              → *Header*
      ## Header             → *Header*
      ### Header            → *Header*
      [text](url)           → text (url)
      ![alt](url)           → (removed)
      | table |             → plain text rows
      ---                   → (removed)
    """
    if not text:
        return text

    lines = text.split("\n")
    result = []
    in_code_block = False
    in_table = False
    table_rows = []

    for line in lines:
        # Toggle code blocks — pass through as-is
        if line.strip().startswith("```"):
            if in_code_block:
                in_code_block = False
                result.append("```")
            else:
                in_code_block = True
                result.append("```")
            continue

        if in_code_block:
            result.append(line)
            continue

        # Table handling
        if "|" in line and line.strip().startswith("|"):
            stripped = line.strip()
            # Skip separator rows (|---|---|)
            if re.match(r"^\|[\s\-:|]+\|$", stripped):
                continue
            # Parse table cells
            cells = [c.strip() for c in stripped.split("|")]
            cells = [c for c in cells if c]  # remove empty from leading/trailing |
            if not in_table:
                in_table = True
                # First row is header — bold it
                result.append("*" + " | ".join(cells) + "*")
            else:
                result.append(" | ".join(cells))
            continue
        else:
            in_table = False

        # Remove horizontal rules
        if re.match(r"^[\s]*[-*_]{3,}[\s]*$", line):
            continue

        # Headers → bold
        line = re.sub(r"^#{1,6}\s+(.+)$", r"*\1*", line)

        # Images → remove
        line = re.sub(r"!\[([^\]]*)\]\([^)]+\)", "", line)

        # Links [text](url) → text (url)
        line = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", line)

        # Bold: **text** or __text__ → *text*
        line = re.sub(r"\*\*(.+?)\*\*", r"*\1*", line)
        line = re.sub(r"__(.+?)__", r"*\1*", line)

        # Italic: standalone _text_ is already WhatsApp-compatible
        # But markdown *text* (single) needs → _text_ (only if not already bold)
        # Avoid converting * that are part of bold *...*
        # Single *text* that isn't bold → _text_
        line = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"_\1_", line)

        # Strikethrough: ~~text~~ → ~text~
        line = re.sub(r"~~(.+?)~~", r"~\1~", line)

        # Blockquote: > text → > text (already supported in WhatsApp)

        result.append(line)

    return "\n".join(result).strip()


def clear_conversation(phone: str):
    """Clear conversation history for a phone number."""
    _conversations.pop(phone, None)
