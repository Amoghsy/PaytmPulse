import pytest
from app.models.merchant import Merchant, MerchantCategory
from app.models.product import Product
from app.models.inventory import Inventory
from app.models.action import Action, ActionType, ActionStatus
from app.execution.engine import ExecutionEngine
from app.execution.exceptions import ActionNotApprovedError, ActionRetryExhaustedError


@pytest.fixture
def eng_merchant(db_session):
    m = Merchant(
        name="Deepak Varma",
        shop_name="Varma Traders",
        category=MerchantCategory.KIRANA,
        location="Basavanagudi, Bengaluru",
        language="Kannada",
        phone="919876540003"
    )
    db_session.add(m)
    db_session.commit()
    db_session.refresh(m)
    return m


@pytest.fixture
def eng_product(db_session, eng_merchant):
    p = Product(
        merchant_id=eng_merchant.id,
        name="Basmati Rice 10kg",
        category="Grains",
        price=700.0,
        cost_price=540.0
    )
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)

    inv = Inventory(
        product_id=p.id,
        current_stock=10,
        reorder_level=15,
        maximum_stock=50
    )
    db_session.add(inv)
    db_session.commit()
    return p


def test_execution_engine_full_flow(db_session, eng_merchant, eng_product):
    engine = ExecutionEngine(db_session)
    action = Action(
        merchant_id=eng_merchant.id,
        action_type=ActionType.REORDER,
        status=ActionStatus.APPROVED,
        parameters={"product_id": eng_product.id, "quantity": 15}
    )
    db_session.add(action)
    db_session.commit()

    resp = engine.execute_action(action.id)
    assert resp.status == "EXECUTED"
    assert resp.execution_id.startswith("exec_")
    assert resp.details["stock_after"] == 25

    # Verify action model status in DB
    db_session.refresh(action)
    assert action.status == ActionStatus.EXECUTED
    assert action.executed_at is not None
    assert action.execution_id == resp.execution_id


def test_execution_engine_idempotency(db_session, eng_merchant, eng_product):
    engine = ExecutionEngine(db_session)
    action = Action(
        merchant_id=eng_merchant.id,
        action_type=ActionType.REORDER,
        status=ActionStatus.APPROVED,
        parameters={"product_id": eng_product.id, "quantity": 10}
    )
    db_session.add(action)
    db_session.commit()

    # 1. First execution
    resp1 = engine.execute_action(action.id)
    assert resp1.status == "EXECUTED"

    # 2. Duplicate second execution request
    resp2 = engine.execute_action(action.id)
    assert resp2.status == "EXECUTED"
    assert resp2.execution_id == resp1.execution_id

    # Ensure inventory was only incremented ONCE (10 + 10 = 20, NOT 30)
    inv = db_session.query(Inventory).filter(Inventory.product_id == eng_product.id).first()
    assert inv.current_stock == 20


def test_execution_engine_unapproved_rejected(db_session, eng_merchant, eng_product):
    engine = ExecutionEngine(db_session)
    action = Action(
        merchant_id=eng_merchant.id,
        action_type=ActionType.REORDER,
        status=ActionStatus.PENDING,
        parameters={"product_id": eng_product.id, "quantity": 10}
    )
    db_session.add(action)
    db_session.commit()

    with pytest.raises(ActionNotApprovedError):
        engine.execute_action(action.id)


def test_execution_engine_status_and_history(db_session, eng_merchant, eng_product):
    engine = ExecutionEngine(db_session)
    action = Action(
        merchant_id=eng_merchant.id,
        action_type=ActionType.REORDER,
        status=ActionStatus.APPROVED,
        parameters={"product_id": eng_product.id, "quantity": 5}
    )
    db_session.add(action)
    db_session.commit()

    engine.execute_action(action.id)

    status_resp = engine.get_action_status(action.id)
    assert status_resp.status == "EXECUTED"

    history = engine.get_merchant_history(eng_merchant.id)
    assert len(history) >= 1
    assert history[0].action_id == action.id
