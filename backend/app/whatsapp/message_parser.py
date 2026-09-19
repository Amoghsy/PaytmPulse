"""
Paytm Pulse - Phase 7 WhatsApp Message Parser
Extracts standardized inbound messages from Meta WhatsApp Cloud API webhook events.
"""

import logging
from typing import Dict, Any, Optional
from app.whatsapp.schemas import ParsedInboundMessage

logger = logging.getLogger("paytm_pulse.whatsapp.parser")


def parse_whatsapp_webhook_payload(payload: Dict[str, Any]) -> Optional[ParsedInboundMessage]:
    """
    Parses a raw WhatsApp Webhook JSON payload into a structured `ParsedInboundMessage`.
    Returns None if payload is not a valid incoming user message (e.g. status updates).
    """
    try:
        entries = payload.get("entry", [])
        if not entries:
            return None

        for entry in entries:
            changes = entry.get("changes", [])
            for change in changes:
                value = change.get("value", {})
                messages = value.get("messages", [])
                if not messages:
                    # Could be a status update (sent/delivered/read)
                    continue

                msg = messages[0]
                msg_id = msg.get("id", "")
                sender_phone = msg.get("from", "")
                timestamp = msg.get("timestamp", "")
                msg_type = msg.get("type", "unknown")

                text_content: Optional[str] = None
                audio_id: Optional[str] = None
                button_payload: Optional[str] = None
                button_title: Optional[str] = None

                if msg_type == "text":
                    text_content = msg.get("text", {}).get("body", "").strip()

                elif msg_type == "audio" or msg_type == "voice":
                    audio_id = msg.get("audio", {}).get("id") or msg.get("voice", {}).get("id")

                elif msg_type == "interactive":
                    interactive = msg.get("interactive", {})
                    i_type = interactive.get("type")
                    if i_type == "button_reply":
                        reply = interactive.get("button_reply", {})
                        button_payload = reply.get("id")
                        button_title = reply.get("title")
                    elif i_type == "list_reply":
                        reply = interactive.get("list_reply", {})
                        button_payload = reply.get("id")
                        button_title = reply.get("title")

                elif msg_type == "button":
                    btn = msg.get("button", {})
                    button_payload = btn.get("payload")
                    button_title = btn.get("text")

                return ParsedInboundMessage(
                    message_id=msg_id,
                    sender_phone=sender_phone,
                    timestamp=str(timestamp),
                    message_type=msg_type,
                    text_content=text_content,
                    audio_id=audio_id,
                    button_payload=button_payload,
                    button_title=button_title,
                    raw_payload=payload
                )

        return None
    except Exception as e:
        logger.error(f"Error parsing WhatsApp webhook payload: {str(e)}", exc_info=True)
        return None
