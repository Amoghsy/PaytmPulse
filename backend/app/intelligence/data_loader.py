import logging
from datetime import datetime, timedelta
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.merchant import Merchant
from app.models.product import Product
from app.models.customer import Customer
from app.models.inventory import Inventory
from app.models.transaction import Transaction
from app.models.business_event import BusinessEvent
from app.models.base import utc_now

logger = logging.getLogger("paytm_pulse.intelligence.data_loader")


def load_merchant_sales(session: Session, merchant_id: str, days: int = 30) -> pd.DataFrame:
    """
    Retrieves all transactions for a merchant within the past `days` as a DataFrame.
    """
    cutoff = utc_now() - timedelta(days=days)
    records = session.query(
        Transaction.id,
        Transaction.merchant_id,
        Transaction.product_id,
        Transaction.customer_id,
        Transaction.quantity,
        Transaction.unit_price,
        Transaction.amount,
        Transaction.payment_method,
        Transaction.transaction_timestamp
    ).filter(
        Transaction.merchant_id == merchant_id,
        Transaction.transaction_timestamp >= cutoff
    ).order_by(Transaction.transaction_timestamp.asc()).all()

    if not records:
        return pd.DataFrame(columns=[
            "id", "merchant_id", "product_id", "customer_id",
            "quantity", "unit_price", "amount", "payment_method", "transaction_timestamp"
        ])

    df = pd.DataFrame([
        {
            "id": r.id,
            "merchant_id": r.merchant_id,
            "product_id": r.product_id,
            "customer_id": r.customer_id,
            "quantity": int(r.quantity),
            "unit_price": float(r.unit_price),
            "amount": float(r.amount),
            "payment_method": r.payment_method.value if hasattr(r.payment_method, "value") else str(r.payment_method),
            "transaction_timestamp": pd.to_datetime(r.transaction_timestamp, utc=True)
        } for r in records
    ])
    return df


def load_product_sales(session: Session, merchant_id: str, product_id: str = None, days: int = 30) -> pd.DataFrame:
    """
    Retrieves product transaction records merged with Product master details.
    """
    cutoff = utc_now() - timedelta(days=days)
    query = session.query(
        Transaction.id,
        Transaction.merchant_id,
        Transaction.product_id,
        Product.name.label("product_name"),
        Product.category.label("category"),
        Product.price.label("catalog_price"),
        Product.cost_price.label("cost_price"),
        Transaction.quantity,
        Transaction.unit_price,
        Transaction.amount,
        Transaction.transaction_timestamp
    ).join(Product, Transaction.product_id == Product.id).filter(
        Transaction.merchant_id == merchant_id,
        Transaction.transaction_timestamp >= cutoff
    )

    if product_id:
        query = query.filter(Transaction.product_id == product_id)

    records = query.order_by(Transaction.transaction_timestamp.asc()).all()

    if not records:
        return pd.DataFrame(columns=[
            "id", "merchant_id", "product_id", "product_name", "category",
            "catalog_price", "cost_price", "quantity", "unit_price", "amount", "transaction_timestamp"
        ])

    df = pd.DataFrame([
        {
            "id": r.id,
            "merchant_id": r.merchant_id,
            "product_id": r.product_id,
            "product_name": r.product_name,
            "category": r.category,
            "catalog_price": float(r.catalog_price),
            "cost_price": float(r.cost_price),
            "quantity": int(r.quantity),
            "unit_price": float(r.unit_price),
            "amount": float(r.amount),
            "transaction_timestamp": pd.to_datetime(r.transaction_timestamp, utc=True)
        } for r in records
    ])
    return df


def load_inventory_data(session: Session, merchant_id: str) -> pd.DataFrame:
    """
    Retrieves current inventory stock levels merged with product catalogue.
    """
    records = session.query(
        Product.id.label("product_id"),
        Product.name.label("product_name"),
        Product.category,
        Product.price,
        Product.cost_price,
        Product.average_daily_sales,
        Inventory.current_stock,
        Inventory.reorder_level,
        Inventory.maximum_stock,
        Inventory.last_restocked_at
    ).outerjoin(Inventory, Product.id == Inventory.product_id).filter(
        Product.merchant_id == merchant_id,
        Product.is_active.is_(True)
    ).all()

    if not records:
        return pd.DataFrame(columns=[
            "product_id", "product_name", "category", "price", "cost_price",
            "average_daily_sales", "current_stock", "reorder_level", "maximum_stock", "last_restocked_at"
        ])

    df = pd.DataFrame([
        {
            "product_id": r.product_id,
            "product_name": r.product_name,
            "category": r.category,
            "price": float(r.price),
            "cost_price": float(r.cost_price),
            "average_daily_sales": float(r.average_daily_sales or 0.0),
            "current_stock": int(r.current_stock if r.current_stock is not None else 0),
            "reorder_level": int(r.reorder_level if r.reorder_level is not None else 10),
            "maximum_stock": int(r.maximum_stock if r.maximum_stock is not None else 100),
            "last_restocked_at": pd.to_datetime(r.last_restocked_at, utc=True) if r.last_restocked_at else None
        } for r in records
    ])
    return df


def load_customer_transactions(session: Session, merchant_id: str) -> pd.DataFrame:
    """
    Retrieves customer records merged with transaction history for RFM intelligence.
    """
    customers = session.query(Customer).filter(Customer.merchant_id == merchant_id).all()
    if not customers:
        return pd.DataFrame(columns=[
            "customer_id", "name", "phone", "total_spend", "purchase_count",
            "last_purchase_at", "average_purchase_interval"
        ])

    df = pd.DataFrame([
        {
            "customer_id": c.id,
            "name": c.name,
            "phone": c.phone,
            "total_spend": float(c.total_spend or 0.0),
            "purchase_count": int(c.purchase_count or 0),
            "last_purchase_at": pd.to_datetime(c.last_purchase_at, utc=True) if c.last_purchase_at else None,
            "average_purchase_interval": float(c.average_purchase_interval) if c.average_purchase_interval else None
        } for c in customers
    ])
    return df


def load_hourly_aggregation(session: Session, merchant_id: str, product_id: str = None, days: int = 30) -> pd.DataFrame:
    """
    Aggregates transaction metrics by hour bucket for time-series modeling.
    """
    df = load_product_sales(session, merchant_id, product_id=product_id, days=days)
    if df.empty:
        return pd.DataFrame(columns=["timestamp_hour", "quantity", "revenue", "order_count", "aov"])

    df["timestamp_hour"] = df["transaction_timestamp"].dt.floor("h")
    agg = df.groupby("timestamp_hour").agg(
        quantity=("quantity", "sum"),
        revenue=("amount", "sum"),
        order_count=("id", "count")
    ).reset_index()

    agg["aov"] = agg["revenue"] / agg["order_count"]
    agg = agg.sort_values("timestamp_hour").reset_index(drop=True)
    return agg
