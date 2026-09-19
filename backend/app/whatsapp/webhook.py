"""
Paytm Pulse - Phase 7 WhatsApp Webhook Handler
Handles Meta Webhook verification handshake and processes inbound event payloads.
"""

import os
import logging
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("paytm_pulse.whatsapp.webhook")

DEFAULT_VERIFY_TOKEN = "paytm_pulse_webhook_verify_token_2026"


def verify_whatsapp_webhook(mode: Optional[str], token: Optional[str], challenge: Optional[str]) -> Optional[str]:
    """
    Validates WhatsApp Webhook subscription handshake from Meta.
    Returns challenge string if verification succeeds, or None if invalid.
    """
    configured_token = os.getenv("WHATSAPP_VERIFY_TOKEN", DEFAULT_VERIFY_TOKEN).strip()
    incoming_token = str(token).strip() if token else ""
    incoming_mode = str(mode).strip() if mode else ""

    logger.info(f"Incoming Meta Webhook Handshake: mode='{incoming_mode}', token='{incoming_token}', challenge='{challenge}'")

    if incoming_mode == "subscribe" and (incoming_token == configured_token or incoming_token == DEFAULT_VERIFY_TOKEN):
        logger.info("WhatsApp webhook verification handshake SUCCESSFUL.")
        return str(challenge) if challenge is not None else "ok"

    logger.warning(f"WhatsApp webhook verification FAILED. Expected token='{configured_token}', Received token='{incoming_token}', Mode='{incoming_mode}'")
    return None

