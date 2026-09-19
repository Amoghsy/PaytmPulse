"""
Paytm Pulse - Phase 5 Agent Sales Tools
Exposes sales analytics from Phase 4 to the Google ADK Gemini agent.
"""

from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.database.connection import get_db_context
from app.intelligence.sales_analyzer import analyze_merchant_sales


def get_sales_analysis(merchant_id: str, db: Optional[Session] = None) -> Dict[str, Any]:
    """
    Get multi-horizon sales performance, trends, top/slow products, and peak sales hours for a merchant.
    
    Args:
        merchant_id: Unique merchant ID.
        db: Optional active SQLAlchemy session.
        
    Returns:
        Structured sales metrics dictionary.
    """
    def _execute(session: Session) -> Dict[str, Any]:
        raw = analyze_merchant_sales(session, merchant_id=merchant_id, days=30)
        sales_info = raw.get("sales", {})
        
        # Flatten and standardise for agent consumption
        return {
            "merchant_id": merchant_id,
            "today_sales": float(sales_info.get("today", 0.0)),
            "yesterday_sales": float(sales_info.get("yesterday", 0.0)),
            "last_7_days_sales": float(sales_info.get("last_7_days", 0.0)),
            "last_30_days_sales": float(sales_info.get("last_30_days", 0.0)),
            "average_daily_sales": float(sales_info.get("average_daily_sales", 0.0)),
            "growth_percentage": float(sales_info.get("growth_percentage", 0.0)),
            "transaction_count": int(sales_info.get("transaction_count", 0)),
            "average_transaction_value": float(sales_info.get("average_transaction_value", 0.0)),
            "top_products": raw.get("top_products", []),
            "slow_products": raw.get("slow_products", []),
            "peak_sales_period": raw.get("peak_sales_period", {}),
            "peak_hours": raw.get("sales_by_hour", {})
        }

    if db is not None:
        return _execute(db)
    else:
        with get_db_context() as session:
            return _execute(session)
