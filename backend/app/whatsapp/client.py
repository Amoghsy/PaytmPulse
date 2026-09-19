"""
Paytm Pulse - Phase 7 WhatsApp Cloud API Client
Handles outbound messages, media downloads, and interactive message templates with mock mode fallback.
"""

import os
import logging
import httpx
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

from app.whatsapp.schemas import WhatsAppQuickReplyButton

load_dotenv()
logger = logging.getLogger("paytm_pulse.whatsapp.client")


class WhatsAppClient:
    """
    Client for interacting with Meta's WhatsApp Cloud API (Graph API).
    Includes automatic Mock Mode support for zero-credential development and testing.
    """

    def __init__(
        self,
        access_token: Optional[str] = None,
        phone_number_id: Optional[str] = None,
        api_version: Optional[str] = None,
        mock_mode: Optional[bool] = None,
    ):
        self._access_token = access_token
        self._phone_number_id = phone_number_id
        self._api_version = api_version
        self._mock_mode = mock_mode
        self.sent_messages_log: List[Dict[str, Any]] = []

    def _get_config(self):
        """Dynamically reloads environment configuration on each send."""
        from pathlib import Path
        backend_env = Path(__file__).resolve().parent.parent.parent / ".env"
        root_env = Path(__file__).resolve().parent.parent.parent.parent / ".env"
        if backend_env.exists():
            load_dotenv(dotenv_path=backend_env, override=True)
        elif root_env.exists():
            load_dotenv(dotenv_path=root_env, override=True)
        else:
            load_dotenv(override=True)

        token = os.getenv("WHATSAPP_ACCESS_TOKEN", "").strip() or self._access_token or ""
        phone_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "").strip() or self._phone_number_id or ""
        version = os.getenv("WHATSAPP_API_VERSION", "").strip() or self._api_version or "v25.0"
        
        env_mock = os.getenv("WHATSAPP_MOCK_MODE", "false").strip().lower() in ("true", "1", "yes")
        has_creds = bool(token and phone_id and len(token) > 20)
        
        if self._mock_mode is not None:
            is_mock = self._mock_mode
        else:
            is_mock = env_mock or not has_creds
        
        base_url = f"https://graph.facebook.com/{version}/{phone_id}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        logger.info(f"WhatsApp Client Config: is_mock={is_mock}, phone_id={phone_id}, version={version}, token_len={len(token)}")
        return is_mock, base_url, headers

    def _normalize_phone(self, phone: str) -> str:
        """Strips formatting from phone number e.g. '+91 98765-43210' -> '919876543210'."""
        load_dotenv(override=True)
        override = os.getenv("WHATSAPP_TEST_PHONE", "").strip()
        if override:
            cleaned_override = "".join(ch for ch in override if ch.isdigit())
            if cleaned_override:
                logger.info(f"Using WHATSAPP_TEST_PHONE override: {cleaned_override}")
                return cleaned_override
        cleaned = "".join(ch for ch in str(phone) if ch.isdigit())
        return cleaned

    def send_text_message(self, recipient_phone: str, text: str) -> Dict[str, Any]:
        """
        Sends a plain text message to a WhatsApp user.
        """
        is_mock, base_url, headers = self._get_config()
        phone = self._normalize_phone(recipient_phone)
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": phone,
            "type": "text",
            "text": {"preview_url": False, "body": text}
        }

        if is_mock:
            logger.info(f"[WHATSAPP MOCK MODE] Outbound TEXT to {phone}: '{text}'")
            mock_resp = {
                "messaging_product": "whatsapp",
                "contacts": [{"input": phone, "wa_id": phone}],
                "messages": [{"id": f"wamid.mock_{os.urandom(8).hex()}"}],
                "mock": True
            }
            self.sent_messages_log.append({"to": phone, "type": "text", "body": text, "response": mock_resp})
            return mock_resp

        try:
            logger.info(f"[WHATSAPP LIVE API] Sending real WhatsApp text to {phone} via {base_url}/messages...")
            with httpx.Client(timeout=12.0) as client:
                resp = client.post(f"{base_url}/messages", headers=headers, json=payload)
                data = resp.json()
                if resp.status_code >= 400:
                    err_msg = data.get("error", {}).get("message", resp.text)
                    logger.warning(
                        f"Meta WhatsApp text send returned error ({resp.status_code}): {err_msg}. "
                        "Initiating pre-approved template fallback to ensure instant WhatsApp delivery outside 24h window..."
                    )
                    import datetime
                    curr_date = datetime.datetime.now().strftime("%b %d, %Y")
                    template_components = [
                        {
                            "type": "body",
                            "parameters": [
                                {"type": "text", "text": "Paytm Pulse Merchant"},
                                {"type": "text", "text": text[:30] if text else "STORE_ALERT"},
                                {"type": "text", "text": curr_date}
                            ]
                        }
                    ]
                    tpl_res = self.send_template_message(
                        recipient_phone=phone,
                        template_name="jaspers_market_order_confirmation_v1",
                        language_code="en_US",
                        components=template_components
                    )
                    if "error" not in tpl_res:
                        tpl_res["fallback_used"] = True
                        return tpl_res

                    hw_res = self.send_template_message(
                        recipient_phone=phone,
                        template_name="hello_world",
                        language_code="en_US",
                        components=[]
                    )
                    if "error" not in hw_res:
                        hw_res["fallback_used"] = True
                        return hw_res

                    return {"error": err_msg, "status_code": resp.status_code, "mock": False}
                logger.info(f"WhatsApp Message successfully delivered to Meta! Message ID: {data.get('messages', [{}])[0].get('id')}")
                return data
        except httpx.HTTPStatusError as e:
            logger.error(f"WhatsApp API HTTP error {e.response.status_code}: {e.response.text}")
            return {"error": str(e), "status_code": e.response.status_code, "mock": False}
        except Exception as e:
            logger.error(f"Failed to send WhatsApp text message: {str(e)}", exc_info=True)
            return {"error": str(e), "mock": False}

    def send_interactive_message(
        self,
        recipient_phone: str,
        body_text: str,
        buttons: List[WhatsAppQuickReplyButton],
        header_text: Optional[str] = None,
        footer_text: Optional[str] = "Paytm Pulse • Reply or Tap"
    ) -> Dict[str, Any]:
        """
        Sends an interactive quick-reply button message (up to 3 buttons).
        """
        is_mock, base_url, headers = self._get_config()
        phone = self._normalize_phone(recipient_phone)
        button_components = []
        for btn in buttons[:3]:  # WhatsApp supports max 3 quick reply buttons
            button_components.append({
                "type": "reply",
                "reply": {
                    "id": str(btn.id),
                    "title": str(btn.title)[:20]  # Max 20 chars
                }
            })

        interactive_obj: Dict[str, Any] = {
            "type": "button",
            "body": {"text": body_text},
            "action": {"buttons": button_components}
        }

        if header_text:
            interactive_obj["header"] = {"type": "text", "text": header_text}
        if footer_text:
            interactive_obj["footer"] = {"text": footer_text}

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": phone,
            "type": "interactive",
            "interactive": interactive_obj
        }

        if is_mock:
            logger.info(
                f"[WHATSAPP MOCK MODE] Outbound INTERACTIVE to {phone}: '{body_text}' | "
                f"Buttons: {[b.title for b in buttons]}"
            )
            mock_resp = {
                "messaging_product": "whatsapp",
                "contacts": [{"input": phone, "wa_id": phone}],
                "messages": [{"id": f"wamid.mock_interactive_{os.urandom(8).hex()}"}],
                "mock": True
            }
            self.sent_messages_log.append({
                "to": phone,
                "type": "interactive",
                "body": body_text,
                "buttons": [b.model_dump() for b in buttons],
                "response": mock_resp
            })
            return mock_resp

        try:
            logger.info(f"[WHATSAPP LIVE API] Sending real interactive WhatsApp template to {phone} via {base_url}/messages...")
            with httpx.Client(timeout=12.0) as client:
                resp = client.post(f"{base_url}/messages", headers=headers, json=payload)
                data = resp.json()
                if resp.status_code >= 400:
                    err_msg = data.get("error", {}).get("message", resp.text)
                    logger.warning(
                        f"Meta WhatsApp interactive send returned error ({resp.status_code}): {err_msg}. "
                        "Initiating pre-approved template fallback to ensure instant WhatsApp delivery outside 24h window..."
                    )
                    # Extract parameter values for template
                    p1 = "Paytm Pulse Merchant"
                    if header_text:
                        p1 = header_text.replace("🚨", "").replace("⚡", "").replace("💡", "").replace("📱", "").strip()[:30] or p1
                    p2 = "PULSE_ALERT_ACTION"
                    if buttons:
                        p2 = buttons[0].title[:30]
                    
                    import datetime
                    curr_date = datetime.datetime.now().strftime("%b %d, %Y")

                    template_components = [
                        {
                            "type": "body",
                            "parameters": [
                                {"type": "text", "text": p1},
                                {"type": "text", "text": p2},
                                {"type": "text", "text": curr_date}
                            ]
                        }
                    ]

                    # 1. Try jaspers_market_order_confirmation_v1
                    tpl_res = self.send_template_message(
                        recipient_phone=phone,
                        template_name="jaspers_market_order_confirmation_v1",
                        language_code="en_US",
                        components=template_components
                    )
                    if "error" not in tpl_res:
                        logger.info(f"Fallback to 'jaspers_market_order_confirmation_v1' succeeded! Message ID: {tpl_res.get('messages', [{}])[0].get('id')}")
                        tpl_res["fallback_used"] = True
                        return tpl_res

                    # 2. Try hello_world
                    logger.warning("jaspers_market_order_confirmation_v1 template failed. Trying 'hello_world' fallback...")
                    hw_res = self.send_template_message(
                        recipient_phone=phone,
                        template_name="hello_world",
                        language_code="en_US",
                        components=[]
                    )
                    if "error" not in hw_res:
                        logger.info(f"Fallback to 'hello_world' succeeded! Message ID: {hw_res.get('messages', [{}])[0].get('id')}")
                        hw_res["fallback_used"] = True
                        return hw_res

                    return {"error": err_msg, "status_code": resp.status_code, "mock": False}

                logger.info(f"Interactive WhatsApp Message successfully delivered to Meta! Message ID: {data.get('messages', [{}])[0].get('id')}")
                return data
        except httpx.HTTPStatusError as e:
            logger.error(f"WhatsApp API HTTP error {e.response.status_code}: {e.response.text}")
            return {"error": str(e), "status_code": e.response.status_code, "mock": False}
        except Exception as e:
            logger.error(f"Failed to send WhatsApp interactive message: {str(e)}", exc_info=True)
            return {"error": str(e), "mock": False}

    def send_template_message(
        self,
        recipient_phone: str,
        template_name: str = "jaspers_market_order_confirmation_v1",
        language_code: str = "en_US",
        components: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Sends an approved Meta WhatsApp template message (e.g. jaspers_market_order_confirmation_v1 or hello_world).
        """
        is_mock, base_url, headers = self._get_config()
        phone = self._normalize_phone(recipient_phone)

        if components is None:
            if template_name == "hello_world":
                components = []
            else:
                components = [
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": "Paytm Pulse Merchant"},
                            {"type": "text", "text": "DEMAND_SPIKE_ALERT"},
                            {"type": "text", "text": "Sep 19, 2026"}
                        ]
                    }
                ]

        template_payload: Dict[str, Any] = {
            "name": template_name,
            "language": {"code": language_code}
        }
        if components:
            template_payload["components"] = components

        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "template",
            "template": template_payload
        }

        if is_mock:
            logger.info(f"[WHATSAPP MOCK MODE] Outbound TEMPLATE to {phone}: '{template_name}'")
            return {
                "messaging_product": "whatsapp",
                "contacts": [{"input": phone, "wa_id": phone}],
                "messages": [{"id": f"wamid.mock_template_{os.urandom(8).hex()}"}],
                "mock": True
            }

        try:
            logger.info(f"[WHATSAPP LIVE API] POST {base_url}/messages | Payload: {payload}")
            with httpx.Client(timeout=12.0) as client:
                resp = client.post(f"{base_url}/messages", headers=headers, json=payload)
                data = resp.json()
                logger.info(f"[WHATSAPP LIVE API] Meta HTTP {resp.status_code} Response: {data}")
                if resp.status_code >= 400:
                    logger.error(f"Meta WhatsApp API Error ({resp.status_code}): {resp.text}")
                    return {"error": data.get("error", {}).get("message", resp.text), "status_code": resp.status_code, "mock": False}
                logger.info(f"Meta Template Message successfully delivered! Message ID: {data.get('messages', [{}])[0].get('id')}")
                return data
        except Exception as e:
            logger.error(f"Failed to send WhatsApp template message: {str(e)}", exc_info=True)
            return {"error": str(e), "mock": False}

    def send_audio_message(
        self,
        recipient_phone: str,
        audio_url: Optional[str] = None,
        audio_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Sends an audio/voice note message to a WhatsApp user.
        """
        is_mock, base_url, headers = self._get_config()
        phone = self._normalize_phone(recipient_phone)
        audio_obj: Dict[str, Any] = {}
        if audio_id:
            audio_obj["id"] = audio_id
        elif audio_url:
            audio_obj["link"] = audio_url
        else:
            audio_obj["link"] = "https://example.com/audio/sample_response.ogg"

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": phone,
            "type": "audio",
            "audio": audio_obj
        }

        if is_mock:
            logger.info(f"[WHATSAPP MOCK MODE] Outbound AUDIO to {phone}: URL={audio_url or audio_id}")
            mock_resp = {
                "messaging_product": "whatsapp",
                "contacts": [{"input": phone, "wa_id": phone}],
                "messages": [{"id": f"wamid.mock_audio_{os.urandom(8).hex()}"}],
                "mock": True
            }
            self.sent_messages_log.append({"to": phone, "type": "audio", "audio": audio_obj, "response": mock_resp})
            return mock_resp

        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.post(f"{base_url}/messages", headers=headers, json=payload)
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.error(f"Failed to send WhatsApp audio message: {str(e)}", exc_info=True)
            return {"error": str(e), "mock": False}

    def download_media(self, media_id: str) -> Optional[bytes]:
        """
        Fetches binary media data from WhatsApp Graph API given media_id.
        """
        is_mock, base_url, headers = self._get_config()
        if is_mock or not media_id or media_id.startswith("test_") or media_id.startswith("media_"):
            logger.info(f"[WHATSAPP MOCK] Downloading media {media_id} (returning mock audio bytes)")
            return b"MOCK_AUDIO_DATA_BYTES_FOR_SARVAM"

        try:
            version = os.getenv("WHATSAPP_API_VERSION", "v25.0").strip() or "v25.0"
            token = os.getenv("WHATSAPP_ACCESS_TOKEN", "").strip() or self._access_token or ""
            with httpx.Client(timeout=15.0) as client:
                # Step 1: Get media URL
                meta_url = f"https://graph.facebook.com/{version}/{media_id}"
                meta_resp = client.get(meta_url, headers=headers)
                meta_resp.raise_for_status()
                media_url = meta_resp.json().get("url")

                if not media_url:
                    return None

                # Step 2: Download raw binary
                bin_resp = client.get(media_url, headers={"Authorization": f"Bearer {token}"})
                bin_resp.raise_for_status()
                return bin_resp.content
        except Exception as e:
            logger.error(f"Failed to download WhatsApp media {media_id}: {str(e)}", exc_info=True)
            return None


# Global singleton instance
whatsapp_client = WhatsAppClient()
