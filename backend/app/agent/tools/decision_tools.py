"""
Paytm Pulse - Phase 6 Agent Decision Tools
Exposes Decision Engine next best action evaluation to Google ADK / Gemini agent.
"""

from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.database.connection import get_db_context


def generate_next_best_actions(
    merchant_id: str,
    event_id: Optional[str] = None,
    db: Optional[Session] = None
) -> Dict[str, Any]:
    """
    Generate and prioritize candidate actions for a merchant or specific event using the Decision Engine.
    
    Args:
        merchant_id: Unique merchant ID.
        event_id: Optional BusinessEvent ID.
        db: Optional active SQLAlchemy session.
        
    Returns:
        Structured dictionary containing Next Best Action and alternative ranked actions.
    """
    def _execute(session: Session) -> Dict[str, Any]:
        from app.decision.engine import DecisionEngine
        engine = DecisionEngine(session)
        decision_resp = engine.generate_decision(merchant_id=merchant_id, event_id=event_id)
        return decision_resp.model_dump()

    if db is not None:
        return _execute(db)
    else:
        with get_db_context() as session:
            return _execute(session)
