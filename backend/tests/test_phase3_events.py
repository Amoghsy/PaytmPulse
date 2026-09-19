import pytest
from datetime import datetime, timezone, timedelta

from app.models import (
    Merchant, MerchantCategory, Product, Inventory,
    Customer, Transaction, PaymentMethod, BusinessEvent,
    EventType, EventSeverity
)


@pytest.fixture(autouse=True)
def setup_test_data(db_session):
    # Seed 1 Merchant, 1 Product, 1 Customer, 1 Inventory record
    m = Merchant(id="m_test_001", name="Test Merchant", shop_name="Test Store", category=MerchantCategory.KIRANA, location="Bengaluru", phone="9876543210")
    p = Product(id="p_test_001", merchant_id="m_test_001", name="Amul Milk 1L", category="Dairy", price=66.00, cost_price=58.00)
    c = Customer(id="c_test_001", merchant_id="m_test_001", name="Rahul Sharma", phone="9876543210")
    inv = Inventory(id="inv_test_001", product_id="p_test_001", current_stock=10, reorder_level=5)

    db_session.add_all([m, p, c, inv])
    db_session.commit()


def test_ingest_transaction_success(client):
    payload = {
        "external_event_id": "evt_test_1001",
        "merchant_id": "m_test_001",
        "product_id": "p_test_001",
        "customer_id": "c_test_001",
        "quantity": 2,
        "unit_price": 66.00,
        "payment_method": "UPI"
    }
    response = client.post("/api/v1/events/transaction", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "success"
    assert data["external_event_id"] == "evt_test_1001"
    assert data["summary"]["amount"] == 132.00
    assert data["summary"]["remaining_stock"] == 8


def test_transaction_idempotency(client):
    payload = {
        "external_event_id": "evt_test_idempotent",
        "merchant_id": "m_test_001",
        "product_id": "p_test_001",
        "quantity": 1,
        "unit_price": 66.00
    }
    # First call
    res1 = client.post("/api/v1/events/transaction", json=payload)
    assert res1.status_code == 201
    assert res1.json()["status"] == "success"

    # Second call with same external_event_id
    res2 = client.post("/api/v1/events/transaction", json=payload)
    assert res2.status_code == 201
    assert res2.json()["status"] == "already_processed"


def test_invalid_merchant_id(client):
    payload = {
        "merchant_id": "non_existent_merchant",
        "product_id": "p_test_001",
        "quantity": 1,
        "unit_price": 50.0
    }
    response = client.post("/api/v1/events/transaction", json=payload)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_stockout_risk_event_trigger(client):
    # Reduce inventory stock by purchasing 6 units (stock 10 -> 4, below reorder 5)
    payload = {
        "merchant_id": "m_test_001",
        "product_id": "p_test_001",
        "quantity": 6,
        "unit_price": 66.00
    }
    response = client.post("/api/v1/events/transaction", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert len(data["detected_events"]) > 0
    stockout_event = next((ev for ev in data["detected_events"] if ev["event_type"] == "STOCKOUT_RISK"), None)
    assert stockout_event is not None
    assert stockout_event["payload"]["available_stock"] == 4


def test_event_cooldown_deduplication(client, db_session):
    # Trigger stockout risk 1
    payload = {
        "merchant_id": "m_test_001",
        "product_id": "p_test_001",
        "quantity": 6,
        "unit_price": 66.00
    }
    client.post("/api/v1/events/transaction", json=payload)

    # Count events before 2nd trigger
    events_count_1 = db_session.query(BusinessEvent).filter(BusinessEvent.event_type == EventType.STOCKOUT_RISK).count()
    assert events_count_1 == 1

    # Trigger stockout risk 2 within 15 mins (stock 4 -> 3)
    payload["quantity"] = 1
    client.post("/api/v1/events/transaction", json=payload)

    # Cooldown should update payload rather than creating 2nd row
    events_count_2 = db_session.query(BusinessEvent).filter(BusinessEvent.event_type == EventType.STOCKOUT_RISK).count()
    assert events_count_2 == 1


def test_batch_transaction_burst(client):
    payloads = [
        {
            "external_event_id": f"evt_burst_{i}",
            "merchant_id": "m_test_001",
            "product_id": "p_test_001",
            "quantity": 1,
            "unit_price": 66.00
        } for i in range(10)
    ]
    response = client.post("/api/v1/events/transaction/batch", json=payloads)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["processed_count"] == 10
