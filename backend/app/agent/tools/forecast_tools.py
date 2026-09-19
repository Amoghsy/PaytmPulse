"""
Paytm Pulse - Phase 5 Agent Demand Forecast Tools
Exposes demand forecasting from Phase 4 to the Google ADK Gemini agent.
"""

from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.database.connection import get_db_context
from app.intelligence.demand_forecaster import forecast_product_demand


def forecast_demand(
    merchant_id: str,
    product_id: str,
    horizon: str = "next_hour",
    db: Optional[Session] = None
) -> Dict[str, Any]:
    """
    Generate ML and trend-based demand forecasts for a product across short and medium horizons.
    
    Args:
        merchant_id: Unique merchant ID.
        product_id: Unique product ID.
        horizon: Forecast horizon ("next_hour", "next_6h", or "next_day").
        db: Optional active SQLAlchemy session.
        
    Returns:
        Demand forecast metrics dictionary.
    """
    def _execute(session: Session) -> Dict[str, Any]:
        raw = forecast_product_demand(session, merchant_id=merchant_id, product_id=product_id)
        
        # Select forecasted quantity corresponding to requested horizon
        if horizon == "next_6h":
            forecast_val = raw.get("forecast_next_6h", 0.0)
        elif horizon == "next_day":
            forecast_val = raw.get("forecast_next_day", 0.0)
        else:
            forecast_val = raw.get("forecast_next_hour", 0.0)

        return {
            "merchant_id": merchant_id,
            "product_id": product_id,
            "product": raw.get("product_name", "Product"),
            "current_demand": int(raw.get("current_demand", 0)),
            "forecast_demand": float(forecast_val),
            "baseline_demand": float(raw.get("baseline_demand", 0.0)),
            "horizon": horizon,
            "forecast_next_hour": float(raw.get("forecast_next_hour", 0.0)),
            "forecast_next_6h": float(raw.get("forecast_next_6h", 0.0)),
            "forecast_next_day": float(raw.get("forecast_next_day", 0.0)),
            "method": raw.get("method", "statistical_regression")
        }

    if db is not None:
        return _execute(db)
    else:
        with get_db_context() as session:
            return _execute(session)
