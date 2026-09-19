import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from app.models import (
    Merchant, MerchantCategory, Product, Inventory,
    Customer, Transaction, PaymentMethod, BusinessEvent,
    EventType, EventSeverity
)
from app.models.base import utc_now, generate_uuid
from app.intelligence import (
    analyze_merchant_sales,
    analyze_product_demand,
    detect_sales_anomalies,
    detect_product_anomalies,
    forecast_product_demand,
    predict_product_stockout,
    predict_merchant_stockouts,
    analyze_merchant_customers,
    get_single_customer_intelligence,
    detect_merchant_opportunities,
    train_anomaly_model,
    load_anomaly_model,
    train_demand_model,
    load_demand_model,
    analyze_business_event
)


@pytest.fixture(autouse=True)
def seed_ml_test_data(db_session):
    now = utc_now()
    m = Merchant(id="m_ml_001", name="Ramesh Kirana", shop_name="Ramesh Kirana Store", category=MerchantCategory.KIRANA, location="Bengaluru", phone="9876543210")
    p1 = Product(id="p_ml_001", merchant_id="m_ml_001", name="Cold Drinks 500ml", category="Beverages", price=40.00, cost_price=32.00)
    p2 = Product(id="p_ml_002", merchant_id="m_ml_001", name="Potato Chips 50g", category="Snacks", price=20.00, cost_price=15.00)
    c1 = Customer(id="c_ml_001", merchant_id="m_ml_001", name="Amit Verma", phone="9876543211", total_spend=3500.00, purchase_count=12, last_purchase_at=now - timedelta(days=2))
    c2 = Customer(id="c_ml_002", merchant_id="m_ml_001", name="Suresh Gupta", phone="9876543212", total_spend=1500.00, purchase_count=4, last_purchase_at=now - timedelta(days=25)) # AT_RISK
    inv1 = Inventory(id="inv_ml_001", product_id="p_ml_001", current_stock=18, reorder_level=10)
    inv2 = Inventory(id="inv_ml_002", product_id="p_ml_002", current_stock=50, reorder_level=15)

    db_session.add_all([m, p1, p2, c1, c2, inv1, inv2])

    # Seed 60 historical transactions across 10 days
    tx_list = []
    for day in range(10):
        for hour in [10, 14, 18, 20]:
            t_stamp = now - timedelta(days=day, hours=(24 - hour))
            tx1 = Transaction(
                id=generate_uuid(),
                merchant_id="m_ml_001",
                product_id="p_ml_001",
                customer_id="c_ml_001",
                quantity=3,
                unit_price=Decimal("40.00"),
                amount=Decimal("120.00"),
                payment_method=PaymentMethod.UPI,
                transaction_timestamp=t_stamp
            )
            tx2 = Transaction(
                id=generate_uuid(),
                merchant_id="m_ml_001",
                product_id="p_ml_002",
                customer_id="c_ml_001",
                quantity=2,
                unit_price=Decimal("20.00"),
                amount=Decimal("40.00"),
                payment_method=PaymentMethod.UPI,
                transaction_timestamp=t_stamp
            )
            tx_list.extend([tx1, tx2])

    db_session.add_all(tx_list)
    db_session.commit()


def test_sales_analyzer_merchant(db_session):
    res = analyze_merchant_sales(db_session, "m_ml_001", days=30)
    assert res["merchant_id"] == "m_ml_001"
    assert res["sales"]["last_7_days"] > 0
    assert res["sales"]["transaction_count"] >= 60
    assert len(res["top_products"]) >= 2
    assert "sales_by_hour" in res
    assert "sales_by_day" in res
    assert "peak_sales_period" in res


def test_sales_analyzer_product(db_session):
    res = analyze_product_demand(db_session, "m_ml_001", "p_ml_001", days=30)
    assert res["product_id"] == "p_ml_001"
    assert res["units_sold"] > 0
    assert res["revenue"] > 0


def test_anomaly_detection_nominal(db_session):
    res = detect_sales_anomalies(db_session, "m_ml_001", days=30)
    assert res["merchant_id"] == "m_ml_001"
    assert "anomaly_detected" in res
    assert "severity" in res


def test_anomaly_detection_demand_spike(db_session):
    # Insert surge of 50 units in the latest hour
    now = utc_now()
    surge_tx = Transaction(
        id=generate_uuid(),
        merchant_id="m_ml_001",
        product_id="p_ml_001",
        quantity=50,
        unit_price=Decimal("40.00"),
        amount=Decimal("2000.00"),
        payment_method=PaymentMethod.UPI,
        transaction_timestamp=now
    )
    db_session.add(surge_tx)
    db_session.commit()

    res = detect_sales_anomalies(db_session, "m_ml_001", days=30)
    assert res["anomaly_detected"] is True
    assert res["anomaly_type"] in ["DEMAND_SPIKE", "UNUSUAL_VOLUME"]
    assert res["severity"] in ["HIGH", "CRITICAL"]


def test_demand_forecasting(db_session):
    res = forecast_product_demand(db_session, "m_ml_001", "p_ml_001", days=30)
    assert res["product_id"] == "p_ml_001"
    assert res["forecast_next_hour"] >= 0
    assert res["forecast_next_day"] >= res["forecast_next_hour"]
    assert "evaluation_metrics" in res


def test_stockout_prediction(db_session):
    res = predict_product_stockout(db_session, "m_ml_001", "p_ml_001")
    assert res["product_id"] == "p_ml_001"
    assert res["current_stock"] == 18
    assert res["estimated_hours_to_stockout"] > 0
    assert res["stockout_risk"] in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]


def test_customer_intelligence(db_session):
    res = analyze_merchant_customers(db_session, "m_ml_001")
    assert res["total_customers"] == 2
    assert res["segments_summary"]["HIGH_VALUE"] >= 1
    assert res["segments_summary"]["AT_RISK"] >= 1


def test_opportunity_detection(db_session):
    res = detect_merchant_opportunities(db_session, "m_ml_001")
    assert res["merchant_id"] == "m_ml_001"
    assert res["total_opportunities"] > 0
    types = [o["type"] for o in res["opportunities"]]
    assert any(t in ["DEMAND_GROWTH", "RESTOCK", "CUSTOMER_WINBACK", "CROSS_SELL"] for t in types)


def test_business_event_enrichment(db_session):
    ev = BusinessEvent(
        id="evt_test_ml_001",
        merchant_id="m_ml_001",
        event_type=EventType.DEMAND_SPIKE,
        severity=EventSeverity.HIGH,
        payload={"product_id": "p_ml_001", "product_name": "Cold Drinks 500ml", "unit_price": 40.0},
        detected_at=utc_now()
    )
    db_session.add(ev)
    db_session.commit()

    analysis = analyze_business_event(db_session, "evt_test_ml_001")
    assert analysis["event_id"] == "evt_test_ml_001"
    assert "anomaly" in analysis["analysis"]
    assert "forecast" in analysis["analysis"]
    assert "inventory" in analysis["analysis"]


def test_model_manager_train_and_load(db_session):
    train_res = train_anomaly_model(db_session, "m_ml_001", days=30, save=True)
    assert train_res["status"] == "trained_and_saved"

    loaded_model = load_anomaly_model("m_ml_001")
    assert loaded_model is not None


def test_api_endpoints(client):
    # 1. Sales API
    r1 = client.get("/api/v1/intelligence/sales/m_ml_001")
    assert r1.status_code == 200
    assert "sales" in r1.json()

    # 2. Anomaly API
    r2 = client.post("/api/v1/intelligence/anomaly-detection", json={"merchant_id": "m_ml_001"})
    assert r2.status_code == 200
    assert "anomaly_detected" in r2.json()

    # 3. Forecast API
    r3 = client.post("/api/v1/intelligence/demand-forecast", json={"merchant_id": "m_ml_001", "product_id": "p_ml_001"})
    assert r3.status_code == 200
    assert "forecast_next_hour" in r3.json()

    # 4. Stockout API
    r4 = client.post("/api/v1/intelligence/stockout-prediction", json={"merchant_id": "m_ml_001", "product_id": "p_ml_001"})
    assert r4.status_code == 200
    assert "estimated_hours_to_stockout" in r4.json()

    # 5. Customer API
    r5 = client.get("/api/v1/intelligence/customers/m_ml_001")
    assert r5.status_code == 200
    assert "segments_summary" in r5.json()

    # 6. Opportunity API
    r6 = client.get("/api/v1/intelligence/opportunities/m_ml_001")
    assert r6.status_code == 200
    assert "opportunities" in r6.json()
