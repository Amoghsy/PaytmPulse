import os
import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy import func
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from app.models.transaction import Transaction
from app.models.inventory import Inventory
from app.models.product import Product
from app.models.business_event import EventType, EventSeverity

load_dotenv()

logger = logging.getLogger("paytm_pulse.events.rules")

SPIKE_THRESHOLD = float(os.getenv("EVENT_DEMAND_SPIKE_THRESHOLD", 2.0))
DECLINE_THRESHOLD = float(os.getenv("EVENT_SALES_DECLINE_THRESHOLD", 0.30))


def evaluate_demand_spike(session: Session, merchant_id: str, current_time: datetime) -> tuple[bool, dict]:
    """
    Evaluates if current 1-hour transaction volume/revenue for merchant exceeds 2x historical 30-day hourly average.
    """
    one_hour_ago = current_time - timedelta(hours=1)
    thirty_days_ago = current_time - timedelta(days=30)

    # 1. Current 1-hour metrics
    current_txs = session.query(
        func.count(Transaction.id).label("count"),
        func.coalesce(func.sum(Transaction.amount), 0.0).label("revenue")
    ).filter(
        Transaction.merchant_id == merchant_id,
        Transaction.transaction_timestamp >= one_hour_ago
    ).first()

    current_count = current_txs.count if current_txs else 0
    current_revenue = float(current_txs.revenue) if current_txs else 0.0

    # 2. Historical 30-day average per hour
    total_txs = session.query(
        func.count(Transaction.id).label("count"),
        func.coalesce(func.sum(Transaction.amount), 0.0).label("revenue")
    ).filter(
        Transaction.merchant_id == merchant_id,
        Transaction.transaction_timestamp >= thirty_days_ago,
        Transaction.transaction_timestamp < one_hour_ago
    ).first()

    total_count = total_txs.count if total_txs else 0
    total_revenue = float(total_txs.revenue) if total_txs else 0.0

    # 720 hours in 30 days
    avg_hourly_count = total_count / 720.0
    avg_hourly_revenue = total_revenue / 720.0

    # Trigger if count or revenue is > SPIKE_THRESHOLD * avg (minimum 3 transactions required to prevent false alarms on empty DB)
    if current_count >= 3 and (
        (avg_hourly_count > 0 and current_count >= SPIKE_THRESHOLD * avg_hourly_count) or
        (avg_hourly_revenue > 0 and current_revenue >= SPIKE_THRESHOLD * avg_hourly_revenue) or
        (avg_hourly_count == 0 and current_count >= 5)
    ):
        multiplier = round(current_count / max(avg_hourly_count, 1.0), 2)
        payload = {
            "merchant_id": merchant_id,
            "current_1h_transactions": current_count,
            "current_1h_revenue": current_revenue,
            "historical_avg_hourly_txs": round(avg_hourly_count, 2),
            "historical_avg_hourly_revenue": round(avg_hourly_revenue, 2),
            "spike_multiplier": multiplier,
            "message": f"Demand spike detected: {current_count} transactions in past 1h ({multiplier}x historical hourly average)."
        }
        severity = EventSeverity.HIGH if multiplier >= 3.0 else EventSeverity.MEDIUM
        return True, {"event_type": EventType.DEMAND_SPIKE, "severity": severity, "payload": payload}

    return False, {}


def evaluate_sales_decline(session: Session, merchant_id: str, current_time: datetime) -> tuple[bool, dict]:
    """
    Evaluates if merchant sales over past 7 days dropped by >30% compared to previous 7-day period.
    """
    seven_days_ago = current_time - timedelta(days=7)
    fourteen_days_ago = current_time - timedelta(days=14)

    # Past 7 days sales
    recent_sales = session.query(
        func.coalesce(func.sum(Transaction.amount), 0.0)
    ).filter(
        Transaction.merchant_id == merchant_id,
        Transaction.transaction_timestamp >= seven_days_ago
    ).scalar() or 0.0

    # Previous 7 days sales
    previous_sales = session.query(
        func.coalesce(func.sum(Transaction.amount), 0.0)
    ).filter(
        Transaction.merchant_id == merchant_id,
        Transaction.transaction_timestamp >= fourteen_days_ago,
        Transaction.transaction_timestamp < seven_days_ago
    ).scalar() or 0.0

    recent_sales = float(recent_sales)
    previous_sales = float(previous_sales)

    if previous_sales > 100.0:  # Minimum baseline needed to detect drop
        decline_pct = (previous_sales - recent_sales) / previous_sales
        if decline_pct >= DECLINE_THRESHOLD:
            payload = {
                "merchant_id": merchant_id,
                "recent_7d_sales": recent_sales,
                "previous_7d_sales": previous_sales,
                "decline_percentage": round(decline_pct * 100, 2),
                "message": f"Sales decline detected: {round(decline_pct * 100, 1)}% drop in past 7 days compared to prior week."
            }
            severity = EventSeverity.HIGH if decline_pct >= 0.50 else EventSeverity.MEDIUM
            return True, {"event_type": EventType.SALES_DECLINE, "severity": severity, "payload": payload}

    return False, {}


def evaluate_stockout_risk(session: Session, merchant_id: str, product_id: str) -> tuple[bool, dict]:
    """
    Evaluates if product stock is at or below reorder level.
    """
    inv = session.query(Inventory).filter(
        Inventory.product_id == product_id
    ).first()

    if inv:
        prod = session.query(Product).filter(Product.id == product_id).first()
        prod_name = prod.name if prod else "Unknown Product"

        if inv.current_stock <= inv.reorder_level:
            severity = EventSeverity.CRITICAL if inv.current_stock <= 2 else EventSeverity.HIGH
            payload = {
                "merchant_id": merchant_id,
                "product_id": product_id,
                "product_name": prod_name,
                "available_stock": inv.current_stock,
                "reorder_level": inv.reorder_level,
                "message": f"Stockout risk for '{prod_name}': Available stock ({inv.current_stock}) is at or below reorder level ({inv.reorder_level})."
            }
            return True, {"event_type": EventType.STOCKOUT_RISK, "severity": severity, "payload": payload}

    return False, {}
