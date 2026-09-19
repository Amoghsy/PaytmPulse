from decimal import Decimal
from datetime import datetime, timezone
from app.models import Merchant, MerchantCategory, Product, Customer, Transaction, PaymentMethod


def test_list_merchants_endpoint(client, db_session):
    merchant = Merchant(
        name="Ravi Kumar",
        shop_name="Ravi Store",
        category=MerchantCategory.KIRANA,
        location="Bengaluru",
        phone="9876543210"
    )
    db_session.add(merchant)
    db_session.commit()

    response = client.get("/merchants")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["shop_name"] == "Ravi Store"


def test_merchant_summary_endpoint(client, db_session):
    merchant = Merchant(
        name="Sharma Ji",
        shop_name="Sharma Kirana",
        category=MerchantCategory.KIRANA,
        location="Delhi",
        phone="9876543211"
    )
    db_session.add(merchant)
    db_session.commit()

    product = Product(
        merchant_id=merchant.id,
        name="Atta 5kg",
        category="Staples",
        price=Decimal("250.00"),
        cost_price=Decimal("210.00"),
        current_stock=20
    )
    db_session.add(product)

    customer = Customer(
        merchant_id=merchant.id,
        name="Vijay Kumar",
        phone="9876511111",
        total_spend=Decimal("250.00"),
        purchase_count=1
    )
    db_session.add(customer)
    db_session.commit()

    tx = Transaction(
        merchant_id=merchant.id,
        product_id=product.id,
        customer_id=customer.id,
        quantity=1,
        unit_price=Decimal("250.00"),
        amount=Decimal("250.00"),
        payment_method=PaymentMethod.UPI,
        transaction_timestamp=datetime.now(timezone.utc)
    )
    db_session.add(tx)
    db_session.commit()

    response = client.get(f"/merchants/{merchant.id}/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["shop_name"] == "Sharma Kirana"
    assert data["total_products"] == 1
    assert data["total_customers"] == 1
    assert data["total_transactions"] == 1
    assert data["total_revenue"] == 250.0


def test_merchant_not_found(client):
    response = client.get("/merchants/non-existent-id")
    assert response.status_code == 404
    data = response.json()
    assert data["detail"]["error"]["code"] == "MERCHANT_NOT_FOUND"
