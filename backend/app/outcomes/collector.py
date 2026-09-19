import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.action import Action
from app.models.transaction import Transaction
from app.models.inventory import Inventory
from app.outcomes.schemas import BaselineSnapshot, ObservedMetrics

logger = logging.getLogger("paytm_pulse.outcomes.collector")


def ensure_utc(dt: Optional[datetime]) -> datetime:
    if dt is None:
        return datetime.now(timezone.utc)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class OutcomeDataCollector:
    """
    Collects post-action business data within the observation window.
    """

    def __init__(self, db: Session):
        self.db = db

    def collect(self, action: Action, baseline: BaselineSnapshot) -> ObservedMetrics:
        """
        Collect empirical observations following action execution.
        """
        merchant_id = action.merchant_id
        action_type = str(action.action_type.value if hasattr(action.action_type, "value") else action.action_type).upper()
        params = action.parameters or {}
        start_time = action.executed_at or action.created_at
        now = datetime.now(timezone.utc)
        
        # Calculate observed window duration
        hours_elapsed = max(0.01, (ensure_utc(now) - ensure_utc(start_time)).total_seconds() / 3600.0)

        metrics = ObservedMetrics(
            collected_at=now,
            window_hours_observed=round(hours_elapsed, 2),
            metadata={
                "start_time": start_time.isoformat() if start_time else None,
                "end_time": now.isoformat(),
            }
        )

        try:
            # 1. Product specific or Store wide transaction aggregation
            product_id = baseline.product_id or params.get("product_id")
            tx_query = self.db.query(
                func.count(Transaction.id).label("tx_count"),
                func.sum(Transaction.amount).label("total_revenue"),
                func.sum(Transaction.quantity).label("total_units")
            ).filter(
                Transaction.merchant_id == merchant_id,
                Transaction.created_at >= start_time,
                Transaction.created_at <= now
            )

            if product_id:
                tx_query = tx_query.filter(Transaction.product_id == product_id)

            res = tx_query.first()
            if res and res.tx_count:
                metrics.transactions_count = int(res.tx_count or 0)
                metrics.actual_sales_revenue = float(res.total_revenue or 0.0)
                metrics.sales_after = float(res.total_revenue or 0.0)
                metrics.revenue_after = float(res.total_revenue or 0.0)
                metrics.units_sold = int(res.total_units or 0)

            # 2. Inventory state check
            if product_id:
                inv = self.db.query(Inventory).filter(
                    Inventory.product_id == product_id
                ).first()
                if inv:
                    metrics.final_stock_level = inv.current_stock
                    metrics.inventory_after = inv.current_stock
                    metrics.stockout_occurred = (inv.current_stock <= 0)

            # 3. Customer response & Winback collection
            target_customers = baseline.target_customer_ids or params.get("customer_ids") or []
            if target_customers:
                returning_tx = self.db.query(Transaction.customer_id).filter(
                    Transaction.merchant_id == merchant_id,
                    Transaction.customer_id.in_(target_customers),
                    Transaction.created_at >= start_time,
                    Transaction.created_at <= now
                ).distinct().all()

                returning_ids = [r[0] for r in returning_tx if r[0]]
                metrics.returning_customers_count = len(returning_ids)
                metrics.returning_customer_ids = returning_ids
                metrics.offer_conversions = len(returning_ids)

            # 4. Cross-sell / Secondary product collection
            secondary_id = baseline.metadata.get("secondary_product_id") or params.get("secondary_product_id")
            if secondary_id:
                sec_tx = self.db.query(func.sum(Transaction.quantity)).filter(
                    Transaction.merchant_id == merchant_id,
                    Transaction.product_id == secondary_id,
                    Transaction.created_at >= start_time,
                    Transaction.created_at <= now
                ).scalar()
                metrics.secondary_units_sold = int(sec_tx or 0)

        except Exception as e:
            logger.error(f"Error collecting post-action observations for action {action.id}: {e}", exc_info=True)
            metrics.metadata["collection_error"] = str(e)

        return metrics
