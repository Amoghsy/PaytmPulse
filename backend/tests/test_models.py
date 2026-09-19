from decimal import Decimal
from datetime import datetime, timezone
from app.models import (
    Merchant, MerchantCategory,
    Product, Inventory, Customer, Transaction, PaymentMethod
)


def test_merchant_creation(db_session):
    merchant = Merchant(
        name="Test Merchant",
        shop_name="Test Shop",
        category=MerchantCategory.KIRANA,
        location="Bengaluru",
        language="Kannada",
        phone="9999988888"
    )
    db_session.add(merchant)
    db_session.commit()

    saved = db_session.query(Merchant).filter_by(phone="9999988888").first()
    assert saved is not None
    assert saved.shop_name == "Test Shop"
    assert saved.category == MerchantCategory.KIRANA


def test_product_and_inventory_relationship(db_session):
    merchant = Merchant(
        name="Test Merchant",
        shop_name="Test Shop",
        category=MerchantCategory.PHARMACY,
        location="Delhi",
        phone="9999977777"
    )
    db_session.add(merchant)
    db_session.commit()

    product = Product(
        merchant_id=merchant.id,
        name="Paracetamol 650mg",
        category="Medicines",
        price=Decimal("30.00"),
        cost_price=Decimal("20.00"),
        current_stock=50,
        reorder_level=10
    )
    db_session.add(product)
    db_session.commit()

    inventory = Inventory(
        product_id=product.id,
        current_stock=50,
        reorder_level=10,
        maximum_stock=200
    )
    db_session.add(inventory)
    db_session.commit()

    saved_prod = db_session.query(Product).filter_by(id=product.id).first()
    assert saved_prod.inventory is not None
    assert saved_prod.inventory.current_stock == 50


def test_transaction_creation(db_session):
    merchant = Merchant(
        name="Test Merchant",
        shop_name="Test Shop",
        category=MerchantCategory.RESTAURANT,
        location="Mumbai",
        phone="9999966666"
    )
    db_session.add(merchant)
    db_session.commit()

    product = Product(
        merchant_id=merchant.id,
        name="Veg Biryani",
        category="Main Course",
        price=Decimal("200.00"),
        cost_price=Decimal("90.00"),
        current_stock=30,
        reorder_level=5
    )
    db_session.add(product)

    customer = Customer(
        merchant_id=merchant.id,
        name="Aman Gupta",
        phone="9876500000",
        total_spend=Decimal("200.00"),
        purchase_count=1
    )
    db_session.add(customer)
    db_session.commit()

    tx = Transaction(
        merchant_id=merchant.id,
        product_id=product.id,
        customer_id=customer.id,
        quantity=1,
        unit_price=Decimal("200.00"),
        amount=Decimal("200.00"),
        payment_method=PaymentMethod.UPI,
        transaction_timestamp=datetime.now(timezone.utc)
    )
    db_session.add(tx)
    db_session.commit()

    saved_tx = db_session.query(Transaction).filter_by(id=tx.id).first()
    assert saved_tx is not None
    assert saved_tx.amount == Decimal("200.00")
    assert saved_tx.payment_method == PaymentMethod.UPI
