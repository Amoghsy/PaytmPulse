import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.action import Action, ActionType, ActionStatus
from app.models.transaction import Transaction
from app.models.customer import Customer
from app.models.business_event import BusinessEvent, EventType
from app.intelligence.sales_analyzer import analyze_merchant_sales
from app.financial.rules import FinancialRulesEngine
from app.financial.schemas import FinancialNeedDetectionResult

logger = logging.getLogger("paytm_pulse.financial.need_detector")


class FinancialNeedDetector:
    """
    Extracts live merchant business signals and feeds them to the rules engine
    to detect potential working capital, inventory, or expansion requirements.
    """

    def __init__(self, db: Session):
        self.db = db

    def detect_financial_need(self, merchant_id: str) -> FinancialNeedDetectionResult:
        """
        Gathers business metrics and runs deterministic evaluation.
        """
        metrics = self._gather_merchant_signals(merchant_id)
        return FinancialRulesEngine.evaluate(merchant_id, metrics)

    def _gather_merchant_signals(self, merchant_id: str) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        lookback_7d = now - timedelta(days=7)
        lookback_14d = now - timedelta(days=14)

        # 1. Sales & Growth from Sales Analyzer / DB
        avg_daily_sales = 1500.0
        sales_growth = 0.0
        try:
            sales_info = analyze_merchant_sales(self.db, merchant_id=merchant_id, days=14)
            sales_metrics = sales_info.get("sales", {})
            avg_daily_sales = float(sales_metrics.get("average_daily_sales", 1500.0))
            growth_pct = float(sales_metrics.get("growth_percentage", 0.0))
            sales_growth = round(growth_pct / 100.0, 2)
        except Exception as e:
            logger.warning(f"Sales analysis fallback for merchant {merchant_id}: {e}")

        # 2. Demand Surge Signals from Business Events
        demand_events = self.db.query(BusinessEvent).filter(
            BusinessEvent.merchant_id == merchant_id,
            BusinessEvent.event_type.in_([EventType.DEMAND_SPIKE, EventType.STOCKOUT_RISK]),
            BusinessEvent.created_at >= lookback_7d
        ).all()

        demand_growth = 0.0
        for ev in demand_events:
            payload = ev.payload or {}
            spike_pct = payload.get("spike_percentage") or payload.get("surge_ratio", 0.0)
            if spike_pct:
                val = float(spike_pct)
                if val > 1.0:
                    val = val / 100.0
                demand_growth = max(demand_growth, val)

        # If no explicit event payload, check recent 3-day transaction velocity vs previous 7-day
        if demand_growth == 0.0:
            tx_7d = self.db.query(func.sum(Transaction.amount)).filter(
                Transaction.merchant_id == merchant_id,
                Transaction.created_at >= lookback_7d
            ).scalar() or 0.0
            tx_14d = self.db.query(func.sum(Transaction.amount)).filter(
                Transaction.merchant_id == merchant_id,
                Transaction.created_at >= lookback_14d,
                Transaction.created_at < lookback_7d
            ).scalar() or 0.0

            if tx_14d > 0:
                demand_growth = round(max(0.0, (float(tx_7d) - float(tx_14d)) / float(tx_14d)), 2)

        # 3. Restock Actions Count & Spend in last 7 days
        restock_actions = self.db.query(Action).filter(
            Action.merchant_id == merchant_id,
            Action.action_type.in_([ActionType.REORDER, "REORDER", "RESTOCK_PRODUCT"]),
            Action.created_at >= lookback_7d
        ).all()

        restock_count = len(restock_actions)
        recent_restock_spend = 0.0
        for act in restock_actions:
            params = act.parameters or {}
            qty = params.get("quantity") or params.get("restock_quantity", 24)
            unit_cost = params.get("unit_cost") or params.get("cost_price", 28.0)
            recent_restock_spend += float(qty) * float(unit_cost)

        # 4. Customer Growth
        total_customers = self.db.query(func.count(Customer.id)).filter(
            Customer.merchant_id == merchant_id
        ).scalar() or 0

        recent_new_customers = self.db.query(func.count(Customer.id)).filter(
            Customer.merchant_id == merchant_id,
            Customer.created_at >= lookback_7d
        ).scalar() or 0

        customer_growth = 0.0
        if total_customers > 0:
            customer_growth = round(recent_new_customers / max(1, total_customers), 2)

        return {
            "demand_growth": demand_growth,
            "sales_growth": sales_growth,
            "restock_count_last_7_days": restock_count,
            "recent_restock_spend": recent_restock_spend,
            "average_daily_sales": avg_daily_sales,
            "customer_growth": customer_growth,
            "total_customers": total_customers
        }
