import json
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.database.connection import get_db_context
from app.outcomes.service import OutcomeService


def get_action_outcome(action_id: str, db: Optional[Session] = None) -> str:
    """
    Retrieve the measured closed-loop business outcome for a specific action ID.
    Returns impact, revenue change, stockout prevention status, and learning summary.
    """
    def _execute(session: Session) -> str:
        service = OutcomeService(session)
        outcome = service.get_outcome_by_action(action_id)
        if not outcome:
            return json.dumps({
                "status": "UNMEASURED_OR_NOT_FOUND",
                "message": f"No outcome recorded yet for action '{action_id}'."
            })
        
        return json.dumps({
            "action_id": outcome.action_id,
            "outcome_type": outcome.outcome_type,
            "impact": outcome.impact,
            "status": outcome.status,
            "confidence": outcome.confidence,
            "sales_before": outcome.sales_before,
            "sales_after": outcome.sales_after,
            "revenue_change": outcome.revenue_change,
            "stockout_prevented": outcome.stockout_prevented,
            "customers_recovered": outcome.customers_recovered,
            "offer_conversion": outcome.offer_conversion,
            "learning_signal": outcome.learning_signals.get("signal") if outcome.learning_signals else None,
            "measured_at": outcome.measured_at.isoformat() if outcome.measured_at else None
        }, indent=2)

    if db is not None:
        return _execute(db)
    else:
        with get_db_context() as session:
            return _execute(session)


def get_action_history(merchant_id: str, limit: int = 5, db: Optional[Session] = None) -> str:
    """
    Retrieve previous executed actions and their measured business outcomes for a merchant.
    Use this to understand past successes and failures before recommending new actions.
    """
    def _execute(session: Session) -> str:
        service = OutcomeService(session)
        outcomes = service.get_merchant_outcomes(merchant_id, limit=limit)
        summary = service.get_merchant_summary(merchant_id)

        return json.dumps({
            "merchant_id": merchant_id,
            "total_actions_executed": summary.actions_executed,
            "positive_outcomes": summary.positive_outcomes,
            "neutral_outcomes": summary.neutral_outcomes,
            "negative_outcomes": summary.negative_outcomes,
            "recent_outcomes": [
                {
                    "action_id": o.action_id,
                    "outcome_type": o.outcome_type,
                    "impact": o.impact,
                    "revenue_change": o.revenue_change,
                    "stockout_prevented": o.stockout_prevented,
                    "customers_recovered": o.customers_recovered
                }
                for o in outcomes
            ]
        }, indent=2)

    if db is not None:
        return _execute(db)
    else:
        with get_db_context() as session:
            return _execute(session)

