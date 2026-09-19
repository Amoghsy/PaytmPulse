import pytest
from app.models.merchant import Merchant, MerchantCategory
from app.models.product import Product
from app.models.inventory import Inventory
from app.models.action import Action, ActionType, ActionStatus


@pytest.fixture
def api_exec_merchant(db_session):
    m = Merchant(
        name="Sunil Shetty",
        shop_name="Sunil Stores",
        category=MerchantCategory.KIRANA,
        location="Rajajinagar, Bengaluru",
        language="Kannada",
        phone="919876540004"
    )
    db_session.add(m)
    db_session.commit()
    db_session.refresh(m)

    p = Product(
        merchant_id=m.id,
        name="Wheat Flour 5kg",
        category="Flours",
        price=220.0,
        cost_price=175.0
    )
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)

    inv = Inventory(
        product_id=p.id,
        current_stock=8,
        reorder_level=12,
        maximum_stock=50
    )
    db_session.add(inv)
    db_session.commit()

    act = Action(
        merchant_id=m.id,
        action_type=ActionType.REORDER,
        status=ActionStatus.APPROVED,
        parameters={"product_id": p.id, "quantity": 16}
    )
    db_session.add(act)
    db_session.commit()
    db_session.refresh(act)

    return m, p, act


def test_api_execute_action_endpoint(client, api_exec_merchant):
    merchant, product, action = api_exec_merchant
    response = client.post(f"/execution/{action.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "EXECUTED"
    assert data["action_id"] == action.id
    assert data["details"]["stock_after"] == 24


def test_api_execute_unapproved_action_endpoint(client, db_session, api_exec_merchant):
    merchant, product, _ = api_exec_merchant
    unapproved_act = Action(
        merchant_id=merchant.id,
        action_type=ActionType.REORDER,
        status=ActionStatus.PENDING,
        parameters={"product_id": product.id, "quantity": 10}
    )
    db_session.add(unapproved_act)
    db_session.commit()
    db_session.refresh(unapproved_act)

    response = client.post(f"/execution/{unapproved_act.id}")
    assert response.status_code == 400


def test_api_get_action_status_endpoint(client, api_exec_merchant):
    _, _, action = api_exec_merchant
    response = client.get(f"/execution/{action.id}/status")
    assert response.status_code == 200
    data = response.json()
    assert data["action_id"] == action.id
    assert data["status"] == "APPROVED"


def test_api_get_merchant_history_endpoint(client, api_exec_merchant):
    merchant, _, action = api_exec_merchant
    # Execute first
    client.post(f"/execution/{action.id}")

    response = client.get(f"/execution/merchant/{merchant.id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["status"] == "EXECUTED"
