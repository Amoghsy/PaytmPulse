import json
from typing import Optional
from sqlalchemy.orm import Session
from app.database.connection import get_db_context
from app.financial.recommendation_service import FinancialRecommendationService


def get_financial_opportunities(merchant_id: str, db: Optional[Session] = None) -> str:
    """
    Retrieve contextual simulated financial product opportunities (e.g. Working Capital, Inventory Financing)
    based on merchant inventory demand surges and business growth signals.
    Note: Products are strictly simulated demo representations.
    """
    def _execute(session: Session) -> str:
        service = FinancialRecommendationService(session)
        opp = service.get_merchant_opportunities(merchant_id)

        if not opp.opportunity_detected or not opp.recommendation:
            return json.dumps({
                "merchant_id": merchant_id,
                "opportunity_detected": False,
                "message": opp.message or "No contextual financial opportunities detected based on current business metrics."
            }, indent=2)

        rec = opp.recommendation
        return json.dumps({
            "merchant_id": merchant_id,
            "opportunity_detected": True,
            "recommendation_id": rec.id,
            "need_type": rec.need_type,
            "title": rec.title,
            "matched_product": rec.product_name,
            "reason": rec.reason,
            "supporting_signals": rec.supporting_signals,
            "simulated_amount": rec.simulated_amount,
            "simulated_duration_days": rec.duration_days,
            "confidence": rec.confidence,
            "status": rec.status
        }, indent=2)

    if db is not None:
        return _execute(db)
    else:
        with get_db_context() as session:
            return _execute(session)
