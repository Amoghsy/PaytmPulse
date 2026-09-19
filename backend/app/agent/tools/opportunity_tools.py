"""
Paytm Pulse - Phase 5 Agent Opportunity Detection Tools
Exposes revenue, restocking, cross-sell, and retention opportunities from Phase 4 to the Google ADK Gemini agent.
"""

from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from app.database.connection import get_db_context
from app.intelligence.opportunity_detector import detect_merchant_opportunities


def detect_opportunities(
    merchant_id: str,
    db: Optional[Session] = None
) -> Dict[str, Any]:
    """
    Scan sales trends, stockout risks, customer churn, and cross-sell affinities to discover high-value business opportunities.
    
    Args:
        merchant_id: Unique merchant ID.
        db: Optional active SQLAlchemy session.
        
    Returns:
        Structured opportunities list and summary counts.
    """
    def _execute(session: Session) -> Dict[str, Any]:
        raw = detect_merchant_opportunities(session, merchant_id=merchant_id)
        opps: List[Dict[str, Any]] = raw.get("opportunities", [])
        
        # Breakdown by category
        restock_opps = [o for o in opps if o.get("type") == "RESTOCK"]
        growth_opps = [o for o in opps if o.get("type") == "DEMAND_GROWTH"]
        winback_opps = [o for o in opps if o.get("type") == "CUSTOMER_WINBACK"]
        cross_sell_opps = [o for o in opps if o.get("type") == "CROSS_SELL"]
        revenue_opps = [o for o in opps if o.get("type") == "REVENUE_OPPORTUNITY"]

        return {
            "merchant_id": merchant_id,
            "total_opportunities": len(opps),
            "opportunities": opps,
            "categories": {
                "RESTOCK": len(restock_opps),
                "DEMAND_GROWTH": len(growth_opps),
                "CUSTOMER_WINBACK": len(winback_opps),
                "CROSS_SELL": len(cross_sell_opps),
                "REVENUE_OPPORTUNITY": len(revenue_opps)
            }
        }

    if db is not None:
        return _execute(db)
    else:
        with get_db_context() as session:
            return _execute(session)
