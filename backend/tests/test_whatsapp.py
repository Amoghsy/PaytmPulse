import pytest
from app.whatsapp.webhook import verify_whatsapp_webhook
from app.whatsapp.message_parser import parse_whatsapp_webhook_payload
from app.whatsapp.client import WhatsAppClient
from app.whatsapp.schemas import WhatsAppQuickReplyButton


def test_whatsapp_webhook_verification_success():
    mode = "subscribe"
    token = "paytm_pulse_webhook_verify_token_2026"
    challenge = "challenge_code_12345"
    res = verify_whatsapp_webhook(mode, token, challenge)
    assert res == challenge


def test_whatsapp_webhook_verification_failure():
    res = verify_whatsapp_webhook("subscribe", "wrong_token", "challenge_123")
    assert res is None


def test_parse_whatsapp_text_message():
    raw_payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "id": "wamid.HBgLMTIzNDU2",
                                    "from": "919876543210",
                                    "timestamp": "1726617600",
                                    "type": "text",
                                    "text": {"body": "How are my sales today?"}
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }
    parsed = parse_whatsapp_webhook_payload(raw_payload)
    assert parsed is not None
    assert parsed.message_id == "wamid.HBgLMTIzNDU2"
    assert parsed.sender_phone == "919876543210"
    assert parsed.message_type == "text"
    assert parsed.text_content == "How are my sales today?"


def test_parse_whatsapp_button_reply():
    raw_payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "id": "wamid.HBgLMTIzNDU3",
                                    "from": "919876543210",
                                    "timestamp": "1726617601",
                                    "type": "interactive",
                                    "interactive": {
                                        "type": "button_reply",
                                        "button_reply": {
                                            "id": "APPROVE_rec_test_123",
                                            "title": "✅ Approve"
                                        }
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }
    parsed = parse_whatsapp_webhook_payload(raw_payload)
    assert parsed is not None
    assert parsed.message_type == "interactive"
    assert parsed.button_payload == "APPROVE_rec_test_123"
    assert parsed.button_title == "✅ Approve"


def test_whatsapp_mock_client_send_text():
    client = WhatsAppClient(mock_mode=True)
    res = client.send_text_message("919876543210", "Hello from Paytm Pulse!")
    assert res.get("mock") is True
    assert "messages" in res


def test_whatsapp_mock_client_send_interactive():
    client = WhatsAppClient(mock_mode=True)
    buttons = [
        WhatsAppQuickReplyButton(id="APPROVE_1", title="Approve"),
        WhatsAppQuickReplyButton(id="REJECT_1", title="Reject")
    ]
    res = client.send_interactive_message(
        recipient_phone="919876543210",
        body_text="Urgent Stock Alert",
        buttons=buttons
    )
    assert res.get("mock") is True
    assert len(client.sent_messages_log) > 0
