"""Paytm Pulse - Phase 11 Agent Memory Tools.

Exposes fast Redis memory snapshot and short-term operational context
to the Google ADK / Gemini agent.
"""
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.database.connection import get_db_context
from app.memory.context_builder import build_agent_context


def get_recent_merchant_context(
    merchant_id: str,
    db: Optional[Session] = None
) -> Dict[str, Any]:
    """
    Retrieve the current fast-memory snapshot for a merchant from Redis (and DB fallback),
    including active session state, recent transactions, unhandled alerts,
    pending recommendations, and recent conversation turns.
    
    Args:
        merchant_id: Unique merchant identifier.
        db: Optional SQLAlchemy database session.
        
    Returns:
        Structured context dictionary containing recent operational memory.
    """
    def _execute(session: Session) -> Dict[str, Any]:
        return build_agent_context(merchant_id, db=session)

    if db is not None:
        return _execute(db)
    else:
        with get_db_context() as session:
            return _execute(session)
