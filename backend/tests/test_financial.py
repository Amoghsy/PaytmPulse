import pytest
from datetime import datetime, timezone, timedelta
from app.models.merchant import Merchant, MerchantCategory
from app.models.product import Product
from app.models.inventory import Inventory
from app.models.customer import Customer
from app.models.action import Action, ActionType, ActionStatus
from app.models.business_event import BusinessEvent, EventType, EventSeverity
from app.models.financial_product import FinancialProduct
from app.models.financial_recommendation import FinancialRecommendation, FinancialRecommendationStatus
from app.financial.recommendation_service import FinancialRecommendationService
from app.financial.rules import FinancialRulesEngine
from app.financial.schemas import FinancialNeedType
from app.agent.tools.financial_tools import get_financial_opportunities
from app.agent.runner import AgentRunner


def create_mock_kirana_merchant(db):
    merchant = Merchant(
        id="m_fin_kirana_1",
        name="Ramesh Kumar",
        shop_name="Ramesh Kirana Store",
        category=MerchantCategory.KIRANA,
        location="Bengaluru",
        phone="+919876543299"
    )
    db.add(merchant)

    product = Product(
        id="p_fin_cold_drink",
        merchant_id=merchant.id,
        name="Cold Drink 500ml",
        category="beverages",
        price=40.0,
        cost_price=28.0,
        current_stock=18
    )
    db.add(product)

    inventory = Inventory(
        id="inv_fin_1",
        product_id=product.id,
        current_stock=18,
        reorder_level=20
    )
    db.add(inventory)

    db.commit()
    return merchant, product, inventory


def test_catalog_seeding_and_retrieval(db_session):
    service = FinancialRecommendationService(db_session)
    catalog = service.get_catalog()

    assert len(catalog) == 4
    codes = [p.product_code for p in catalog]
    assert "WORKING_CAPITAL_SIM" in codes
    assert "INVENTORY_FINANCING_SIM" in codes
    assert "BUSINESS_EXPANSION_SIM" in codes
    assert "CASH_FLOW_SUPPORT_SIM" in codes

    for prod in catalog:
        assert prod.simulated is True
        assert prod.active is True


def test_working_capital_need_detection(db_session):
    merchant, product, _ = create_mock_kirana_merchant(db_session)

    # 1. Create demand surge event (48% surge)
    event = BusinessEvent(
        id="evt_fin_surge",
        merchant_id=merchant.id,
        event_type=EventType.DEMAND_SPIKE,
        severity=EventSeverity.HIGH,
        payload={"product_id": product.id, "spike_percentage": 48.0},
        detected_at=datetime.now(timezone.utc)
    )
    db_session.add(event)

    # 2. Add 2 recent restock actions (frequent restocking)
    now = datetime.now(timezone.utc)
    act1 = Action(
        id="act_fin_restock_1",
        merchant_id=merchant.id,
        action_type=ActionType.REORDER,
        parameters={"product_id": product.id, "quantity": 24, "unit_cost": 28.0},
        status=ActionStatus.EXECUTED,
        created_at=now - timedelta(days=3)
    )
    act2 = Action(
        id="act_fin_restock_2",
        merchant_id=merchant.id,
        action_type=ActionType.REORDER,
        parameters={"product_id": product.id, "quantity": 24, "unit_cost": 28.0},
        status=ActionStatus.EXECUTED,
        created_at=now - timedelta(days=1)
    )
    db_session.add_all([act1, act2])
    db_session.commit()

    service = FinancialRecommendationService(db_session)
    opp = service.analyze_and_recommend(merchant.id)

    assert opp.opportunity_detected is True
    assert opp.need_result.need_type == FinancialNeedType.WORKING_CAPITAL
    assert opp.recommendation is not None
    assert opp.recommendation.need_type == "WORKING_CAPITAL"
    assert opp.recommendation.simulated_amount > 0
    assert opp.matched_product.product_code == "WORKING_CAPITAL_SIM"
    assert "simulated" in opp.recommendation.disclaimer.lower()


def test_inventory_financing_rule(db_session):
    metrics = {
        "demand_growth": 0.18,
        "restock_count_last_7_days": 3,
        "recent_restock_spend": 2500.0,
        "average_daily_sales": 2000.0,
        "sales_growth": 0.05,
        "customer_growth": 0.02
    }
    result = FinancialRulesEngine.evaluate("m_test", metrics)

    assert result.need_detected is True
    assert result.need_type == FinancialNeedType.INVENTORY_FINANCING
    assert result.confidence >= 0.70
    assert result.estimated_requirement_amount > 0


def test_business_expansion_rule(db_session):
    metrics = {
        "demand_growth": 0.05,
        "restock_count_last_7_days": 0,
        "recent_restock_spend": 0.0,
        "average_daily_sales": 3000.0,
        "sales_growth": 0.25,      # 25% sustained sales growth
        "customer_growth": 0.18    # 18% new customer expansion
    }
    result = FinancialRulesEngine.evaluate("m_test_growth", metrics)

    assert result.need_detected is True
    assert result.need_type == FinancialNeedType.BUSINESS_EXPANSION
    assert result.confidence >= 0.75
    assert result.estimated_requirement_amount >= 25000.0


def test_cash_flow_support_rule(db_session):
    metrics = {
        "demand_growth": 0.0,
        "restock_count_last_7_days": 1,
        "recent_restock_spend": 1000.0,
        "average_daily_sales": 1200.0,
        "sales_growth": -0.22,     # -22% sales dip
        "customer_growth": 0.0
    }
    result = FinancialRulesEngine.evaluate("m_test_dip", metrics)

    assert result.need_detected is True
    assert result.need_type == FinancialNeedType.CASH_FLOW_SUPPORT
    assert result.confidence >= 0.70


def test_normal_business_steady_state_no_need(db_session):
    metrics = {
        "demand_growth": 0.02,
        "restock_count_last_7_days": 0,
        "recent_restock_spend": 0.0,
        "average_daily_sales": 1000.0,
        "sales_growth": 0.01,
        "customer_growth": 0.01
    }
    result = FinancialRulesEngine.evaluate("m_steady", metrics)

    assert result.need_detected is False
    assert result.need_type is None


def test_recommendation_cooldown(db_session):
    merchant, product, _ = create_mock_kirana_merchant(db_session)

    # Create demand surge
    event = BusinessEvent(
        id="evt_cooldown_surge",
        merchant_id=merchant.id,
        event_type=EventType.DEMAND_SPIKE,
        severity=EventSeverity.HIGH,
        payload={"product_id": product.id, "spike_percentage": 50.0},
        detected_at=datetime.now(timezone.utc)
    )
    db_session.add(event)

    now = datetime.now(timezone.utc)
    for i in range(2):
        act = Action(
            id=f"act_cd_{i}",
            merchant_id=merchant.id,
            action_type=ActionType.REORDER,
            parameters={"product_id": product.id, "quantity": 20},
            status=ActionStatus.EXECUTED,
            created_at=now - timedelta(days=i + 1)
        )
        db_session.add(act)
    db_session.commit()

    service = FinancialRecommendationService(db_session)
    first_opp = service.analyze_and_recommend(merchant.id)
    assert first_opp.opportunity_detected is True

    # Immediate second call should be caught by cooldown without creating new DB row
    second_opp = service.analyze_and_recommend(merchant.id, bypass_cooldown=False)
    assert second_opp.opportunity_detected is True
    assert second_opp.recommendation.id == first_opp.recommendation.id

    rec_count = db_session.query(FinancialRecommendation).filter(
        FinancialRecommendation.merchant_id == merchant.id
    ).count()
    assert rec_count == 1


def test_merchant_interest_and_decline_lifecycle(db_session):
    merchant, _, _ = create_mock_kirana_merchant(db_session)
    service = FinancialRecommendationService(db_session)
    service.seed_catalog_if_empty()

    prod = db_session.query(FinancialProduct).first()

    rec = FinancialRecommendation(
        id="rec_fin_lifecycle_1",
        merchant_id=merchant.id,
        product_id=prod.id,
        need_type="WORKING_CAPITAL",
        title="Working Capital Support",
        reason="Test reason",
        supporting_signals=["Signal 1", "Signal 2"],
        confidence=0.85,
        simulated_amount=25000.0,
        duration_days=90,
        status=FinancialRecommendationStatus.RECOMMENDED
    )
    db_session.add(rec)
    db_session.commit()

    # 1. Express Interest
    interest_res = service.record_merchant_interest(rec.id, notes="Interested in inventory support")
    assert interest_res.status == "INTERESTED"

    # 2. Decline
    decline_res = service.record_merchant_decline(rec.id, reason="Not required right now")
    assert decline_res.status == "DECLINED"


def test_financial_api_endpoints(client, db_session):
    merchant, product, _ = create_mock_kirana_merchant(db_session)

    # 1. Get Products
    resp1 = client.get("/financial/products")
    assert resp1.status_code == 200
    products = resp1.json()
    assert len(products) >= 4

    # 2. Add surge signals
    event = BusinessEvent(
        id="evt_api_surge",
        merchant_id=merchant.id,
        event_type=EventType.DEMAND_SPIKE,
        severity=EventSeverity.HIGH,
        payload={"product_id": product.id, "spike_percentage": 40.0},
        detected_at=datetime.now(timezone.utc)
    )
    db_session.add(event)
    for i in range(2):
        act = Action(
            id=f"act_api_restock_{i}",
            merchant_id=merchant.id,
            action_type=ActionType.REORDER,
            parameters={"product_id": product.id, "quantity": 20},
            status=ActionStatus.EXECUTED,
            created_at=datetime.now(timezone.utc) - timedelta(days=i + 1)
        )
        db_session.add(act)
    db_session.commit()

    # 3. Analyze & Recommend API
    resp2 = client.post(f"/financial/analyze/{merchant.id}")
    assert resp2.status_code == 200
    data = resp2.json()
    assert data["opportunity_detected"] is True
    rec_id = data["recommendation"]["id"]

    # 4. Get Details
    resp3 = client.get(f"/financial/recommendation/{rec_id}")
    assert resp3.status_code == 200
    assert resp3.json()["id"] == rec_id

    # 5. Express Interest API
    resp4 = client.post(f"/financial/recommendations/{rec_id}/interest", json={"notes": "Demo interest"})
    assert resp4.status_code == 200
    assert resp4.json()["status"] == "INTERESTED"

    # 6. Decline API
    resp5 = client.post(f"/financial/recommendations/{rec_id}/decline", json={"reason": "Not needed"})
    assert resp5.status_code == 200
    assert resp5.json()["status"] == "DECLINED"


def test_agent_financial_tool_and_chat(db_session):
    merchant, product, _ = create_mock_kirana_merchant(db_session)
    merchant.language = "English"
    db_session.commit()

    # Set up surge signals
    event = BusinessEvent(
        id="evt_tool_surge",
        merchant_id=merchant.id,
        event_type=EventType.DEMAND_SPIKE,
        severity=EventSeverity.HIGH,
        payload={"product_id": product.id, "spike_percentage": 50.0},
        detected_at=datetime.now(timezone.utc)
    )
    db_session.add(event)
    for i in range(2):
        act = Action(
            id=f"act_tool_restock_{i}",
            merchant_id=merchant.id,
            action_type=ActionType.REORDER,
            parameters={"product_id": product.id, "quantity": 20},
            status=ActionStatus.EXECUTED,
            created_at=datetime.now(timezone.utc) - timedelta(days=i + 1)
        )
        db_session.add(act)
    db_session.commit()

    # 1. ADK Agent Tool call
    tool_output = get_financial_opportunities(merchant.id, db=db_session)
    assert "opportunity_detected" in tool_output
    assert "simulated" in tool_output.lower()

    # 2. Conversational Agent chat
    runner = AgentRunner(db_session)
    chat_resp = runner.run_chat(merchant.id, "Do you have any loan or working capital options for my store?")
    assert chat_resp.merchant_id == merchant.id
    assert "simulated" in chat_resp.response.lower()
    assert "opportunity" in chat_resp.response.lower() or "working capital" in chat_resp.response.lower()
