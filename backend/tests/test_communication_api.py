import pytest
from app.models.merchant import Merchant, MerchantCategory
from app.models.product import Product
from app.models.recommendation import Recommendation, RecommendationType, RecommendationStatus
from app.models.action import Action, ActionType, ActionStatus


@pytest.fixture
def api_merchant(db_session):
    m = Merchant(
        name="Anand Sharma",
        shop_name="Anand Provisions",
        category=MerchantCategory.KIRANA,
        location="Jayanagar, Bengaluru",
        language="Kannada",
        phone="919811122233"
    )
    db_session.add(m)
    db_session.commit()
    db_session.refresh(m)

    p = Product(
        merchant_id=m.id,
        name="Basmati Rice 5kg",
        category="Grains",
        price=350.0,
        cost_price=270.0
    )
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)

    rec = Recommendation(
        merchant_id=m.id,
        type=RecommendationType.STOCK_REORDER,
        title="Restock Basmati Rice 5kg",
        reason="High sales velocity. Inventory low.",
        confidence=0.9,
        urgency="HIGH",
        expected_impact="₹2,500 protected revenue",
        status=RecommendationStatus.PENDING
    )
    db_session.add(rec)
    db_session.commit()
    db_session.refresh(rec)

    act = Action(
        recommendation_id=rec.id,
        merchant_id=m.id,
        action_type=ActionType.REORDER,
        status=ActionStatus.PENDING,
        parameters={"quantity": 20}
    )
    db_session.add(act)
    db_session.commit()

    return m, rec


def test_whatsapp_webhook_get_verification(client):
    response = client.get("/webhooks/whatsapp?hub.mode=subscribe&hub.verify_token=paytm_pulse_webhook_verify_token_2026&hub.challenge=test_challenge_123")
    assert response.status_code == 200
    assert response.text == "test_challenge_123"


def test_whatsapp_webhook_get_invalid_token(client):
    response = client.get("/webhooks/whatsapp?hub.mode=subscribe&hub.verify_token=wrong_token&hub.challenge=test_challenge_123")
    assert response.status_code == 403


def test_whatsapp_webhook_post_inbound(client, api_merchant):
    merchant, _ = api_merchant
    payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "id": "wamid.INBOUND_001",
                                    "from": merchant.phone,
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
    response = client.post("/webhooks/whatsapp", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "PROCESSED"


def test_simulate_test_message_endpoint(client, api_merchant):
    merchant, _ = api_merchant
    payload = {
        "merchant_id": merchant.id,
        "message": "What is my top selling product?",
        "is_voice": False
    }
    response = client.post("/communication/test-message", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["merchant_id"] == merchant.id
    assert "response_text" in data
    assert len(data["response_text"]) > 0


def test_trigger_proactive_recommendation_alert_endpoint(client, api_merchant):
    _, rec = api_merchant
    response = client.post(f"/communication/test-recommendation/{rec.id}?bypass_cooldown=true")
    assert response.status_code == 200
    data = response.json()
    assert data["decision_id"] == rec.id
    assert data["status"] in ("SENT", "COOLDOWN_PREVENTED")


def test_communication_history_endpoint(client, api_merchant):
    merchant, _ = api_merchant
    response = client.get(f"/communication/history/{merchant.id}")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_clear_conversation_context_endpoint(client, api_merchant):
    merchant, _ = api_merchant
    response = client.post(f"/communication/clear-context/{merchant.id}")
    assert response.status_code == 200
    assert response.json().get("status") == "CLEARED"
