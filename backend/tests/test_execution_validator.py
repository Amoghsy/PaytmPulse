import pytest
from app.models.merchant import Merchant, MerchantCategory
from app.models.product import Product
from app.models.action import Action, ActionType, ActionStatus
from app.execution.validator import ActionValidator
from app.execution.exceptions import (
    ActionValidationError,
    ActionNotApprovedError,
    ActionAlreadyExecutedError
)


@pytest.fixture
def val_merchant(db_session):
    m = Merchant(
        name="Kiran Rao",
        shop_name="Kiran Departmental",
        category=MerchantCategory.KIRANA,
        location="MG Road, Bengaluru",
        language="Kannada",
        phone="919876540001"
    )
    db_session.add(m)
    db_session.commit()
    db_session.refresh(m)
    return m


@pytest.fixture
def val_product(db_session, val_merchant):
    p = Product(
        merchant_id=val_merchant.id,
        name="Sunflower Oil 1L",
        category="Groceries",
        price=180.0,
        cost_price=140.0
    )
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)
    return p


def test_validator_approved_action_success(db_session, val_merchant, val_product):
    act = Action(
        merchant_id=val_merchant.id,
        action_type=ActionType.REORDER,
        status=ActionStatus.APPROVED,
        parameters={"product_id": val_product.id, "quantity": 20}
    )
    db_session.add(act)
    db_session.commit()

    # Should not raise
    ActionValidator.validate_for_execution(act, db_session)


def test_validator_unapproved_action_rejected(db_session, val_merchant, val_product):
    act = Action(
        merchant_id=val_merchant.id,
        action_type=ActionType.REORDER,
        status=ActionStatus.PENDING,  # Not APPROVED
        parameters={"product_id": val_product.id, "quantity": 20}
    )
    db_session.add(act)
    db_session.commit()

    with pytest.raises(ActionNotApprovedError):
        ActionValidator.validate_for_execution(act, db_session)


def test_validator_already_executed_action_rejected(db_session, val_merchant, val_product):
    act = Action(
        merchant_id=val_merchant.id,
        action_type=ActionType.REORDER,
        status=ActionStatus.EXECUTED,
        parameters={"product_id": val_product.id, "quantity": 20}
    )
    db_session.add(act)
    db_session.commit()

    with pytest.raises(ActionAlreadyExecutedError):
        ActionValidator.validate_for_execution(act, db_session)


def test_validator_invalid_restock_quantity(db_session, val_merchant, val_product):
    act = Action(
        merchant_id=val_merchant.id,
        action_type=ActionType.REORDER,
        status=ActionStatus.APPROVED,
        parameters={"product_id": val_product.id, "quantity": -5}
    )
    db_session.add(act)
    db_session.commit()

    with pytest.raises(ActionValidationError):
        ActionValidator.validate_for_execution(act, db_session)


def test_validator_invalid_promotion_discount(db_session, val_merchant, val_product):
    act = Action(
        merchant_id=val_merchant.id,
        action_type=ActionType.PROMOTION,
        status=ActionStatus.APPROVED,
        parameters={"product_id": val_product.id, "discount_percentage": 75.0}  # Over 50%
    )
    db_session.add(act)
    db_session.commit()

    with pytest.raises(ActionValidationError):
        ActionValidator.validate_for_execution(act, db_session)
