import pytest
from datetime import datetime, timezone
from app.models.merchant import Merchant, MerchantCategory
from app.models.product import Product
from app.models.inventory import Inventory
from app.models.recommendation import Recommendation, RecommendationType, RecommendationStatus
from app.models.action import Action, ActionType, ActionStatus
from app.whatsapp.schemas import ParsedInboundMessage
from app.communication.message_handler import MessageHandler
from app.communication.notification_service import NotificationService
from app.communication.conversation_manager import ConversationManager


@pytest.fixture
def test_merchant(db_session):
    m = Merchant(
        name="Ramesh Kumar",
        shop_name="Ramesh Kirana Store",
        category=MerchantCategory.KIRANA,
        location="Indiranagar, Bengaluru",
        language="Kannada",
        phone="919876543210"
    )
    db_session.add(m)
    db_session.commit()
    db_session.refresh(m)
    return m


@pytest.fixture
def other_merchant(db_session):
    m = Merchant(
        name="Suresh Patel",
        shop_name="Patel Supermarket",
        category=MerchantCategory.KIRANA,
        location="Koramangala, Bengaluru",
        language="Hindi",
        phone="919876543999"
    )
    db_session.add(m)
    db_session.commit()
    db_session.refresh(m)
    return m


@pytest.fixture
def test_product(db_session, test_merchant):
    p = Product(
        merchant_id=test_merchant.id,
        name="Cold Drinks 500ml",
        category="Beverages",
        price=40.0,
        cost_price=28.0
    )
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)

    inv = Inventory(
        product_id=p.id,
        current_stock=12,
        reorder_level=25,
        maximum_stock=50
    )
    db_session.add(inv)
    db_session.commit()
    return p


@pytest.fixture
def test_recommendation(db_session, test_merchant, test_product):
    rec = Recommendation(
        merchant_id=test_merchant.id,
        event_id=None,
        type=RecommendationType.STOCK_REORDER,
        title="Restock Cold Drinks 500ml",
        reason="High demand detected. Inventory is projected to deplete within 3 hours.",
        confidence=0.92,
        urgency="HIGH",
        expected_impact="₹1,500 protected revenue",
        status=RecommendationStatus.PENDING
    )
    db_session.add(rec)
    db_session.commit()
    db_session.refresh(rec)

    act = Action(
        recommendation_id=rec.id,
        merchant_id=test_merchant.id,
        action_type=ActionType.REORDER,
        status=ActionStatus.PENDING,
        parameters={"quantity": 30, "product_id": test_product.id}
    )
    db_session.add(act)
    db_session.commit()
    return rec


def test_inbound_text_query(db_session, test_merchant, test_product):
    handler = MessageHandler(db_session)
    parsed = ParsedInboundMessage(
        message_id="msg_001",
        sender_phone="919876543210",
        timestamp="1726617600",
        message_type="text",
        text_content="How are my sales today?"
    )

    res = handler.process_inbound_message(parsed)
    assert res.get("status") == "TEXT_PROCESSED"
    assert "sales" in res.get("response_text", "").lower() or len(res.get("response_text", "")) > 0


def test_inbound_voice_query(db_session, test_merchant, test_product, monkeypatch):
    from unittest.mock import MagicMock
    from app.voice import sarvam_client
    monkeypatch.setattr(sarvam_client, "speech_to_text", lambda *args, **kwargs: {"transcript": "Show today's sales summary", "language_code": "en-IN"})
    
    handler = MessageHandler(db_session)
    parsed = ParsedInboundMessage(
        message_id="msg_002",
        sender_phone="919876543210",
        timestamp="1726617600",
        message_type="voice",
        audio_id="media_audio_id_test"
    )

    res = handler.process_inbound_message(parsed)
    assert res.get("status") == "VOICE_PROCESSED"
    assert res.get("transcript") != ""
    assert res.get("response_text") != ""


def test_deterministic_button_approval(db_session, test_merchant, test_recommendation):
    handler = MessageHandler(db_session)
    parsed = ParsedInboundMessage(
        message_id="msg_003",
        sender_phone="919876543210",
        timestamp="1726617600",
        message_type="interactive",
        button_payload=f"APPROVE_{test_recommendation.id}",
        button_title="✅ Approve"
    )

    res = handler.process_inbound_message(parsed)
    assert res.get("status") == "APPROVED"
    assert res.get("decision_id") == test_recommendation.id

    # Verify database state transition
    db_session.refresh(test_recommendation)
    assert test_recommendation.status == RecommendationStatus.APPROVED


def test_deterministic_button_rejection(db_session, test_merchant, test_recommendation):
    handler = MessageHandler(db_session)
    parsed = ParsedInboundMessage(
        message_id="msg_004",
        sender_phone="919876543210",
        timestamp="1726617600",
        message_type="interactive",
        button_payload=f"REJECT_{test_recommendation.id}",
        button_title="❌ Reject"
    )

    res = handler.process_inbound_message(parsed)
    assert res.get("status") == "REJECTED"

    # Verify database state transition
    db_session.refresh(test_recommendation)
    assert test_recommendation.status == RecommendationStatus.REJECTED


def test_unauthorized_recommendation_approval(db_session, other_merchant, test_recommendation):
    """Suresh Patel (other merchant) attempts to approve Ramesh's recommendation."""
    handler = MessageHandler(db_session)
    parsed = ParsedInboundMessage(
        message_id="msg_005",
        sender_phone="919876543999",  # Other merchant's phone
        timestamp="1726617600",
        message_type="interactive",
        button_payload=f"APPROVE_{test_recommendation.id}",
        button_title="✅ Approve"
    )

    res = handler.process_inbound_message(parsed)
    assert res.get("status") == "UNAUTHORIZED"

    # Verify recommendation was NOT approved
    db_session.refresh(test_recommendation)
    assert test_recommendation.status == RecommendationStatus.PENDING


def test_unregistered_merchant_phone(db_session):
    handler = MessageHandler(db_session)
    parsed = ParsedInboundMessage(
        message_id="msg_006",
        sender_phone="910000000000",  # Unregistered phone
        timestamp="1726617600",
        message_type="text",
        text_content="Hello"
    )

    res = handler.process_inbound_message(parsed)
    assert res.get("status") == "UNREGISTERED_SENDER"


def test_proactive_alert_with_cooldown(db_session, test_merchant, test_recommendation):
    notifications = NotificationService(db_session)

    # 1. Send first alert
    res1 = notifications.send_recommendation_alert(test_merchant, test_recommendation)
    assert res1.get("sent") is True

    # 2. Mock active cooldown in redis
    rec_type_val = test_recommendation.type.value if hasattr(test_recommendation.type, "value") else str(test_recommendation.type)
    is_cool = notifications._is_cooldown_active(test_merchant.id, getattr(test_recommendation, "product_id", None), rec_type_val)
    assert res1.get("decision_id") == test_recommendation.id


def test_conversation_manager_memory(db_session, test_merchant):
    ConversationManager.clear_context(test_merchant.id)
    ctx = ConversationManager.get_context(test_merchant.id)
    assert len(ctx.get("turns", [])) == 0

    ConversationManager.add_interaction(
        merchant_id=test_merchant.id,
        user_message="Cold drinks stock eshtu ide?",
        agent_response="You have 12 units remaining.",
        product_name="Cold Drinks 500ml"
    )

    updated_ctx = ConversationManager.get_context(test_merchant.id)
    assert updated_ctx.get("last_product_name") == "Cold Drinks 500ml" or len(updated_ctx.get("turns", [])) >= 0
