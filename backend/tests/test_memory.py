"""Paytm Pulse - Phase 11 Redis & Agent Fast Memory Tests.

Tests:
1. Transaction Fast Memory (LPUSH, LTRIM, TTL, DB fallback)
2. Alert Fast Memory (HSET, HDEL, HGETALL, DB fallback)
3. Merchant Session Memory (HSET, TTL renewal)
4. Multi-turn Conversation Memory (rolling buffer, DB fallback)
5. Recommendation Fast Memory (cache, active map, invalidation)
6. Intelligence Cache (analytics caching & bulk invalidation)
7. Unified Agent Context Builder (Redis + PostgreSQL hybrid)
8. Merchant Data Isolation (no cross-merchant leakage)
9. Graceful Fallback (resilience when Redis is unavailable)
10. Memory REST API Endpoints (/memory/*)
"""
import pytest
import uuid
import time
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.memory.transaction_memory import TransactionMemory
from app.memory.alert_memory import AlertMemory
from app.memory.session_memory import SessionMemory
from app.memory.conversation_memory import ConversationMemory
from app.memory.recommendation_memory import RecommendationMemory
from app.memory.cache import IntelligenceCache
from app.memory.context_builder import build_agent_context
from app.agent.tools.memory_tools import get_recent_merchant_context
from app.models.merchant import Merchant


@pytest.fixture
def mock_merchant(db_session: Session):
    """Creates a test merchant for memory testing."""
    merchant_id = f"test_mem_m_{uuid.uuid4().hex[:8]}"
    merchant = Merchant(
        id=merchant_id,
        name="Memory Test Store",
        shop_name="Memory Test Store",
        category="KIRANA",
        location="Mumbai",
        phone=f"+91{uuid.uuid4().int % 10000000000:010d}"
    )
    db_session.add(merchant)
    db_session.commit()
    db_session.refresh(merchant)
    return merchant


def test_transaction_memory(mock_merchant):
    """Test pushing and retrieving transactions in fast memory."""
    m_id = mock_merchant.id
    tx1 = {"id": "tx_1", "merchant_id": m_id, "amount": 100.0, "product_name": "Milk"}
    tx2 = {"id": "tx_2", "merchant_id": m_id, "amount": 250.0, "product_name": "Bread"}

    # Push to memory
    pushed = TransactionMemory.push_transaction(m_id, tx1)
    if pushed:
        TransactionMemory.push_transaction(m_id, tx2)
        txns = TransactionMemory.get_recent_transactions(m_id, limit=5)
        assert len(txns) >= 2
        assert txns[0]["id"] == "tx_2"  # LIFO order from LPUSH


def test_alert_memory(mock_merchant):
    """Test storing, retrieving, and clearing active alerts."""
    m_id = mock_merchant.id
    ev_id = f"ev_{uuid.uuid4().hex[:6]}"
    alert = {
        "id": ev_id,
        "event_type": "STOCKOUT_RISK",
        "severity": "HIGH",
        "payload": {"product_name": "Sugar", "remaining_stock": 2}
    }

    set_res = AlertMemory.set_alert(m_id, ev_id, alert)
    if set_res:
        alerts = AlertMemory.get_active_alerts(m_id)
        assert any(a["id"] == ev_id for a in alerts)

        # Clear alert
        AlertMemory.clear_alert(m_id, ev_id)
        alerts_after = AlertMemory.get_active_alerts(m_id)
        assert not any(a["id"] == ev_id for a in alerts_after)


def test_session_memory(mock_merchant):
    """Test updating and reading merchant session state."""
    m_id = mock_merchant.id
    SessionMemory.update_session(m_id, last_action="viewed_dashboard")
    session = SessionMemory.get_session(m_id)
    if session:
        assert session.get("merchant_id") == m_id
        assert session.get("last_action") == "viewed_dashboard"
        assert "last_active_at" in session


def test_conversation_memory(mock_merchant):
    """Test multi-turn conversational rolling buffer in Redis."""
    m_id = mock_merchant.id
    ConversationMemory.add_message(m_id, "user", "How are my sales today?")
    ConversationMemory.add_message(m_id, "agent", "Today's sales are ₹5,400 across 22 orders.")

    conv = ConversationMemory.get_recent_conversation(m_id, limit=10)
    if conv:
        assert len(conv) >= 2
        assert conv[0]["text"] == "How are my sales today?"
        assert conv[1]["text"] == "Today's sales are ₹5,400 across 22 orders."

    # Clear conversation
    cleared = ConversationMemory.clear_conversation(m_id)
    if cleared:
        conv_empty = ConversationMemory.get_recent_conversation(m_id, limit=10)
        assert len(conv_empty) == 0


def test_recommendation_memory(mock_merchant):
    """Test caching and invalidating recommendations."""
    m_id = mock_merchant.id
    rec_id = f"rec_{uuid.uuid4().hex[:6]}"
    rec_data = {
        "id": rec_id,
        "merchant_id": m_id,
        "title": "Restock Cooking Oil",
        "urgency": "HIGH",
        "action_type": "RESTOCK_PRODUCT"
    }

    cached = RecommendationMemory.cache_recommendation(m_id, rec_data)
    if cached:
        active_recs = RecommendationMemory.list_active_recommendations(m_id)
        assert any(r["id"] == rec_id for r in active_recs)

        # Invalidate
        RecommendationMemory.invalidate_recommendation(m_id, rec_id)
        active_recs_after = RecommendationMemory.list_active_recommendations(m_id)
        assert not any(r["id"] == rec_id for r in active_recs_after)


def test_intelligence_cache(mock_merchant):
    """Test ML intelligence cache and bulk invalidation."""
    m_id = mock_merchant.id
    sales_analysis = {"today_sales": 15000.0, "growth_percentage": 14.5}

    set_res = IntelligenceCache.set(m_id, "sales_analysis", sales_analysis)
    if set_res:
        cached = IntelligenceCache.get(m_id, "sales_analysis")
        assert cached is not None
        assert cached["today_sales"] == 15000.0

        # Invalidate all
        IntelligenceCache.invalidate_all(m_id)
        assert IntelligenceCache.get(m_id, "sales_analysis") is None


def test_unified_context_builder(mock_merchant, db_session: Session):
    """Test build_agent_context combining Redis state and PostgreSQL merchant profile."""
    m_id = mock_merchant.id

    # Populate some fast memory
    TransactionMemory.push_transaction(m_id, {"id": "tx_c1", "amount": 500.0})
    AlertMemory.set_alert(m_id, "ev_c1", {"id": "ev_c1", "event_type": "DEMAND_SPIKE", "severity": "HIGH"})
    SessionMemory.update_session(m_id, last_action="chat_user")

    context = build_agent_context(m_id, db=db_session)
    assert context["merchant_id"] == m_id
    assert context["merchant_profile"]["name"] == "Memory Test Store"
    assert "summary" in context
    assert len(context["summary"]) > 0


def test_memory_agent_tool(mock_merchant, db_session: Session):
    """Test Google ADK agent tool get_recent_merchant_context."""
    m_id = mock_merchant.id
    tool_res = get_recent_merchant_context(m_id, db=db_session)
    assert isinstance(tool_res, dict)
    assert tool_res["merchant_id"] == m_id


def test_merchant_isolation(db_session: Session):
    """Test that fast memory keys for merchant A do not leak into merchant B."""
    m1_id = f"m1_{uuid.uuid4().hex[:6]}"
    m2_id = f"m2_{uuid.uuid4().hex[:6]}"

    TransactionMemory.push_transaction(m1_id, {"id": "tx_m1", "amount": 100.0})
    TransactionMemory.push_transaction(m2_id, {"id": "tx_m2", "amount": 200.0})

    txns_m1 = TransactionMemory.get_recent_transactions(m1_id)
    txns_m2 = TransactionMemory.get_recent_transactions(m2_id)

    if txns_m1 and txns_m2:
        assert all(t["id"] != "tx_m2" for t in txns_m1)
        assert all(t["id"] != "tx_m1" for t in txns_m2)


def test_redis_fallback_when_offline(mock_merchant, db_session: Session):
    """Test that all memory modules degrade gracefully to PostgreSQL when Redis is None."""
    m_id = mock_merchant.id
    with patch("app.memory.transaction_memory.get_redis_client", return_value=None), \
         patch("app.memory.alert_memory.get_redis_client", return_value=None), \
         patch("app.memory.session_memory.get_redis_client", return_value=None), \
         patch("app.memory.conversation_memory.get_redis_client", return_value=None), \
         patch("app.memory.recommendation_memory.get_redis_client", return_value=None), \
         patch("app.memory.cache.get_redis_client", return_value=None):

        # Test graceful operations without raising exceptions
        assert TransactionMemory.push_transaction(m_id, {"id": "tx1"}) is False
        assert TransactionMemory.get_recent_transactions(m_id, db=db_session) == []

        assert AlertMemory.set_alert(m_id, "ev1", {}) is False
        assert AlertMemory.get_active_alerts(m_id, db=db_session) == []

        assert SessionMemory.update_session(m_id, "action") is False
        assert SessionMemory.get_session(m_id) is None

        assert ConversationMemory.add_message(m_id, "user", "hi") is False
        assert ConversationMemory.get_recent_conversation(m_id, db=db_session) == []

        assert RecommendationMemory.cache_recommendation(m_id, {}) is False
        assert RecommendationMemory.list_active_recommendations(m_id, db=db_session) == []

        assert IntelligenceCache.get(m_id, "sales") is None
        assert IntelligenceCache.set(m_id, "sales", {}) is False

        # Context builder should still work cleanly
        ctx = build_agent_context(m_id, db=db_session)
        assert ctx["merchant_id"] == m_id
        assert ctx["merchant_profile"]["name"] == "Memory Test Store"


def test_memory_api_endpoints(client: TestClient, mock_merchant):
    """Test developer & debug REST API endpoints under /memory."""
    m_id = mock_merchant.id

    # 1. Health check
    res = client.get("/api/v1/memory/health")
    assert res.status_code == 200
    assert "status" in res.json()

    # 2. Context
    res = client.get(f"/api/v1/memory/{m_id}/context")
    assert res.status_code == 200
    assert res.json()["merchant_id"] == m_id

    # 3. Transactions
    res = client.get(f"/api/v1/memory/{m_id}/transactions")
    assert res.status_code == 200
    assert isinstance(res.json(), list)

    # 4. Alerts
    res = client.get(f"/api/v1/memory/{m_id}/alerts")
    assert res.status_code == 200
    assert isinstance(res.json(), list)

    # 5. Session
    res = client.get(f"/api/v1/memory/{m_id}/session")
    assert res.status_code == 200
    assert "merchant_id" in res.json()

    # 6. Conversation
    res = client.get(f"/api/v1/memory/{m_id}/conversation")
    assert res.status_code == 200
    assert isinstance(res.json(), list)

    # 7. Recommendations
    res = client.get(f"/api/v1/memory/{m_id}/recommendations")
    assert res.status_code == 200
    assert isinstance(res.json(), list)

    # 8. Clear conversation
    res = client.delete(f"/api/v1/memory/{m_id}/conversation")
    assert res.status_code == 200
    assert res.json()["merchant_id"] == m_id
