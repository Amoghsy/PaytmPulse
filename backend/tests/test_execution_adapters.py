import pytest
from app.models.merchant import Merchant, MerchantCategory
from app.models.product import Product
from app.models.inventory import Inventory
from app.models.action import Action, ActionType, ActionStatus
from app.models.promotion import Promotion, PromotionStatus
from app.adapters.inventory import InventoryActionAdapter
from app.adapters.promotion import PromotionActionAdapter
from app.adapters.customer import CustomerActionAdapter
from app.adapters.mock_paytm import MockPaytmAdapter
from app.adapters.paytm import PaytmAdapter


@pytest.fixture
def adapt_merchant(db_session):
    m = Merchant(
        name="Manjunath Gowda",
        shop_name="Gowda Super Mart",
        category=MerchantCategory.KIRANA,
        location="Malleshwaram, Bengaluru",
        language="Kannada",
        phone="919876540002"
    )
    db_session.add(m)
    db_session.commit()
    db_session.refresh(m)
    return m


@pytest.fixture
def adapt_product(db_session, adapt_merchant):
    p = Product(
        merchant_id=adapt_merchant.id,
        name="Mineral Water 1L",
        category="Beverages",
        price=20.0,
        cost_price=14.0
    )
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)

    inv = Inventory(
        product_id=p.id,
        current_stock=18,
        reorder_level=20,
        maximum_stock=100
    )
    db_session.add(inv)
    db_session.commit()
    return p


def test_inventory_adapter_restock(db_session, adapt_merchant, adapt_product):
    adapter = InventoryActionAdapter()
    action = Action(
        merchant_id=adapt_merchant.id,
        action_type=ActionType.REORDER,
        status=ActionStatus.APPROVED,
        parameters={"product_id": adapt_product.id, "quantity": 24}
    )
    db_session.add(action)
    db_session.commit()

    res = adapter.execute(action, db_session)
    assert res.success is True
    assert res.status == "EXECUTED"
    assert res.details["quantity_restocked"] == 24
    assert res.details["stock_before"] == 18
    assert res.details["stock_after"] == 42

    # Verify persistent DB state
    inv = db_session.query(Inventory).filter(Inventory.product_id == adapt_product.id).first()
    assert inv.current_stock == 42
    assert inv.last_restocked_at is not None


def test_promotion_adapter_launch(db_session, adapt_merchant, adapt_product):
    adapter = PromotionActionAdapter()
    action = Action(
        merchant_id=adapt_merchant.id,
        action_type=ActionType.PROMOTION,
        status=ActionStatus.APPROVED,
        parameters={"product_id": adapt_product.id, "discount_percentage": 15.0, "duration_hours": 12}
    )
    db_session.add(action)
    db_session.commit()

    res = adapter.execute(action, db_session)
    assert res.success is True
    assert res.status == "EXECUTED"
    assert res.details["discount_percentage"] == 15.0

    # Verify promotion in DB
    promo = db_session.query(Promotion).filter(Promotion.action_id == action.id).first()
    assert promo is not None
    assert promo.status == PromotionStatus.ACTIVE
    assert promo.discount_percentage == 15.0


def test_customer_adapter_winback(db_session, adapt_merchant):
    adapter = CustomerActionAdapter()
    action = Action(
        merchant_id=adapt_merchant.id,
        action_type=ActionType.WINBACK,
        status=ActionStatus.APPROVED,
        parameters={"target_segment": "AT_RISK", "discount_percentage": 10.0}
    )
    db_session.add(action)
    db_session.commit()

    res = adapter.execute(action, db_session)
    assert res.success is True
    assert res.status == "EXECUTED"
    assert res.details["campaign_type"] == "CUSTOMER_WINBACK"
    assert res.details["target_segment"] == "AT_RISK"


def test_mock_paytm_adapter_delegation(db_session, adapt_merchant, adapt_product):
    adapter = MockPaytmAdapter()
    action = Action(
        merchant_id=adapt_merchant.id,
        action_type=ActionType.REORDER,
        status=ActionStatus.APPROVED,
        parameters={"product_id": adapt_product.id, "quantity": 10}
    )
    db_session.add(action)
    db_session.commit()

    res = adapter.execute(action, db_session)
    assert res.success is True
    assert res.status == "EXECUTED"
    assert res.is_mock is True


def test_paytm_adapter_fallback(db_session, adapt_merchant, adapt_product):
    adapter = PaytmAdapter()
    action = Action(
        merchant_id=adapt_merchant.id,
        action_type=ActionType.REORDER,
        status=ActionStatus.APPROVED,
        parameters={"product_id": adapt_product.id, "quantity": 5}
    )
    db_session.add(action)
    db_session.commit()

    res = adapter.execute(action, db_session)
    assert res.success is True
    assert res.is_mock is True
