"""
Paytm Pulse - Phase 5 Agent Inventory & Stockout Tools
Exposes stockout risk and inventory runway analysis from Phase 4 to the Google ADK Gemini agent.
"""

from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.database.connection import get_db_context
from app.intelligence.stockout_predictor import predict_product_stockout, predict_merchant_stockouts


def predict_stockout(
    merchant_id: str,
    product_id: str,
    db: Optional[Session] = None
) -> Dict[str, Any]:
    """
    Evaluate real-time stockout risk, velocity, and estimated runway hours for a specific product.
    
    Args:
        merchant_id: Unique merchant ID.
        product_id: Unique product ID.
        db: Optional active SQLAlchemy session.
        
    Returns:
        Stockout prediction metrics dictionary.
    """
    def _execute(session: Session) -> Dict[str, Any]:
        raw = predict_product_stockout(session, merchant_id=merchant_id, product_id=product_id)
        return {
            "merchant_id": merchant_id,
            "product_id": product_id,
            "product": raw.get("product_name", "Product"),
            "current_stock": int(raw.get("current_stock", 0)),
            "forecast_hourly_demand": float(raw.get("forecast_hourly_demand", 0.0)),
            "average_hourly_demand": float(raw.get("average_hourly_demand", 0.0)),
            "estimated_hours_to_stockout": float(raw.get("estimated_hours_to_stockout", 999.0)),
            "estimated_minutes_to_stockout": int(raw.get("estimated_minutes_to_stockout", 0)),
            "risk": str(raw.get("stockout_risk", "LOW")),
            "reorder_recommended": bool(raw.get("reorder_recommended", False))
        }

    if db is not None:
        return _execute(db)
    else:
        with get_db_context() as session:
            return _execute(session)


def get_all_stockout_risks(
    merchant_id: str,
    db: Optional[Session] = None
) -> Dict[str, Any]:
    """
    Retrieve all at-risk products for a merchant sorted by urgency of stockout.
    
    Args:
        merchant_id: Unique merchant ID.
        db: Optional active SQLAlchemy session.
        
    Returns:
        Dictionary of critical, high, and medium stockout risk items.
    """
    def _execute(session: Session) -> Dict[str, Any]:
        raw_list = predict_merchant_stockouts(session, merchant_id=merchant_id)
        at_risk = [p for p in raw_list if p.get("stockout_risk") in ["CRITICAL", "HIGH", "MEDIUM"]]
        return {
            "merchant_id": merchant_id,
            "total_at_risk": len(at_risk),
            "at_risk_products": at_risk,
            "all_products": raw_list
        }

    if db is not None:
        return _execute(db)
    else:
        with get_db_context() as session:
            return _execute(session)
