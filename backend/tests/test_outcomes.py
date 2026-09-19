import pytest
from datetime import datetime, timezone, timedelta
from app.models.merchant import Merchant, MerchantCategory
from app.models.product import Product
from app.models.inventory import Inventory
from app.models.customer import Customer
from app.models.transaction import Transaction
from app.models.business_event import BusinessEvent, EventType, EventSeverity
from app.models.recommendation import Recommendation, RecommendationType
from app.models.action import Action, ActionType, ActionStatus
from app.models.outcome import Outcome
from app.outcomes.service import OutcomeService
from app.outcomes.schemas import OutcomeType, OutcomeImpact
from app.agent.tools.outcome_tools import get_action_outcome, get_action_history


def create_mock_merchant_and_catalog(db):
    merchant = Merchant(
        id="m_outcomes_1",
        name="Ramesh Kumar",
        shop_name="Ramesh Kirana Store",
        category=MerchantCategory.KIRANA,
        location="Bengaluru",
        phone="+919876543210"
    )
    db.add(merchant)

    product = Product(
        id="p_cold_drinks",
        merchant_id=merchant.id,
        name="Cold Drink 500ml",
        category="beverages",
        price=40.0,
        cost_price=28.0,
        current_stock=42
    )
    db.add(product)

    inventory = Inventory(
        id="inv_cd_1",
        product_id=product.id,
        current_stock=42,  # restocked from 18 to 42
        reorder_level=20
    )
    db.add(inventory)

    db.commit()
    return merchant, product, inventory



def test_restock_outcome_measurement(db_session):
    merchant, product, inventory = create_mock_merchant_and_catalog(db_session)

    # 1. Create executed restock action
    now = datetime.now(timezone.utc) - timedelta(hours=2)
    action = Action(
        id="act_restock_101",
        merchant_id=merchant.id,
        action_type=ActionType.REORDER,
        parameters={"product_id": product.id, "quantity": 24, "stock_before": 18, "unit_cost": 28.0},
        status=ActionStatus.EXECUTED,
        execution_id="EXEC-RESTOCK-101",
        executed_at=now
    )
    db_session.add(action)
    db_session.commit()

    # 2. Add simulated post-action transactions (25 units sold, exceeding initial stock 18)
    for i in range(5):
        t_time = now + timedelta(minutes=20 * (i + 1))
        tx = Transaction(
            id=f"tx_post_{i}",
            merchant_id=merchant.id,
            product_id=product.id,
            unit_price=40.0,
            amount=200.0,  # 5 units @ 40
            quantity=5,
            payment_method="UPI",
            transaction_timestamp=t_time,
            created_at=t_time
        )
        db_session.add(tx)
    
    # 42 - 25 = 17 remaining stock
    inventory.current_stock = 17
    db_session.commit()


    # 3. Measure outcome
    service = OutcomeService(db_session)
    outcome = service.measure_action_outcome(action.id)

    assert outcome.action_id == action.id
    assert outcome.stockout_prevented is True
    assert outcome.impact == OutcomeImpact.POSITIVE.value
    assert outcome.outcome_type == OutcomeType.STOCKOUT_PREVENTED.value
    assert outcome.sales_after == 1000.0
    assert outcome.revenue_change is not None
    assert outcome.learning_signals is not None


def test_promotion_outcome_measurement(db_session):
    merchant, product, _ = create_mock_merchant_and_catalog(db_session)

    now = datetime.now(timezone.utc) - timedelta(hours=3)
    action = Action(
        id="act_promo_101",
        merchant_id=merchant.id,
        action_type=ActionType.PROMOTION,
        parameters={"product_id": product.id, "discount_percent": 15, "offer_code": "COLD15"},
        status=ActionStatus.EXECUTED,
        execution_id="EXEC-PROMO-101",
        executed_at=now
    )
    db_session.add(action)
    db_session.commit()

    # Simulate transactions
    for i in range(4):
        t_time = now + timedelta(minutes=30 * (i + 1))
        tx = Transaction(
            id=f"tx_promo_{i}",
            merchant_id=merchant.id,
            product_id=product.id,
            unit_price=34.0,
            amount=170.0,
            quantity=5,
            payment_method="UPI",
            transaction_timestamp=t_time,
            created_at=t_time
        )
        db_session.add(tx)
    db_session.commit()

    service = OutcomeService(db_session)
    outcome = service.measure_action_outcome(action.id)

    assert outcome.action_id == action.id
    assert outcome.impact == OutcomeImpact.POSITIVE.value
    assert outcome.sales_after == 680.0
    assert outcome.offer_conversion is not None


def test_customer_winback_outcome(db_session):
    merchant, product, _ = create_mock_merchant_and_catalog(db_session)

    c1 = Customer(id="cust_wb_1", merchant_id=merchant.id, name="Anil", phone="+919999900001")
    c2 = Customer(id="cust_wb_2", merchant_id=merchant.id, name="Suresh", phone="+919999900002")
    c3 = Customer(id="cust_wb_3", merchant_id=merchant.id, name="Priya", phone="+919999900003")
    db_session.add_all([c1, c2, c3])
    db_session.commit()

    now = datetime.now(timezone.utc) - timedelta(hours=5)
    action = Action(
        id="act_winback_101",
        merchant_id=merchant.id,
        action_type=ActionType.WINBACK,
        parameters={"customer_ids": ["cust_wb_1", "cust_wb_2", "cust_wb_3"], "discount_percent": 20},
        status=ActionStatus.EXECUTED,
        execution_id="EXEC-WB-101",
        executed_at=now
    )
    db_session.add(action)
    db_session.commit()

    # 2 customers return
    t1 = now + timedelta(hours=1)
    t2 = now + timedelta(hours=2)
    tx1 = Transaction(id="tx_wb_1", merchant_id=merchant.id, customer_id="cust_wb_1", product_id=product.id, unit_price=40.0, amount=200.0, quantity=5, transaction_timestamp=t1, created_at=t1)
    tx2 = Transaction(id="tx_wb_2", merchant_id=merchant.id, customer_id="cust_wb_2", product_id=product.id, unit_price=40.0, amount=160.0, quantity=4, transaction_timestamp=t2, created_at=t2)
    db_session.add_all([tx1, tx2])
    db_session.commit()

    service = OutcomeService(db_session)
    outcome = service.measure_action_outcome(action.id)

    assert outcome.customers_recovered == 2
    assert outcome.offer_conversion == 0.67
    assert outcome.impact == OutcomeImpact.POSITIVE.value


def test_insufficient_data_handling(db_session):
    merchant, product, _ = create_mock_merchant_and_catalog(db_session)

    # Executed just now with 0 post-action transactions
    now = datetime.now(timezone.utc)
    action = Action(
        id="act_new_101",
        merchant_id=merchant.id,
        action_type=ActionType.REORDER,
        parameters={"product_id": product.id, "quantity": 10},
        status=ActionStatus.EXECUTED,
        execution_id="EXEC-NEW-101",
        executed_at=now
    )
    db_session.add(action)
    db_session.commit()

    service = OutcomeService(db_session)
    outcome = service.measure_action_outcome(action.id)

    assert outcome.impact == OutcomeImpact.INSUFFICIENT_DATA.value
    assert outcome.status == "INSUFFICIENT_DATA"
    assert outcome.stockout_prevented is False


def test_duplicate_measurement_prevention(db_session):
    merchant, product, _ = create_mock_merchant_and_catalog(db_session)

    now = datetime.now(timezone.utc) - timedelta(hours=1)
    action = Action(
        id="act_dup_101",
        merchant_id=merchant.id,
        action_type=ActionType.PROMOTION,
        parameters={"product_id": product.id},
        status=ActionStatus.EXECUTED,
        execution_id="EXEC-DUP-101",
        executed_at=now
    )
    db_session.add(action)
    db_session.commit()

    t_dup = now + timedelta(minutes=10)
    tx = Transaction(id="tx_dup_1", merchant_id=merchant.id, product_id=product.id, unit_price=40.0, amount=120.0, quantity=3, transaction_timestamp=t_dup, created_at=t_dup)
    db_session.add(tx)
    db_session.commit()

    service = OutcomeService(db_session)
    first_res = service.measure_action_outcome(action.id)
    second_res = service.measure_action_outcome(action.id)

    assert first_res.id == second_res.id
    count = db_session.query(Outcome).filter(Outcome.action_id == action.id).count()
    assert count == 1


def test_outcome_api_endpoints(client, db_session):
    merchant, product, _ = create_mock_merchant_and_catalog(db_session)

    now = datetime.now(timezone.utc) - timedelta(hours=1)
    action = Action(
        id="act_api_101",
        merchant_id=merchant.id,
        action_type=ActionType.REORDER,
        parameters={"product_id": product.id, "quantity": 20},
        status=ActionStatus.EXECUTED,
        execution_id="EXEC-API-101",
        executed_at=now
    )
    db_session.add(action)
    db_session.commit()

    # 1. Trigger Measurement via API
    resp = client.post(f"/outcomes/measure/{action.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["action_id"] == action.id
    outcome_id = data["id"]

    # 2. Get by Outcome ID
    resp2 = client.get(f"/outcomes/{outcome_id}")
    assert resp2.status_code == 200
    assert resp2.json()["id"] == outcome_id

    # 3. Get by Action ID
    resp3 = client.get(f"/outcomes/action/{action.id}")
    assert resp3.status_code == 200
    assert resp3.json()["action_id"] == action.id

    # 4. Get Merchant Summary
    resp4 = client.get(f"/outcomes/merchant/{merchant.id}/summary")
    assert resp4.status_code == 200
    sum_data = resp4.json()
    assert sum_data["merchant_id"] == merchant.id
    assert sum_data["actions_executed"] >= 1
    assert sum_data["outcomes_measured"] >= 1


def test_closed_loop_traceability(client, db_session):
    merchant, product, _ = create_mock_merchant_and_catalog(db_session)

    # Full lineage: Event -> Recommendation -> Action -> Execution -> Outcome
    event = BusinessEvent(
        id="evt_trace_1",
        merchant_id=merchant.id,
        event_type=EventType.STOCKOUT_RISK,
        severity=EventSeverity.CRITICAL,
        payload={"product_id": product.id, "current_stock": 18},
        detected_at=datetime.now(timezone.utc) - timedelta(hours=2)
    )
    db_session.add(event)
    db_session.flush()

    rec = Recommendation(
        id="rec_trace_1",
        event_id=event.id,
        merchant_id=merchant.id,
        type=RecommendationType.STOCK_REORDER,
        title="Restock Cold Drinks",
        reason="Elevated beverage demand detected during hot afternoon.",
        urgency="HIGH",
        expected_impact="High revenue protection",
        confidence=0.92
    )

    db_session.add(rec)
    db_session.flush()

    action = Action(
        id="act_trace_1",
        recommendation_id=rec.id,
        merchant_id=merchant.id,
        action_type=ActionType.REORDER,
        parameters={"product_id": product.id, "quantity": 24},
        status=ActionStatus.EXECUTED,
        execution_id="EXEC-TRACE-1",
        executed_at=datetime.now(timezone.utc) - timedelta(hours=1)
    )
    db_session.add(action)
    db_session.commit()

    # Add transaction & measure
    t_trace = datetime.now(timezone.utc)
    tx = Transaction(id="tx_trace_1", merchant_id=merchant.id, product_id=product.id, unit_price=40.0, amount=400.0, quantity=10, transaction_timestamp=t_trace, created_at=t_trace)
    db_session.add(tx)
    db_session.commit()


    service = OutcomeService(db_session)
    service.measure_action_outcome(action.id)

    # Trace endpoint
    resp = client.get(f"/outcomes/trace/{action.id}")
    assert resp.status_code == 200
    trace = resp.json()
    assert trace["action_id"] == action.id
    assert trace["event_id"] == event.id
    assert trace["recommendation_id"] == rec.id
    assert trace["execution_id"] == "EXEC-TRACE-1"
    assert trace["outcome_id"] != "UNMEASURED"
    assert trace["action_details"] is not None
    assert trace["recommendation_details"] is not None
    assert trace["event_details"] is not None


def test_stockout_occurred_negative_outcome(db_session):
    """Test scenario where restocking was insufficient and stockout occurred."""
    merchant, product, inventory = create_mock_merchant_and_catalog(db_session)

    now = datetime.now(timezone.utc) - timedelta(hours=2)
    action = Action(
        id="act_restock_fail_1",
        merchant_id=merchant.id,
        action_type=ActionType.REORDER,
        parameters={"product_id": product.id, "quantity": 5, "stock_before": 2},
        status=ActionStatus.EXECUTED,
        execution_id="EXEC-RESTOCK-FAIL-1",
        executed_at=now
    )
    db_session.add(action)
    db_session.commit()

    # Inventory depleted to 0
    inventory.current_stock = 0
    t_post = now + timedelta(minutes=30)
    tx = Transaction(
        id="tx_deplete_1",
        merchant_id=merchant.id,
        product_id=product.id,
        unit_price=40.0,
        amount=280.0,
        quantity=7,
        payment_method="UPI",
        transaction_timestamp=t_post,
        created_at=t_post
    )
    db_session.add(tx)
    db_session.commit()

    service = OutcomeService(db_session)
    outcome = service.measure_action_outcome(action.id)

    assert outcome.action_id == action.id
    assert outcome.stockout_prevented is False
    assert outcome.impact == OutcomeImpact.NEGATIVE.value
    assert outcome.outcome_type == OutcomeType.STOCKOUT_OCCURRED.value


def test_negative_promotion_impact(db_session):
    """Test scenario where a promotion generates negative net revenue impact vs baseline."""
    merchant, product, _ = create_mock_merchant_and_catalog(db_session)

    # 1. Historical baseline: 10 transactions @ 40 = 400
    lookback = datetime.now(timezone.utc) - timedelta(hours=24)
    for i in range(10):
        t_base = lookback + timedelta(hours=i)
        tx_b = Transaction(
            id=f"tx_base_neg_{i}",
            merchant_id=merchant.id,
            product_id=product.id,
            unit_price=40.0,
            amount=400.0,
            quantity=10,
            payment_method="UPI",
            transaction_timestamp=t_base,
            created_at=t_base
        )
        db_session.add(tx_b)
    db_session.commit()

    # 2. Executed promotion
    now = datetime.now(timezone.utc) - timedelta(hours=2)
    action = Action(
        id="act_promo_neg_1",
        merchant_id=merchant.id,
        action_type=ActionType.PROMOTION,
        parameters={"product_id": product.id, "discount_percent": 50},
        status=ActionStatus.EXECUTED,
        execution_id="EXEC-PROMO-NEG-1",
        executed_at=now
    )
    db_session.add(action)
    db_session.commit()

    # 3. Post-action sales: only 1 transaction for 20 (severe drop)
    t_post = now + timedelta(minutes=30)
    tx_p = Transaction(
        id="tx_post_neg_1",
        merchant_id=merchant.id,
        product_id=product.id,
        unit_price=20.0,
        amount=20.0,
        quantity=1,
        payment_method="UPI",
        transaction_timestamp=t_post,
        created_at=t_post
    )
    db_session.add(tx_p)
    db_session.commit()

    service = OutcomeService(db_session)
    outcome = service.measure_action_outcome(action.id)

    assert outcome.impact == OutcomeImpact.NEGATIVE.value
    assert outcome.outcome_type == OutcomeType.NEGATIVE_IMPACT.value
    assert outcome.revenue_change < 0


def test_whatsapp_outcome_notification_formatter(db_session):
    """Test formatting of WhatsApp outcome follow-up message."""
    merchant, product, _ = create_mock_merchant_and_catalog(db_session)

    action = Action(
        id="act_wa_fmt_1",
        merchant_id=merchant.id,
        action_type=ActionType.REORDER,
        parameters={"product_id": product.id, "product_name": "Cold Drink 500ml", "quantity": 24},
        status=ActionStatus.EXECUTED,
        executed_at=datetime.now(timezone.utc) - timedelta(hours=1)
    )
    db_session.add(action)
    db_session.commit()

    # Add transaction
    t_wa = datetime.now(timezone.utc)
    tx = Transaction(
        id="tx_wa_1",
        merchant_id=merchant.id,
        product_id=product.id,
        unit_price=40.0,
        amount=600.0,
        quantity=15,
        payment_method="UPI",
        transaction_timestamp=t_wa,
        created_at=t_wa
    )
    db_session.add(tx)
    db_session.commit()

    service = OutcomeService(db_session)
    service.measure_action_outcome(action.id)
    outcome = db_session.query(Outcome).filter(Outcome.action_id == action.id).first()

    wa_text = service.format_whatsapp_followup(outcome)
    assert "Action Result" in wa_text
    assert "Cold Drink 500ml" in wa_text
    assert "Positive" in wa_text


def test_agent_outcome_tools(db_session):
    merchant, product, _ = create_mock_merchant_and_catalog(db_session)

    action = Action(
        id="act_tool_1",
        merchant_id=merchant.id,
        action_type=ActionType.REORDER,
        parameters={"product_id": product.id, "quantity": 24},
        status=ActionStatus.EXECUTED,
        executed_at=datetime.now(timezone.utc) - timedelta(hours=1)
    )
    db_session.add(action)
    db_session.commit()

    # Query before measurement
    res_unmeasured = get_action_outcome(action.id, db=db_session)
    assert "UNMEASURED_OR_NOT_FOUND" in res_unmeasured

    # Measure
    service = OutcomeService(db_session)
    service.measure_action_outcome(action.id)

    # Query after measurement
    res_measured = get_action_outcome(action.id, db=db_session)
    assert action.id in res_measured

    # Query merchant history
    history = get_action_history(merchant.id, db=db_session)
    assert merchant.id in history


