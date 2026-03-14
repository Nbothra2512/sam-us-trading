# Copyright (c) 2026 Smart Touch Infotech Private Limited. All rights reserved.
# SAM (Smart Analyst for Markets) — Proprietary Software

"""WhatsApp integration via Twilio — receive messages, route through SAM AI agent, reply."""
import os
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


def clear_conversation(phone: str):
    """Clear conversation history for a phone number."""
    _conversations.pop(phone, None)
