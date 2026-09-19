import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.action import Action
from app.models.inventory import Inventory
from app.models.transaction import Transaction
from app.models.product import Product
from app.outcomes.schemas import BaselineSnapshot
from app.outcomes.config import get_observation_window_hours

logger = logging.getLogger("paytm_pulse.outcomes.baseline")


def ensure_utc(dt: Optional[datetime]) -> datetime:
    if dt is None:
        return datetime.now(timezone.utc)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class BaselineCapturer:
    """
    Captures pre-action business metrics at execution time.
    Provides the anchor for counterfactual & before-vs-after comparison.
    """

    def __init__(self, db: Session):
        self.db = db

    def capture_baseline(self, action: Action) -> BaselineSnapshot:
        """
        Extract pre-action context for the given action.
        """
        action_type = str(action.action_type.value if hasattr(action.action_type, "value") else action.action_type).upper()
        params = action.parameters or {}
        merchant_id = action.merchant_id
        now = ensure_utc(action.executed_at) if action.executed_at else datetime.now(timezone.utc)
        window_hours = get_observation_window_hours(action_type)
        lookback = now - timedelta(hours=max(24, window_hours))

        snapshot = BaselineSnapshot(
            captured_at=now,
            product_id=params.get("product_id"),
            baseline_start_time=lookback,
            baseline_end_time=now,
            measurement_start_time=now,
            measurement_end_time=now + timedelta(hours=window_hours),
            metadata={
                "action_id": action.id,
                "action_type": action_type,
                "merchant_id": merchant_id,
                "window_hours": window_hours,
            }
        )

        try:
            if action_type in ["REORDER", "RESTOCK_PRODUCT"]:
                self._capture_inventory_baseline(snapshot, merchant_id, params, now, window_hours)
            elif action_type in ["PROMOTION", "SEND_OFFER", "RUN_PROMOTION"]:
                self._capture_promotion_baseline(snapshot, merchant_id, params, now, window_hours)
            elif action_type in ["WINBACK", "CUSTOMER_WINBACK", "CUSTOMER_RETENTION"]:
                self._capture_customer_baseline(snapshot, merchant_id, params, now, window_hours)
            elif action_type in ["CROSS_SELL", "CREATE_BUNDLE"]:
                self._capture_cross_sell_baseline(snapshot, merchant_id, params, now, window_hours)
            else:
                self._capture_general_baseline(snapshot, merchant_id, now, window_hours)
        except Exception as e:
            logger.warning(f"Error capturing baseline for action {action.id}: {e}", exc_info=True)
            snapshot.metadata["baseline_warning"] = str(e)

        return snapshot

    def _capture_inventory_baseline(
        self,
        snapshot: BaselineSnapshot,
        merchant_id: str,
        params: Dict[str, Any],
        now: datetime,
        window_hours: int
    ):
        product_id = params.get("product_id")
        if product_id:
            inv = self.db.query(Inventory).filter(
                Inventory.product_id == product_id
            ).first()
            if inv:
                stock_val = params.get("stock_before") if params.get("stock_before") is not None else inv.current_stock
                snapshot.stock_level_before = stock_val
                snapshot.inventory_before = stock_val
                snapshot.metadata["reorder_point"] = inv.reorder_level
                snapshot.metadata["restock_quantity"] = params.get("quantity") or params.get("restock_quantity", 0)

            # Historical sales of this product in previous lookback window
            lookback = now - timedelta(hours=max(24, window_hours))
            recent_sales = self.db.query(
                func.sum(Transaction.amount).label("revenue"),
                func.count(Transaction.id).label("tx_count"),
                func.sum(Transaction.quantity).label("units")
            ).filter(
                Transaction.merchant_id == merchant_id,
                Transaction.product_id == product_id,
                Transaction.created_at >= lookback,
                Transaction.created_at < now
            ).first()

            if recent_sales and recent_sales.revenue is not None:
                rev = float(recent_sales.revenue)
                units = int(recent_sales.units or 0)
                snapshot.historical_daily_revenue = rev
                snapshot.revenue_before = rev
                snapshot.sales_before = rev
                snapshot.transactions_before = int(recent_sales.tx_count or 0)
                hours_diff = max(1.0, (now - lookback).total_seconds() / 3600.0)
                velocity = units / hours_diff
                snapshot.historical_sales_velocity = velocity
                snapshot.product_demand_before = velocity
                prod = self.db.query(Product).filter(Product.id == product_id).first()
                unit_price = float(prod.price) if prod else 30.0
                snapshot.expected_sales_window = round(velocity * window_hours * unit_price, 2)
            else:
                prod = self.db.query(Product).filter(Product.id == product_id).first()
                unit_price = float(prod.price) if prod else 30.0
                snapshot.historical_sales_velocity = 1.5
                snapshot.product_demand_before = 1.5
                snapshot.expected_sales_window = round(1.5 * window_hours * unit_price, 2)
                snapshot.revenue_before = snapshot.expected_sales_window
                snapshot.sales_before = snapshot.expected_sales_window

    def _capture_promotion_baseline(
        self,
        snapshot: BaselineSnapshot,
        merchant_id: str,
        params: Dict[str, Any],
        now: datetime,
        window_hours: int
    ):
        product_id = params.get("product_id")
        snapshot.metadata["discount_percent"] = params.get("discount_percent") or params.get("discount", 10)
        
        # Historical sales without discount
        lookback = now - timedelta(hours=window_hours)
        sales = self.db.query(
            func.sum(Transaction.amount).label("revenue"),
            func.count(Transaction.id).label("tx_count")
        ).filter(
            Transaction.merchant_id == merchant_id,
            Transaction.created_at >= lookback,
            Transaction.created_at < now
        )
        if product_id:
            sales = sales.filter(Transaction.product_id == product_id)
        
        result = sales.first()
        rev = float(result.revenue) if result and result.revenue else 0.0
        tx_cnt = int(result.tx_count) if result and result.tx_count else 0
        snapshot.historical_daily_revenue = rev
        snapshot.revenue_before = rev
        snapshot.sales_before = rev
        snapshot.transactions_before = tx_cnt
        snapshot.expected_sales_window = rev
        snapshot.historical_conversion_rate = 0.05

    def _capture_customer_baseline(
        self,
        snapshot: BaselineSnapshot,
        merchant_id: str,
        params: Dict[str, Any],
        now: datetime,
        window_hours: int
    ):
        customer_ids = params.get("customer_ids") or []
        snapshot.target_customer_ids = customer_ids
        target_cnt = len(customer_ids) if customer_ids else params.get("target_count", 0)
        snapshot.target_customer_count = target_cnt
        snapshot.customer_activity_before = target_cnt
        snapshot.historical_conversion_rate = 0.02
        snapshot.metadata["offer_code"] = params.get("offer_code", "WELCOME_BACK")

    def _capture_cross_sell_baseline(
        self,
        snapshot: BaselineSnapshot,
        merchant_id: str,
        params: Dict[str, Any],
        now: datetime,
        window_hours: int
    ):
        primary_id = params.get("primary_product_id")
        secondary_id = params.get("secondary_product_id") or params.get("bundle_product_id")
        snapshot.metadata["primary_product_id"] = primary_id
        snapshot.metadata["secondary_product_id"] = secondary_id
        snapshot.historical_conversion_rate = 0.03

    def _capture_general_baseline(
        self,
        snapshot: BaselineSnapshot,
        merchant_id: str,
        now: datetime,
        window_hours: int
    ):
        lookback = now - timedelta(hours=window_hours)
        sales = self.db.query(
            func.sum(Transaction.amount).label("revenue"),
            func.count(Transaction.id).label("tx_count")
        ).filter(
            Transaction.merchant_id == merchant_id,
            Transaction.created_at >= lookback,
            Transaction.created_at < now
        ).first()

        rev = float(sales.revenue) if sales and sales.revenue else 0.0
        tx_cnt = int(sales.tx_count) if sales and sales.tx_count else 0
        snapshot.historical_daily_revenue = rev
        snapshot.revenue_before = rev
        snapshot.sales_before = rev
        snapshot.transactions_before = tx_cnt
        snapshot.expected_sales_window = rev
