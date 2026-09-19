"""
Paytm Pulse - Phase 5 Agent Tests
Comprehensive tests for Google ADK / Gemini Business Intelligence Agent, tools, and endpoints.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from app.models.merchant import Merchant, MerchantCategory
from app.models.product import Product
from app.models.inventory import Inventory
from app.models.customer import Customer
from app.models.transaction import Transaction, PaymentMethod
from app.models.business_event import BusinessEvent, EventType, EventSeverity
from app.models.base import utc_now

from app.agent.tools.sales_tools import get_sales_analysis
from app.agent.tools.anomaly_tools import detect_anomalies
from app.agent.tools.forecast_tools import forecast_demand
from app.agent.tools.inventory_tools import predict_stockout, get_all_stockout_risks
from app.agent.tools.customer_tools import get_customer_intelligence
from app.agent.tools.opportunity_tools import detect_opportunities
from app.agent.tools.event_tools import get_business_event
from app.agent.context import build_merchant_context
from app.agent.agent import analyze_business_event, analyze_merchant_health, chat_with_merchant
from app.agent.schemas import AgentAnalysis, ChatResponse


@pytest.fixture
def agent_test_data(db_session):
    """Seed structured realistic test merchant, products, inventory, customers, transactions and events."""
    now = utc_now()
    
    # 1. Merchant
    merchant = Merchant(
        id="m_agent_001",
        name="Sunil Gupta",
        shop_name="Gupta General Store",
        category=MerchantCategory.KIRANA,
        location="Connaught Place, New Delhi",
        language="Hindi",
        phone="+919811002233"
    )
    db_session.add(merchant)

    # 2. Products
    p1 = Product(
        id="p_cold_drinks",
        merchant_id=merchant.id,
        name="Cold Drinks 750ml",
        category="Beverages",
        price=45.0,
        cost_price=35.0,
        current_stock=18,
        reorder_level=25,
        supplier="Delhi Beverage Dist"
    )
    p2 = Product(
        id="p_chips",
        merchant_id=merchant.id,
        name="Masala Chips 50g",
        category="Snacks",
        price=20.0,
        cost_price=14.0,
        current_stock=80,
        reorder_level=30,
        supplier="Delhi Snack Corp"
    )
    db_session.add_all([p1, p2])

    # 3. Inventory
    inv1 = Inventory(
        id="inv_cd_001",
        product_id=p1.id,
        current_stock=18,
        reorder_level=25,
        maximum_stock=100
    )
    inv2 = Inventory(
        id="inv_ch_001",
        product_id=p2.id,
        current_stock=80,
        reorder_level=30,
        maximum_stock=150
    )
    db_session.add_all([inv1, inv2])

    # 4. Customers
    c1 = Customer(
        id="c_vip_001",
        merchant_id=merchant.id,
        name="Aman Sharma",
        phone="+919876500001",
        purchase_count=12,
        total_spend=3200.0,
        last_purchase_at=now - timedelta(days=2)
    )
    c2 = Customer(
        id="c_churn_001",
        merchant_id=merchant.id,
        name="Rahul Verma",
        phone="+919876500002",
        purchase_count=8,
        total_spend=1850.0,
        last_purchase_at=now - timedelta(days=45)
    )
    db_session.add_all([c1, c2])

    # 5. Transactions across past 14 days
    for day_offset in range(14):
        tx_time = now - timedelta(days=day_offset, hours=2)
        t = Transaction(
            merchant_id=merchant.id,
            customer_id=c1.id if day_offset % 2 == 0 else c2.id,
            product_id=p1.id if day_offset % 3 == 0 else p2.id,
            quantity=3 if day_offset == 0 else 2,
            unit_price=45.0 if day_offset % 3 == 0 else 20.0,
            amount=135.0 if day_offset == 0 else 40.0,
            payment_method=PaymentMethod.UPI,
            transaction_timestamp=tx_time,
            created_at=tx_time
        )
        db_session.add(t)

    # 6. Business Events
    ev1 = BusinessEvent(
        id="ev_demand_spike_001",
        merchant_id=merchant.id,
        event_type=EventType.DEMAND_SPIKE,
        severity=EventSeverity.HIGH,
        source="rule_engine",
        payload={"product_id": p1.id, "spike_ratio": 2.5, "current_rate": 8},
        detected_at=now - timedelta(minutes=5)
    )
    ev2 = BusinessEvent(
        id="ev_stockout_001",
        merchant_id=merchant.id,
        event_type=EventType.STOCKOUT_RISK,
        severity=EventSeverity.HIGH,
        source="rule_engine",
        payload={"product_id": p1.id, "current_stock": 18, "reorder_level": 25},
        detected_at=now - timedelta(minutes=10)
    )
    ev3 = BusinessEvent(
        id="ev_sales_decline_001",
        merchant_id=merchant.id,
        event_type=EventType.SALES_DECLINE,
        severity=EventSeverity.MEDIUM,
        source="rule_engine",
        payload={"decline_percentage": 0.35},
        detected_at=now - timedelta(minutes=15)
    )
    db_session.add_all([ev1, ev2, ev3])
    db_session.commit()

    return {
        "merchant": merchant,
        "product1": p1,
        "product2": p2,
        "event1": ev1,
        "event2": ev2,
        "event3": ev3
    }


# =============================================================================
# 1. AGENT TOOLS TESTS
# =============================================================================

def test_tool_get_sales_analysis(agent_test_data, db_session):
    merchant_id = agent_test_data["merchant"].id
    res = get_sales_analysis(merchant_id, db=db_session)
    assert res["merchant_id"] == merchant_id
    assert "today_sales" in res
    assert "average_daily_sales" in res
    assert "growth_percentage" in res
    assert "transaction_count" in res
    assert "top_products" in res
    assert isinstance(res["top_products"], list)


def test_tool_detect_anomalies(agent_test_data, db_session):
    merchant_id = agent_test_data["merchant"].id
    product_id = agent_test_data["product1"].id
    
    # Merchant level
    res1 = detect_anomalies(merchant_id, db=db_session)
    assert res1["merchant_id"] == merchant_id
    assert "anomaly_detected" in res1
    assert "type" in res1
    assert "confidence" in res1

    # Product level
    res2 = detect_anomalies(merchant_id, product_id=product_id, db=db_session)
    assert res2["product_id"] == product_id
    assert "observed_value" in res2


def test_tool_forecast_demand(agent_test_data, db_session):
    merchant_id = agent_test_data["merchant"].id
    product_id = agent_test_data["product1"].id
    res = forecast_demand(merchant_id, product_id, horizon="next_hour", db=db_session)
    assert res["merchant_id"] == merchant_id
    assert res["product_id"] == product_id
    assert res["product"] == "Cold Drinks 750ml"
    assert "forecast_demand" in res
    assert "baseline_demand" in res
    assert res["horizon"] == "next_hour"


def test_tool_predict_stockout(agent_test_data, db_session):
    merchant_id = agent_test_data["merchant"].id
    product_id = agent_test_data["product1"].id
    res = predict_stockout(merchant_id, product_id, db=db_session)
    assert res["product"] == "Cold Drinks 750ml"
    assert res["current_stock"] == 18
    assert "estimated_hours_to_stockout" in res
    assert "risk" in res
    assert res["risk"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]


def test_tool_get_all_stockout_risks(agent_test_data, db_session):
    merchant_id = agent_test_data["merchant"].id
    res = get_all_stockout_risks(merchant_id, db=db_session)
    assert res["merchant_id"] == merchant_id
    assert "total_at_risk" in res
    assert "at_risk_products" in res


def test_tool_get_customer_intelligence(agent_test_data, db_session):
    merchant_id = agent_test_data["merchant"].id
    res = get_customer_intelligence(merchant_id, db=db_session)
    assert res["merchant_id"] == merchant_id
    assert res["total_customers"] == 2
    assert "segments_summary" in res
    assert "high_value_customers" in res
    assert "at_risk_customers" in res


def test_tool_detect_opportunities(agent_test_data, db_session):
    merchant_id = agent_test_data["merchant"].id
    res = detect_opportunities(merchant_id, db=db_session)
    assert res["merchant_id"] == merchant_id
    assert "total_opportunities" in res
    assert "categories" in res
    assert "RESTOCK" in res["categories"]


def test_tool_get_business_event(agent_test_data, db_session):
    event_id = agent_test_data["event1"].id
    res = get_business_event(event_id, db=db_session)
    assert res["found"] is True
    assert res["event_type"] == "DEMAND_SPIKE"
    assert res["severity"] == "HIGH"
    assert res["product_id"] == "p_cold_drinks"


def test_merchant_context_builder(agent_test_data, db_session):
    merchant_id = agent_test_data["merchant"].id
    ctx = build_merchant_context(merchant_id, db=db_session)
    assert ctx["found"] is True
    assert ctx["shop_name"] == "Gupta General Store"
    assert ctx["category"] == "KIRANA"
    assert ctx["total_products_count"] == 2
    assert len(ctx["recent_events"]) > 0


# =============================================================================
# 2. AGENT REASONING ON BUSINESS EVENTS & GENERAL HEALTH
# =============================================================================

def test_agent_analyze_event_demand_spike(agent_test_data, db_session):
    event_id = agent_test_data["event1"].id
    analysis: AgentAnalysis = analyze_business_event(event_id, db=db_session)
    assert analysis.event_id == event_id
    assert analysis.merchant_id == agent_test_data["merchant"].id
    assert len(analysis.summary) > 0
    assert len(analysis.evidence) >= 1
    assert analysis.impact.estimated_value >= 0.0
    assert analysis.urgency in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    assert analysis.confidence >= 0.5
    assert analysis.suggested_action_type in ["RESTOCK", "LAUNCH_PROMOTION", "CUSTOMER_WINBACK", "MONITOR"]


def test_agent_analyze_event_stockout(agent_test_data, db_session):
    event_id = agent_test_data["event2"].id
    analysis: AgentAnalysis = analyze_business_event(event_id, db=db_session)
    assert analysis.event_id == event_id
    assert "stock" in analysis.summary.lower() or "inventory" in analysis.summary.lower() or "cold drink" in analysis.summary.lower()
    assert analysis.suggested_action_type == "RESTOCK"


def test_agent_analyze_event_sales_decline(agent_test_data, db_session):
    event_id = agent_test_data["event3"].id
    analysis: AgentAnalysis = analyze_business_event(event_id, db=db_session)
    assert analysis.event_id == event_id
    assert analysis.suggested_action_type in ["LAUNCH_PROMOTION", "MONITOR"]


def test_agent_analyze_merchant_health(agent_test_data, db_session):
    merchant_id = agent_test_data["merchant"].id
    analysis: AgentAnalysis = analyze_merchant_health(merchant_id, db=db_session)
    assert analysis.merchant_id == merchant_id
    assert analysis.event_id is None
    assert len(analysis.evidence) >= 1
    assert analysis.impact.currency == "INR"


# =============================================================================
# 3. MERCHANT CONVERSATIONAL CHAT
# =============================================================================

def test_agent_chat_sales_query(agent_test_data, db_session):
    merchant_id = agent_test_data["merchant"].id
    res: ChatResponse = chat_with_merchant(merchant_id, "How are my sales today?", db=db_session)
    assert res.merchant_id == merchant_id
    assert "sales" in res.response.lower() or "₹" in res.response or "transactions" in res.response.lower()
    assert "today_sales" in res.supporting_data or "sales" in res.supporting_data


def test_agent_chat_top_product_query(agent_test_data, db_session):
    merchant_id = agent_test_data["merchant"].id
    res: ChatResponse = chat_with_merchant(merchant_id, "Which product is selling the most?", db=db_session)
    assert res.merchant_id == merchant_id
    assert len(res.response) > 10


def test_agent_chat_stock_query(agent_test_data, db_session):
    merchant_id = agent_test_data["merchant"].id
    res: ChatResponse = chat_with_merchant(merchant_id, "Which products may run out soon?", db=db_session)
    assert res.merchant_id == merchant_id
    assert len(res.response) > 10


def test_agent_chat_customer_inactivity_query(agent_test_data, db_session):
    merchant_id = agent_test_data["merchant"].id
    res: ChatResponse = chat_with_merchant(merchant_id, "Which customers have become inactive?", db=db_session)
    assert res.merchant_id == merchant_id
    assert "customer" in res.response.lower() or "ग्राहक" in res.response or len(res.response) > 10


def test_agent_chat_opportunities_query(agent_test_data, db_session):
    merchant_id = agent_test_data["merchant"].id
    res: ChatResponse = chat_with_merchant(merchant_id, "What opportunities do I have today?", db=db_session)
    assert res.merchant_id == merchant_id
    assert len(res.response) > 10


# =============================================================================
# 4. REST API ENDPOINTS INTEGRATION TESTS
# =============================================================================

def test_api_analyze_event_endpoint(client, agent_test_data):
    event_id = agent_test_data["event1"].id
    resp = client.post("/api/v1/agent/analyze-event", json={"event_id": event_id})
    assert resp.status_code == 200
    data = resp.json()
    assert data["event_id"] == event_id
    assert data["merchant_id"] == agent_test_data["merchant"].id
    assert "evidence" in data
    assert "impact" in data


def test_api_analyze_merchant_endpoint(client, agent_test_data):
    merchant_id = agent_test_data["merchant"].id
    resp = client.post("/api/v1/agent/analyze-merchant", json={"merchant_id": merchant_id})
    assert resp.status_code == 200
    data = resp.json()
    assert data["merchant_id"] == merchant_id
    assert "summary" in data


def test_api_chat_endpoint(client, agent_test_data):
    merchant_id = agent_test_data["merchant"].id
    resp = client.post("/api/v1/agent/chat", json={
        "merchant_id": merchant_id,
        "message": "What should I pay attention to?"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["merchant_id"] == merchant_id
    assert "response" in data
    assert len(data["response"]) > 5


# =============================================================================
# 5. ERROR HANDLING & MOCK GEMINI TESTS
# =============================================================================

def test_api_analyze_event_invalid_id(client):
    resp = client.post("/api/v1/agent/analyze-event", json={"event_id": "non_existent_event_999"})
    assert resp.status_code == 404


def test_api_analyze_merchant_invalid_id(client):
    resp = client.post("/api/v1/agent/analyze-merchant", json={"merchant_id": "non_existent_merchant_999"})
    assert resp.status_code == 404


def test_agent_with_mocked_gemini_llm(agent_test_data, db_session):
    """Test agent runner when ADK Agent responds with custom structured JSON."""
    from app.agent.runner import AgentRunner

    mock_analysis_json = {
        "summary": "Cold drinks surge observed with projected stockout.",
        "detected_issue": "Surging Demand and Inventory Shortage",
        "evidence": [
            "Demand is 48% above baseline",
            "Forecast indicates 12 units next hour"
        ],
        "impact": {
            "type": "POTENTIAL_REVENUE_LOSS",
            "estimated_value": 1500.0,
            "currency": "INR"
        },
        "urgency": "HIGH",
        "confidence": 0.94,
        "recommendation": "Restock 50 units of Cold Drinks immediately.",
        "suggested_action_type": "RESTOCK"
    }

    runner = AgentRunner(db_session)
    runner.adk_agent.run_investigation = MagicMock(return_value=(mock_analysis_json, ["get_sales_analysis", "simulate_business_action"], True))

    event_id = agent_test_data["event1"].id
    analysis = runner.run_event_analysis(event_id)

    assert analysis.event_id == event_id
    assert analysis.confidence == 0.94
    assert analysis.detected_issue == "Surging Demand and Inventory Shortage"
    assert analysis.suggested_action_type == "RESTOCK"
    assert runner.adk_agent.run_investigation.called
