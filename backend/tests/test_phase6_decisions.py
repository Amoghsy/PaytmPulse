"""
Paytm Pulse - Phase 6 Decision Engine Tests
Comprehensive unit and integration tests for candidate generation, multi-factor scoring,
conflict resolution, deduplication, and approval state transitions.
"""

import pytest
from datetime import datetime, timedelta
import json

from app.models.merchant import Merchant, MerchantCategory
from app.models.product import Product
from app.models.inventory import Inventory
from app.models.customer import Customer
from app.models.transaction import Transaction, PaymentMethod
from app.models.business_event import BusinessEvent, EventType, EventSeverity
from app.models.recommendation import Recommendation, RecommendationType, RecommendationStatus
from app.models.action import Action, ActionType, ActionStatus
from app.models.base import utc_now

from app.decision.engine import DecisionEngine
from app.decision.schemas import NextBestAction, DecisionResponse
from app.decision.rules import (
    calculate_recommended_restock_quantity,
    build_promotion_parameters,
    build_customer_winback_parameters,
    validate_action_parameters
)
from app.decision.impact_estimator import (
    estimate_stockout_protection_impact,
    estimate_promotion_impact,
    estimate_customer_winback_impact
)
from app.agent.tools.decision_tools import generate_next_best_actions


@pytest.fixture
def decision_test_data(db_session):
    """Seed merchant, products, inventory, customers, and events for decision engine testing."""
    now = utc_now()

    merchant = Merchant(
        id="m_dec_001",
        name="Ramesh Sharma",
        shop_name="Sharma Kirana Stores",
        category=MerchantCategory.KIRANA,
        location="Sector 18, Noida",
        language="Hindi",
        phone="+919811009988"
    )
    db_session.add(merchant)

    # Products
    p1 = Product(
        id="p_dec_cold_drinks",
        merchant_id=merchant.id,
        name="Cold Drink 750ml",
        category="Beverages",
        price=45.0,
        cost_price=35.0,
        current_stock=8,
        reorder_level=20,
        supplier="Delhi Beverage Co"
    )
    p2 = Product(
        id="p_dec_chips",
        merchant_id=merchant.id,
        name="Potato Chips 50g",
        category="Snacks",
        price=20.0,
        cost_price=15.0,
        current_stock=90,
        reorder_level=25,
        supplier="Delhi Snack Dist"
    )
    db_session.add_all([p1, p2])

    # Inventory
    inv1 = Inventory(
        id="inv_dec_001",
        product_id=p1.id,
        current_stock=8,
        reorder_level=20,
        maximum_stock=100
    )
    inv2 = Inventory(
        id="inv_dec_002",
        product_id=p2.id,
        current_stock=90,
        reorder_level=25,
        maximum_stock=150
    )
    db_session.add_all([inv1, inv2])

    # Customers
    c1 = Customer(
        id="c_dec_001",
        merchant_id=merchant.id,
        name="Vikas Gupta",
        phone="+919876540001",
        purchase_count=10,
        total_spend=2500.0,
        last_purchase_at=now - timedelta(days=3)
    )
    c2 = Customer(
        id="c_dec_002",
        merchant_id=merchant.id,
        name="Anil Kumar",
        phone="+919876540002",
        purchase_count=5,
        total_spend=1200.0,
        last_purchase_at=now - timedelta(days=40)
    )
    db_session.add_all([c1, c2])

    # Transactions
    for day in range(10):
        t_time = now - timedelta(days=day, hours=1)
        t = Transaction(
            merchant_id=merchant.id,
            customer_id=c1.id if day % 2 == 0 else c2.id,
            product_id=p1.id if day % 2 == 0 else p2.id,
            quantity=2,
            unit_price=45.0 if day % 2 == 0 else 20.0,
            amount=90.0 if day % 2 == 0 else 40.0,
            payment_method=PaymentMethod.UPI,
            transaction_timestamp=t_time,
            created_at=t_time
        )
        db_session.add(t)

    # Events
    ev_spike = BusinessEvent(
        id="ev_dec_spike_001",
        merchant_id=merchant.id,
        event_type=EventType.DEMAND_SPIKE,
        severity=EventSeverity.HIGH,
        source="rule_engine",
        payload={"product_id": p1.id, "spike_ratio": 2.2},
        detected_at=now - timedelta(minutes=5)
    )
    ev_stockout = BusinessEvent(
        id="ev_dec_stockout_001",
        merchant_id=merchant.id,
        event_type=EventType.STOCKOUT_RISK,
        severity=EventSeverity.CRITICAL,
        source="rule_engine",
        payload={"product_id": p1.id, "current_stock": 8},
        detected_at=now - timedelta(minutes=8)
    )
    ev_decline = BusinessEvent(
        id="ev_dec_decline_001",
        merchant_id=merchant.id,
        event_type=EventType.SALES_DECLINE,
        severity=EventSeverity.MEDIUM,
        source="rule_engine",
        payload={"decline_percentage": 0.40},
        detected_at=now - timedelta(minutes=12)
    )
    ev_cust = BusinessEvent(
        id="ev_dec_cust_001",
        merchant_id=merchant.id,
        event_type=EventType.CUSTOMER_RISK,
        severity=EventSeverity.MEDIUM,
        source="rule_engine",
        payload={"inactive_days": 40},
        detected_at=now - timedelta(minutes=14)
    )
    db_session.add_all([ev_spike, ev_stockout, ev_decline, ev_cust])
    db_session.commit()

    return {
        "merchant": merchant,
        "product1": p1,
        "product2": p2,
        "ev_spike": ev_spike,
        "ev_stockout": ev_stockout,
        "ev_decline": ev_decline,
        "ev_cust": ev_cust
    }


# =============================================================================
# 1. RULES & IMPACT ESTIMATOR TESTS
# =============================================================================

def test_calculate_recommended_restock_quantity():
    # Current stock 8, reorder level 20, max 100, hourly demand 3.0
    # target stock = (3.0 * 24) + (3.0 * 4) = 72 + 12 = 84
    # needed = 84 - 8 = 76
    qty = calculate_recommended_restock_quantity(
        current_stock=8,
        reorder_level=20,
        maximum_stock=100,
        forecast_hourly_demand=3.0,
        average_daily_sales_units=20.0
    )
    assert 50 <= qty <= 100
    assert qty <= 100


def test_build_promotion_parameters_bounding():
    # Exceeding discount cap should be bounded to 25%
    p = build_promotion_parameters(product_id="p1", product_price=100.0, suggested_discount=40.0)
    assert p["discount_percentage"] == 25.0
    assert p["promotional_price"] == 75.0

    # Below minimum discount should be bounded to 5%
    p_low = build_promotion_parameters(product_id="p1", product_price=100.0, suggested_discount=2.0)
    assert p_low["discount_percentage"] == 5.0


def test_validate_action_parameters():
    # Valid restock
    valid_r, msg = validate_action_parameters("RESTOCK_PRODUCT", {"product_id": "p1", "quantity": 20})
    assert valid_r is True

    # Invalid restock (negative quantity)
    invalid_r, msg = validate_action_parameters("RESTOCK_PRODUCT", {"product_id": "p1", "quantity": -5})
    assert invalid_r is False

    # Invalid promotion (> 25% discount)
    invalid_p, msg = validate_action_parameters("RUN_PROMOTION", {"discount_percentage": 50})
    assert invalid_p is False


def test_impact_estimators():
    imp_stockout = estimate_stockout_protection_impact(product_price=50.0, current_stock=5, forecast_hourly_demand=2.0, hours_runway=2.0)
    assert imp_stockout.type == "REVENUE_PROTECTED"
    assert imp_stockout.value > 0.0

    imp_promo = estimate_promotion_impact(product_price=40.0, average_daily_sales=1000.0, discount_percentage=10.0)
    assert imp_promo.type == "INCREMENTAL_REVENUE"
    assert imp_promo.value > 0.0

    imp_winback = estimate_customer_winback_impact(at_risk_customers_count=3, avg_customer_historical_spend=1500.0)
    assert imp_winback.type == "RECOVERED_REVENUE"
    assert imp_winback.value > 0.0


# =============================================================================
# 2. DECISION ENGINE SCENARIOS & SCORING TESTS
# =============================================================================

def test_decision_on_demand_spike(decision_test_data, db_session):
    engine = DecisionEngine(db_session)
    merchant_id = decision_test_data["merchant"].id
    event_id = decision_test_data["ev_spike"].id

    resp: DecisionResponse = engine.generate_decision(merchant_id=merchant_id, event_id=event_id)
    assert resp.merchant_id == merchant_id
    assert resp.event_id == event_id
    assert resp.next_best_action is not None
    assert resp.next_best_action.action_type == "RESTOCK_PRODUCT"
    assert resp.next_best_action.status == "PENDING_APPROVAL"
    assert resp.next_best_action.priority in ["CRITICAL", "HIGH"]
    assert len(resp.alternative_actions) >= 1


def test_decision_on_stockout_risk(decision_test_data, db_session):
    engine = DecisionEngine(db_session)
    merchant_id = decision_test_data["merchant"].id
    event_id = decision_test_data["ev_stockout"].id

    resp: DecisionResponse = engine.generate_decision(merchant_id=merchant_id, event_id=event_id)
    assert resp.next_best_action.action_type == "RESTOCK_PRODUCT"
    assert resp.next_best_action.priority == "CRITICAL"
    assert resp.next_best_action.parameters["quantity"] > 0


def test_decision_on_sales_decline(decision_test_data, db_session):
    engine = DecisionEngine(db_session)
    merchant_id = decision_test_data["merchant"].id
    event_id = decision_test_data["ev_decline"].id

    resp: DecisionResponse = engine.generate_decision(merchant_id=merchant_id, event_id=event_id)
    assert resp.next_best_action.action_type in ["RUN_PROMOTION", "CUSTOMER_WINBACK"]
    assert resp.next_best_action.estimated_impact.value > 0.0


def test_decision_on_customer_risk(decision_test_data, db_session):
    engine = DecisionEngine(db_session)
    merchant_id = decision_test_data["merchant"].id
    event_id = decision_test_data["ev_cust"].id

    resp: DecisionResponse = engine.generate_decision(merchant_id=merchant_id, event_id=event_id)
    assert resp.next_best_action.action_type == "CUSTOMER_WINBACK"
    assert resp.next_best_action.parameters["customer_segment"] == "AT_RISK"


def test_decision_general_merchant_health(decision_test_data, db_session):
    engine = DecisionEngine(db_session)
    merchant_id = decision_test_data["merchant"].id

    resp: DecisionResponse = engine.generate_decision(merchant_id=merchant_id, event_id=None)
    assert resp.merchant_id == merchant_id
    assert resp.next_best_action is not None
    assert resp.next_best_action.requires_approval is True


def test_decision_deduplication_cooldown(decision_test_data, db_session):
    engine = DecisionEngine(db_session)
    merchant_id = decision_test_data["merchant"].id
    event_id = decision_test_data["ev_spike"].id

    resp1 = engine.generate_decision(merchant_id=merchant_id, event_id=event_id)
    resp2 = engine.generate_decision(merchant_id=merchant_id, event_id=event_id)

    # Second call should return existing recommendation without creating duplicates
    assert resp1.next_best_action.id == resp2.next_best_action.id
    recs = db_session.query(Recommendation).filter(
        Recommendation.merchant_id == merchant_id,
        Recommendation.event_id == event_id
    ).all()
    assert len(recs) == 1


# =============================================================================
# 3. APPROVAL & REJECTION WORKFLOW TESTS
# =============================================================================

def test_decision_approval_flow(decision_test_data, db_session):
    engine = DecisionEngine(db_session)
    merchant_id = decision_test_data["merchant"].id
    event_id = decision_test_data["ev_spike"].id

    resp = engine.generate_decision(merchant_id=merchant_id, event_id=event_id)
    decision_id = resp.next_best_action.id

    # Verify initial pending status
    pending_list = engine.get_pending_decisions(merchant_id)
    assert any(d.id == decision_id for d in pending_list)

    # Approve
    app_resp = engine.approve_decision(decision_id)
    assert app_resp.status == "APPROVED"

    # Verify state in DB
    rec = db_session.query(Recommendation).filter(Recommendation.id == decision_id).first()
    assert rec.status == RecommendationStatus.APPROVED

    action = db_session.query(Action).filter(Action.recommendation_id == decision_id).first()
    assert action.status == ActionStatus.APPROVED
    assert action.approved_at is not None

    # Should no longer be in pending list
    pending_after = engine.get_pending_decisions(merchant_id)
    assert not any(d.id == decision_id for d in pending_after)


def test_decision_rejection_flow(decision_test_data, db_session):
    engine = DecisionEngine(db_session)
    merchant_id = decision_test_data["merchant"].id
    event_id = decision_test_data["ev_decline"].id

    resp = engine.generate_decision(merchant_id=merchant_id, event_id=event_id)
    decision_id = resp.next_best_action.id

    # Reject
    rej_resp = engine.reject_decision(decision_id)
    assert rej_resp.status == "REJECTED"

    rec = db_session.query(Recommendation).filter(Recommendation.id == decision_id).first()
    assert rec.status == RecommendationStatus.REJECTED


# =============================================================================
# 4. REST API ENDPOINTS TESTS
# =============================================================================

def test_api_generate_decision_endpoint(client, decision_test_data):
    merchant_id = decision_test_data["merchant"].id
    event_id = decision_test_data["ev_spike"].id

    resp = client.post("/api/v1/decisions/generate", json={
        "merchant_id": merchant_id,
        "event_id": event_id
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["merchant_id"] == merchant_id
    assert data["next_best_action"]["action_type"] == "RESTOCK_PRODUCT"
    assert "estimated_impact" in data["next_best_action"]


def test_api_get_pending_decisions(client, decision_test_data):
    merchant_id = decision_test_data["merchant"].id
    event_id = decision_test_data["ev_spike"].id

    # Generate first
    client.post("/api/v1/decisions/generate", json={"merchant_id": merchant_id, "event_id": event_id})

    # Fetch pending
    resp = client.get(f"/api/v1/decisions/{merchant_id}/pending")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["status"] == "PENDING_APPROVAL"


def test_api_approve_decision_endpoint(client, decision_test_data):
    merchant_id = decision_test_data["merchant"].id
    event_id = decision_test_data["ev_spike"].id

    gen_resp = client.post("/api/v1/decisions/generate", json={"merchant_id": merchant_id, "event_id": event_id})
    decision_id = gen_resp.json()["next_best_action"]["id"]

    app_resp = client.post(f"/api/v1/decisions/{decision_id}/approve")
    assert app_resp.status_code == 200
    assert app_resp.json()["status"] == "APPROVED"


def test_api_reject_decision_endpoint(client, decision_test_data):
    merchant_id = decision_test_data["merchant"].id
    event_id = decision_test_data["ev_decline"].id

    gen_resp = client.post("/api/v1/decisions/generate", json={"merchant_id": merchant_id, "event_id": event_id})
    decision_id = gen_resp.json()["next_best_action"]["id"]

    rej_resp = client.post(f"/api/v1/decisions/{decision_id}/reject")
    assert rej_resp.status_code == 200
    assert rej_resp.json()["status"] == "REJECTED"


# =============================================================================
# 5. ADK AGENT DECISION TOOL TEST
# =============================================================================

def test_agent_tool_generate_next_best_actions(decision_test_data, db_session):
    merchant_id = decision_test_data["merchant"].id
    event_id = decision_test_data["ev_spike"].id

    tool_res = generate_next_best_actions(merchant_id=merchant_id, event_id=event_id, db=db_session)
    assert tool_res["merchant_id"] == merchant_id
    assert "next_best_action" in tool_res
    assert tool_res["next_best_action"]["action_type"] == "RESTOCK_PRODUCT"
