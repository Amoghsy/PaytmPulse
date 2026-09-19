"""
Paytm Pulse - Phase 7 Communication API Router
FastAPI endpoints for Meta WhatsApp Webhooks, test simulators, proactive alert triggers, and communication logs.
"""

import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, BackgroundTasks, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.merchant import Merchant
from app.models.recommendation import Recommendation
from app.models.merchant_message import MerchantMessage
from app.whatsapp.webhook import verify_whatsapp_webhook
from app.whatsapp.message_parser import parse_whatsapp_webhook_payload
from app.whatsapp.schemas import ParsedInboundMessage
from app.communication.message_handler import MessageHandler
from app.communication.notification_service import NotificationService
from app.communication.conversation_manager import ConversationManager
from app.communication.schemas import (
    TestMessageRequest,
    TestMessageResponse,
    ProactiveAlertResponse,
    MerchantMessageLogItem
)

logger = logging.getLogger("paytm_pulse.communication.router")

router = APIRouter(tags=["Communication - WhatsApp & Voice"])


# ---------------------------------------------------------
# 1. WhatsApp Cloud API Webhooks
# ---------------------------------------------------------

@router.get("/webhooks/whatsapp", status_code=status.HTTP_200_OK)
@router.get("/webhook/whatsapp", status_code=status.HTTP_200_OK)
@router.get("/webhooks", status_code=status.HTTP_200_OK)
@router.get("/webhook", status_code=status.HTTP_200_OK)
def whatsapp_webhook_verification(
    request: Request,
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token"),
):
    """
    Verification handshake required by Meta WhatsApp Cloud API.
    """
    challenge = verify_whatsapp_webhook(hub_mode, hub_verify_token, hub_challenge)
    if challenge is not None:
        return Response(content=str(challenge), media_type="text/plain", status_code=status.HTTP_200_OK)
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Verification token mismatch")


@router.post("/webhooks/whatsapp", status_code=status.HTTP_200_OK)
@router.post("/webhook/whatsapp", status_code=status.HTTP_200_OK)
@router.post("/webhooks", status_code=status.HTTP_200_OK)
@router.post("/webhook", status_code=status.HTTP_200_OK)
async def whatsapp_webhook_inbound(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Receives incoming WhatsApp messages, media, and button clicks from Meta.
    Returns HTTP 200 immediately to adhere to Meta's SLA (<3s) while executing handlers.
    """
    try:
        payload = await request.json()
    except Exception:
        return {"status": "INVALID_JSON"}

    parsed = parse_whatsapp_webhook_payload(payload)
    if not parsed:
        # Acknowledging delivery receipts, status updates, or non-message payloads
        return {"status": "IGNORED_STATUS_UPDATE"}

    # Process message synchronously or via background task
    handler = MessageHandler(db)
    result = handler.process_inbound_message(parsed)
    return {"status": "PROCESSED", "result": result}


# ---------------------------------------------------------
# 2. Local Testing & Developer Simulators
# ---------------------------------------------------------

@router.post("/communication/test-message", response_model=TestMessageResponse, status_code=status.HTTP_200_OK)
def simulate_merchant_message(
    payload: TestMessageRequest,
    db: Session = Depends(get_db)
):
    """
    Simulates a merchant sending a WhatsApp text or voice note into the system without needing live credentials.
    """
    # 1. Identify Merchant
    merchant = None
    if payload.merchant_id:
        merchant = db.query(Merchant).filter(Merchant.id == payload.merchant_id).first()
    elif payload.phone:
        merchant = db.query(Merchant).filter(Merchant.phone == payload.phone).first()

    if not merchant:
        # Fallback to first available merchant in seed data
        merchant = db.query(Merchant).first()
        if not merchant:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No merchant found in database.")

    # Override language if requested
    if payload.language:
        merchant.language = payload.language

    # 2. Create simulated Inbound Message
    msg_type = "voice" if payload.is_voice else "text"
    parsed = ParsedInboundMessage(
        message_id=f"test_msg_{payload.merchant_id or 'mock'}",
        sender_phone=merchant.phone,
        timestamp="1726617600",
        message_type=msg_type,
        text_content=payload.message if not payload.is_voice else None,
        audio_id="test_audio_media_123" if payload.is_voice else None
    )

    handler = MessageHandler(db)
    res = handler.process_inbound_message(parsed)

    # Prepare response
    resp_text = res.get("response_text") or (
        res.get("result", {}).get("response_text") if isinstance(res.get("result"), dict) else "Processed successfully"
    )
    status_str = str(res.get("status", ""))
    intent_cat = "ACTION_EXECUTION" if "APPROVED" in status_str else ("REJECTION" if "REJECTED" in status_str else "QUERY")

    return TestMessageResponse(
        merchant_id=merchant.id,
        merchant_name=merchant.name,
        shop_name=merchant.shop_name,
        input_message=payload.message,
        is_voice=payload.is_voice,
        response_text=str(resp_text),
        voice_audio_base64=None,
        intent_category=intent_cat,
        suggested_action=res.get("suggested_action") or res.get("action_title"),
        whatsapp_sent=True,
        cooldown_active=False
    )


@router.post("/communication/test-recommendation/{decision_id}", response_model=ProactiveAlertResponse, status_code=status.HTTP_200_OK)
def trigger_proactive_recommendation_alert(
    decision_id: str,
    recipient_phone: Optional[str] = Query(None, description="Override recipient phone number (e.g. your verified WhatsApp number '919876543210')"),
    bypass_cooldown: bool = False,
    db: Session = Depends(get_db)
):
    """
    Sends a proactive Next Best Action recommendation alert to a merchant via WhatsApp Cloud API.
    """
    try:
        rec = db.query(Recommendation).filter(Recommendation.id == decision_id).first()
        if not rec:
            # Fallback to any latest recommendation if testing
            rec = db.query(Recommendation).order_by(Recommendation.created_at.desc()).first()
            if not rec:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Recommendation '{decision_id}' not found.")

        merchant = db.query(Merchant).filter(Merchant.id == rec.merchant_id).first()
        if not merchant:
            merchant = db.query(Merchant).first()
            if not merchant:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associated merchant not found.")

        if recipient_phone and isinstance(recipient_phone, str):
            merchant.phone = recipient_phone

        rec_type_str = rec.type.value if hasattr(rec.type, "value") else str(rec.type)

        # Direct live Meta WhatsApp Cloud API execution matching verified working cURL
        import os, httpx
        from pathlib import Path
        from dotenv import load_dotenv

        backend_env = Path(__file__).resolve().parent.parent.parent / ".env"
        root_env = Path(__file__).resolve().parent.parent.parent.parent / ".env"
        if backend_env.exists():
            load_dotenv(dotenv_path=backend_env, override=True)
        elif root_env.exists():
            load_dotenv(dotenv_path=root_env, override=True)
        else:
            load_dotenv(override=True)

        token = os.getenv("WHATSAPP_ACCESS_TOKEN", "").strip()
        phone_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "1276227445580221").strip()
        test_override = (os.getenv("WHATSAPP_TEST_PHONE") or "").strip()
        to_phone = "".join(ch for ch in test_override if ch.isdigit()) if test_override else "".join(ch for ch in (merchant.phone) if ch.isdigit())
        if recipient_phone and isinstance(recipient_phone, str):
            to_phone = "".join(ch for ch in recipient_phone if ch.isdigit()) or to_phone

        url = f"https://graph.facebook.com/v25.0/{phone_id}/messages"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        # 1. Format exact localized alert recommendation (e.g. Kannada, Hindi, etc.)
        from app.communication.multilingual import format_multilingual_recommendation
        header_text, body_text, buttons, footer_text = format_multilingual_recommendation(
            merchant=merchant,
            recommendation=rec
        )

        button_components = []
        for btn in buttons[:3]:
            button_components.append({
                "type": "reply",
                "reply": {
                    "id": str(btn.id),
                    "title": str(btn.title)[:20]
                }
            })

        # Priority 1: Interactive Quick-Reply WhatsApp Message (Header + Body in Kannada + Quick Buttons)
        interactive_payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_phone,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "header": {"type": "text", "text": header_text[:60]},
                "body": {"text": body_text},
                "footer": {"text": footer_text[:60]},
                "action": {"buttons": button_components}
            }
        }

        # Priority 2: Full Localized Rich Text Alert
        full_text = f"{header_text}\n\n{body_text}\n\n{footer_text}"
        text_payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_phone,
            "type": "text",
            "text": {"preview_url": False, "body": full_text}
        }

        # Priority 3: Meta Template Fallback if outside 24h customer service window
        template_payload = {
            "messaging_product": "whatsapp",
            "to": to_phone,
            "type": "template",
            "template": {
                "name": "jaspers_market_order_confirmation_v1",
                "language": {"code": "en_US"},
                "components": [
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": (merchant.name or "Ravi Kumar")[:30]},
                            {"type": "text", "text": (rec.title or "Restock Atta 5kg")[:30]},
                            {"type": "text", "text": "Sep 19, 2026"}
                        ]
                    }
                ]
            }
        }

        logger.info(f"Sending real localized WhatsApp alert to {to_phone} via Meta Graph API...")
        with httpx.Client(timeout=15.0) as client:
            # 1. Try sending Interactive message with buttons in preferred language
            resp = client.post(url, headers=headers, json=interactive_payload)
            data = resp.json()

            # 2. If interactive fails, try rich text in preferred language
            if resp.status_code >= 400:
                logger.warning(f"Interactive message returned {resp.status_code}: {data.get('error', {}).get('message')}. Trying full text payload...")
                resp = client.post(url, headers=headers, json=text_payload)
                data = resp.json()

            # 3. If outside 24h window, send template and then text
            if resp.status_code >= 400:
                logger.warning(f"Text message returned {resp.status_code}: {data.get('error', {}).get('message')}. Sending template fallback...")
                resp = client.post(url, headers=headers, json=template_payload)
                data = resp.json()

                if resp.status_code < 400:
                    # Also deliver the full Kannada text
                    client.post(url, headers=headers, json=text_payload)

                if resp.status_code >= 400:
                    logger.warning("jaspers_market template failed. Trying hello_world fallback...")
                    hw_payload = {
                        "messaging_product": "whatsapp",
                        "to": to_phone,
                        "type": "template",
                        "template": {"name": "hello_world", "language": {"code": "en_US"}}
                    }
                    resp = client.post(url, headers=headers, json=hw_payload)
                    data = resp.json()
                    if resp.status_code < 400:
                        client.post(url, headers=headers, json=text_payload)

        if resp.status_code >= 400:
            err_obj = data.get("error", {})
            err_msg = err_obj.get("message", resp.text)
            err_code = err_obj.get("code", resp.status_code)
            err_sub = err_obj.get("error_subcode", "")
            err_type = err_obj.get("type", "")
            full_err = f"{err_msg} [Code: {err_code}, Subcode: {err_sub}, Type: {err_type}]"
            return ProactiveAlertResponse(
                decision_id=decision_id,
                merchant_id=merchant.id,
                alert_type=rec_type_str,
                message_text=full_err,
                whatsapp_message_id=None,
                cooldown_prevented=False,
                status="FAILED"
            )

        wa_msgs = data.get("messages", [])
        wa_msg_id = wa_msgs[0].get("id") if wa_msgs and isinstance(wa_msgs, list) and len(wa_msgs) > 0 else "SENT"

        return ProactiveAlertResponse(
            decision_id=decision_id,
            merchant_id=merchant.id,
            alert_type=rec_type_str,
            message_text=f"Real WhatsApp alert delivered to {to_phone}",
            whatsapp_message_id=wa_msg_id,
            cooldown_prevented=False,
            status="SENT"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in trigger_proactive_recommendation_alert: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to send alert: {str(e)}")


@router.post("/communication/test-event-alert/{merchant_id}", status_code=status.HTTP_200_OK)
def trigger_proactive_event_alert(
    merchant_id: str,
    recipient_phone: Optional[str] = Query(None, description="Override recipient phone number (e.g. '919876543210')"),
    event_type: str = Query("DEMAND_SPIKE", description="Event type: DEMAND_SPIKE, STOCKOUT_RISK, SALES_DECLINE"),
    severity: str = Query("HIGH", description="Severity level: LOW, MEDIUM, HIGH, CRITICAL"),
    details_message: Optional[str] = Query(None, description="Custom details message in English (will be formatted for the merchant)"),
    bypass_cooldown: bool = Query(True, description="Bypass anti-spam cooldown for testing"),
    db: Session = Depends(get_db)
):
    """
    Sends a real-time proactive business anomaly alert to a merchant via WhatsApp in their exact preferred language.
    """
    merchant = db.query(Merchant).filter(Merchant.id == merchant_id).first()
    if not merchant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Merchant not found.")

    if recipient_phone:
        merchant.phone = recipient_phone

    if not details_message:
        if "DEMAND" in event_type.upper():
            details_message = "Sudden 2.5x increase in sales volume detected in the last 15 minutes!"
        elif "STOCK" in event_type.upper():
            details_message = "Inventory is running dangerously low. Stock is below the safety threshold."
        elif "DECLINE" in event_type.upper():
            details_message = "Sales velocity has dropped 35% below expected levels for today."
        else:
            details_message = "Important business telemetry update."

    notifications = NotificationService(db)
    result = notifications.send_business_event_alert(
        merchant=merchant,
        event_type=event_type,
        severity=severity,
        details_message=details_message,
        bypass_cooldown=bypass_cooldown
    )

    return {
        "status": "SENT" if result.get("sent") else "FAILED",
        "merchant_id": merchant.id,
        "merchant_name": merchant.name,
        "shop_name": merchant.shop_name,
        "recipient_phone": merchant.phone,
        "language": result.get("language"),
        "event_type": event_type,
        "header_text": result.get("header_text"),
        "body_text": result.get("body_text"),
        "whatsapp_response": result.get("whatsapp_response")
    }


@router.post("/communication/broadcast-multilingual", status_code=status.HTTP_200_OK)
def broadcast_multilingual_alert(
    event_type: str = Query("DEMAND_SPIKE", description="Event type to broadcast"),
    severity: str = Query("HIGH", description="Severity"),
    custom_message: Optional[str] = Query(None, description="Alert message"),
    db: Session = Depends(get_db)
):
    """
    Broadcasts proactive business alerts to all registered merchants,
    translating and tailoring each message into the merchant's exact preferred language and store category.
    """
    merchants = db.query(Merchant).all()
    if not merchants:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No merchants found.")

    notifications = NotificationService(db)
    results = []

    for m in merchants:
        res = notifications.send_business_event_alert(
            merchant=m,
            event_type=event_type,
            severity=severity,
            details_message=custom_message or "Special market alert for your store category.",
            bypass_cooldown=True
        )
        results.append({
            "merchant_id": m.id,
            "merchant_name": m.name,
            "shop_name": m.shop_name,
            "category": m.category.value if hasattr(m.category, "value") else str(m.category),
            "language": res.get("language"),
            "sent": res.get("sent"),
            "header_text": res.get("header_text"),
            "body_text": res.get("body_text")
        })

    return {
        "total_merchants": len(merchants),
        "successful_alerts": len([r for r in results if r["sent"]]),
        "results": results
    }


@router.get("/communication/history/{merchant_id}", response_model=List[MerchantMessageLogItem], status_code=status.HTTP_200_OK)
def get_merchant_message_history(
    merchant_id: str,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """
    Retrieves recent communication logs (inbound/outbound) for a merchant.
    """
    logs = (
        db.query(MerchantMessage)
        .filter(MerchantMessage.merchant_id == merchant_id)
        .order_by(MerchantMessage.created_at.desc())
        .limit(limit)
        .all()
    )
    return logs


@router.post("/communication/send-template-alert", status_code=status.HTTP_200_OK)
def send_template_alert_direct(
    recipient_phone: Optional[str] = Query(description="Recipient phone number with country code"),
    template_name: str = Query("jaspers_market_order_confirmation_v1", description="Template name (e.g. jaspers_market_order_confirmation_v1 or hello_world)"),
    merchant_name: str = Query("Ravi Kumar", description="Merchant name for template param 1"),
    alert_code: str = Query("DEMAND_SPIKE_99", description="Alert/order code for template param 2"),
    date_str: str = Query("Sep 19, 2026", description="Date string for template param 3"),
    db: Session = Depends(get_db)
):
    """
    Sends a direct Meta WhatsApp template message (jaspers_market_order_confirmation_v1 or hello_world)
    guaranteeing delivery even outside the 24-hour customer service window.
    """
    from app.whatsapp.client import whatsapp_client

    components = []
    if template_name != "hello_world":
        components = [
            {
                "type": "body",
                "parameters": [
                    {"type": "text", "text": merchant_name},
                    {"type": "text", "text": alert_code},
                    {"type": "text", "text": date_str}
                ]
            }
        ]

    res = whatsapp_client.send_template_message(
        recipient_phone=recipient_phone,
        template_name=template_name,
        language_code="en_US",
        components=components
    )

    return {
        "status": "SENT" if "error" not in res else "FAILED",
        "recipient_phone": recipient_phone,
        "template_name": template_name,
        "whatsapp_response": res
    }


@router.post("/communication/clear-context/{merchant_id}", status_code=status.HTTP_200_OK)
def clear_conversation_context(merchant_id: str):
    """
    Clears the Redis conversation session context for a merchant.
    """
    ConversationManager.clear_context(merchant_id)
    return {"status": "CLEARED", "merchant_id": merchant_id}
