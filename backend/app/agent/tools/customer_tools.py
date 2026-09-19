"""
Paytm Pulse - Phase 5 Agent Customer Intelligence Tools
Exposes RFM segmentation, churn risk, and customer trends from Phase 4 to the Google ADK Gemini agent.
"""

from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from app.database.connection import get_db_context
from app.intelligence.customer_intelligence import analyze_merchant_customers


def get_customer_intelligence(
    merchant_id: str,
    db: Optional[Session] = None
) -> Dict[str, Any]:
    """
    Retrieve customer segmentation, RFM metrics, active/inactive lists, and churn risk summaries for a merchant.
    
    Args:
        merchant_id: Unique merchant ID.
        db: Optional active SQLAlchemy session.
        
    Returns:
        Customer intelligence metrics dictionary.
    """
    def _execute(session: Session) -> Dict[str, Any]:
        raw = analyze_merchant_customers(session, merchant_id=merchant_id)
        customers: List[Dict[str, Any]] = raw.get("customers", [])
        
        # Categorize customers for prompt efficiency
        high_value = [c for c in customers if c.get("segment") == "HIGH_VALUE"][:5]
        frequent = [c for c in customers if c.get("segment") == "FREQUENT"][:5]
        at_risk = [c for c in customers if c.get("segment") == "AT_RISK"][:5]
        inactive = [c for c in customers if c.get("segment") == "INACTIVE"][:5]
        active = [c for c in customers if c.get("segment") == "ACTIVE"][:5]

        return {
            "merchant_id": merchant_id,
            "total_customers": int(raw.get("total_customers", 0)),
            "segments_summary": raw.get("segments_summary", {}),
            "high_value_customers": high_value,
            "frequent_customers": frequent,
            "at_risk_customers": at_risk,
            "inactive_customers": inactive,
            "active_customers": active
        }

    if db is not None:
        return _execute(db)
    else:
        with get_db_context() as session:
            return _execute(session)
