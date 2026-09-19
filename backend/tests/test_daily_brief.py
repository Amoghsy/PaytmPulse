"""
Paytm Pulse - Phase 8 AI Daily Business Brief Comprehensive Test Suite
Tests context collection, Gemini generative AI summarization, deterministic fallback synthesis,
multi-merchant isolation, idempotency, and WhatsApp notification delivery.
"""

import pytest
from datetime import datetime, timezone
from app.models import (
    Merchant, MerchantCategory,
    Product, Inventory,
    Customer, Transaction, PaymentMethod,
    BusinessEvent, EventType, EventSeverity,
    BusinessBrief, BriefGenerationSource
)
from app.services.brief_service import (
    collect_merchant_brief_context,
    generate_brief_with_gemini,
    generate_deterministic_fallback_brief,
    store_business_brief,
    get_latest_brief,
    send_brief_whatsapp_notification
)


@pytest.fixture
def seeded_brief_environment(db_session):
    """Creates two distinct merchants with inventory, transactions, and events."""
    # Merchant A (Kirana, English, Bengaluru)
    merchant_a = Merchant(
        id="m_kirana_001",
        name="Ravi Kumar",
        shop_name="Ravi General Store",
        category=MerchantCategory.KIRANA,
        location="Bengaluru",
        language="English",
        phone="9876543210"
    )

    # Merchant B (Pharmacy, Kannada, Bengaluru)
    merchant_b = Merchant(
        id="m_pharmacy_002",
        name="Dr. Ananya",
        shop_name="Ananya Health Pharmacy",
        category=MerchantCategory.PHARMACY,
        location="Bengaluru",
        language="Kannada",
        phone="9876543211"
    )
    db_session.add_all([merchant_a, merchant_b])
    db_session.commit()

    # Products for Merchant A
    prod_a1 = Product(id="p_atta_001", merchant_id="m_kirana_001", name="Aashirvaad Atta 5kg", category="GROCERY", unit_price=245.0, cost_price=210.0)
    prod_a2 = Product(id="p_oil_002", merchant_id="m_kirana_001", name="Fortune Sunlite Oil 1L", category="EDIBLE_OIL", unit_price=155.0, cost_price=135.0)
    prod_b1 = Product(id="p_para_003", merchant_id="m_pharmacy_002", name="Paracetamol 650mg", category="MEDICINE", unit_price=30.0, cost_price=18.0)
    db_session.add_all([prod_a1, prod_a2, prod_b1])
    db_session.commit()

    # Inventory: prod_a2 is low stock (stockout risk)
    inv_a1 = Inventory(id="inv_1", merchant_id="m_kirana_001", product_id="p_atta_001", current_stock=40, safety_stock_threshold=10, reorder_point=15)
    inv_a2 = Inventory(id="inv_2", merchant_id="m_kirana_001", product_id="p_oil_002", current_stock=2, safety_stock_threshold=10, reorder_point=15)
    inv_b1 = Inventory(id="inv_3", merchant_id="m_pharmacy_002", product_id="p_para_003", current_stock=100, safety_stock_threshold=20, reorder_point=30)
    db_session.add_all([inv_a1, inv_a2, inv_b1])
    db_session.commit()

    # Customers
    cust_1 = Customer(id="c_1", merchant_id="m_kirana_001", name="Suresh", phone="9900011122", total_orders=8, total_spent=4500.0)
    cust_2 = Customer(id="c_2", merchant_id="m_kirana_001", name="Meena", phone="9900011133", total_orders=1, total_spent=300.0)
    cust_b = Customer(id="c_3", merchant_id="m_pharmacy_002", name="Pooja", phone="9900011144", total_orders=3, total_spent=600.0)
    db_session.add_all([cust_1, cust_2, cust_b])
    db_session.commit()

    # Transactions for Merchant A (Strong sales)
    t1 = Transaction(id="tx_1", merchant_id="m_kirana_001", product_id="p_atta_001", customer_id="c_1", quantity=3, unit_price=245.0, amount=735.0, payment_method=PaymentMethod.UPI)
    t2 = Transaction(id="tx_2", merchant_id="m_kirana_001", product_id="p_oil_002", customer_id="c_2", quantity=2, unit_price=155.0, amount=310.0, payment_method=PaymentMethod.WALLET)
    db_session.add_all([t1, t2])
    db_session.commit()

    # Business Event for Merchant A
    ev_1 = BusinessEvent(
        id="evt_stockout_01",
        merchant_id="m_kirana_001",
        product_id="p_oil_002",
        event_type=EventType.STOCKOUT_RISK,
        severity=EventSeverity.HIGH,
        title="Stockout Risk: Fortune Sunlite Oil 1L",
        description="Fortune Sunlite Oil 1L stock dropped to 2 units.",
        payload={"current_stock": 2, "threshold": 10}
    )
    db_session.add(ev_1)
    db_session.commit()

    return {
        "merchant_a": merchant_a,
        "merchant_b": merchant_b,
        "prod_a1": prod_a1,
        "prod_a2": prod_a2
    }


def test_1_normal_merchant_brief_context_collection(seeded_brief_environment, db_session):
    """Test 1: Verify structured brief context collection gathers all multi-horizon intelligence safely."""
    context = collect_merchant_brief_context("m_kirana_001", db=db_session)
    assert context is not None
    assert context["merchant"]["id"] == "m_kirana_001"
    assert context["merchant"]["shop_name"] == "Ravi General Store"
    assert "sales" in context
    assert "inventory_risks" in context
    assert "customer_intelligence" in context
    assert "opportunities" in context
    assert "recent_events" in context

    # Check that PII is protected (no password, API keys, etc.)
    assert "password" not in context["merchant"]


def test_2_sales_analysis_integration_in_brief(seeded_brief_environment, db_session):
    """Test 2: Verify sales analysis metrics and trends are integrated into the brief."""
    context = collect_merchant_brief_context("m_kirana_001", db=db_session)
    brief = generate_deterministic_fallback_brief(context, language="en")

    assert "key_metrics" in brief
    sales_kpi = next((m for m in brief["key_metrics"] if "sales" in m["label"].lower()), None)
    assert sales_kpi is not None
    assert "₹" in sales_kpi["value"]
    assert sales_kpi["trend"] in ["UP", "DOWN", "FLAT"]


def test_3_stockout_risk_identification_in_brief(seeded_brief_environment, db_session):
    """Test 3: Verify that low-stock products appear in attention items and recommended actions."""
    context = collect_merchant_brief_context("m_kirana_001", db=db_session)
    brief = generate_deterministic_fallback_brief(context, language="en")

    assert len(brief["attention_items"]) > 0
    attention = brief["attention_items"][0]
    assert attention["type"] == "STOCKOUT_RISK"
    assert "Fortune Sunlite Oil" in attention["title"]
    assert attention["urgency"] in ["HIGH", "MEDIUM"]

    # Recommended action should advise restocking Fortune Oil
    assert len(brief["recommended_actions"]) > 0
    action = brief["recommended_actions"][0]
    assert action["action_type"] == "RESTOCK_PRODUCT"
    assert action["requires_approval"] is True


def test_4_customer_opportunities_in_brief(seeded_brief_environment, db_session):
    """Test 4: Verify customer intelligence and opportunity detection in brief."""
    context = collect_merchant_brief_context("m_kirana_001", db=db_session)
    assert context["customer_intelligence"]["total_customers"] == 2

    brief = generate_deterministic_fallback_brief(context, language="en")
    assert isinstance(brief["opportunities"], list)
    assert len(brief["key_metrics"]) >= 3


def test_5_multiple_merchants_isolation(seeded_brief_environment, db_session):
    """Test 5: Verify strict tenant isolation. Merchant A data must never leak into Merchant B."""
    context_a = collect_merchant_brief_context("m_kirana_001", db=db_session)
    context_b = collect_merchant_brief_context("m_pharmacy_002", db=db_session)

    assert context_a["merchant"]["shop_name"] == "Ravi General Store"
    assert context_b["merchant"]["shop_name"] == "Ananya Health Pharmacy"

    # Verify products do not leak
    prod_names_a = [p.get("product_name") for p in context_a["inventory_risks"]]
    prod_names_b = [p.get("product_name") for p in context_b["inventory_risks"]]

    assert "Paracetamol 650mg" not in prod_names_a
    assert "Aashirvaad Atta 5kg" not in prod_names_b


def test_6_deterministic_fallback_when_gemini_unavailable(seeded_brief_environment, db_session, monkeypatch):
    """Test 6: Verify deterministic fallback activates when GOOGLE_API_KEY is missing or invalid."""
    monkeypatch.setenv("GOOGLE_API_KEY", "")
    context = collect_merchant_brief_context("m_kirana_001", db=db_session)
    brief, source = generate_brief_with_gemini(context, language="en")

    assert source == BriefGenerationSource.FALLBACK.value
    assert brief["headline"] is not None
    assert brief["summary"] is not None
    assert len(brief["key_metrics"]) > 0


def test_7_whatsapp_notification_dispatch_and_mock(seeded_brief_environment, db_session, client):
    """Test 7: Verify WhatsApp notification endpoint works and updates delivery flag."""
    context = collect_merchant_brief_context("m_kirana_001", db=db_session)
    brief_content = generate_deterministic_fallback_brief(context, language="en")
    brief = store_business_brief(
        merchant_id="m_kirana_001",
        brief_content=brief_content,
        brief_date="2026-09-19",
        generated_by="fallback",
        language="en",
        db=db_session
    )

    resp = client.post("/api/v1/briefs/m_kirana_001/send-whatsapp", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert data["merchant_id"] == "m_kirana_001"
    assert "🌅" in data["message_text"]

    # Verify DB flag
    db_session.refresh(brief)
    assert brief.whatsapp_delivered is True


def test_8_brief_idempotency_duplicate_execution(seeded_brief_environment, db_session, client):
    """Test 8: Verify idempotency. Storing twice on same date updates existing record without duplicates."""
    context = collect_merchant_brief_context("m_kirana_001", db=db_session)
    brief_1 = generate_deterministic_fallback_brief(context, language="en")

    # Store first time
    rec1 = store_business_brief(
        merchant_id="m_kirana_001",
        brief_content=brief_1,
        brief_date="2026-09-19",
        generated_by="gemini",
        language="en",
        db=db_session
    )

    # Store second time with updated summary
    brief_2 = dict(brief_1)
    brief_2["summary"] = "Updated idempotent morning summary."
    rec2 = store_business_brief(
        merchant_id="m_kirana_001",
        brief_content=brief_2,
        brief_date="2026-09-19",
        generated_by="fallback",
        language="en",
        db=db_session
    )

    # Must be same row ID
    assert rec1.id == rec2.id
    assert rec2.summary == "Updated idempotent morning summary."

    # Verify count in DB is exactly 1 for this date
    count = db_session.query(BusinessBrief).filter_by(merchant_id="m_kirana_001", brief_date="2026-09-19").count()
    assert count == 1


def test_api_endpoints_integration(seeded_brief_environment, client):
    """Test FastAPI REST endpoints for active merchants, context, generate, store, and latest."""
    # 1. GET /briefs/merchants
    resp = client.get("/api/v1/briefs/merchants")
    assert resp.status_code == 200
    merchants = resp.json()
    assert len(merchants) >= 2

    # 2. GET /briefs/{merchant_id}/context
    resp = client.get("/api/v1/briefs/m_kirana_001/context")
    assert resp.status_code == 200
    ctx = resp.json()
    assert ctx["merchant"]["shop_name"] == "Ravi General Store"

    # 3. POST /briefs/generate
    resp = client.post("/api/v1/briefs/generate", json={"merchant_id": "m_kirana_001", "force_refresh": True})
    assert resp.status_code == 200
    brief = resp.json()
    assert brief["merchant_id"] == "m_kirana_001"
    assert "headline" in brief

    # 4. GET /briefs/{merchant_id}/latest
    resp = client.get("/api/v1/briefs/m_kirana_001/latest")
    assert resp.status_code == 200
    latest = resp.json()
    assert latest["merchant_id"] == "m_kirana_001"
