"""Unified Agent Context Builder for Google ADK / Gemini Agent.

Assembles the full fast-memory snapshot (Redis) + persistent profile (PostgreSQL)
into a rich context dictionary for LLM decision making.
"""
from typing import Dict, Any, Optional
import logging
from sqlalchemy.orm import Session

from app.memory.transaction_memory import TransactionMemory
from app.memory.alert_memory import AlertMemory
from app.memory.session_memory import SessionMemory
from app.memory.conversation_memory import ConversationMemory
from app.memory.recommendation_memory import RecommendationMemory

logger = logging.getLogger(__name__)


def build_agent_context(merchant_id: str, db: Optional[Session] = None) -> Dict[str, Any]:
    """
    Build a comprehensive context dictionary combining Redis fast memory
    and PostgreSQL permanent records.
    
    Structure:
    {
        "merchant_id": str,
        "merchant_profile": Dict,
        "session": Dict,
        "recent_transactions": List[Dict],
        "active_alerts": List[Dict],
        "active_recommendations": List[Dict],
        "recent_conversation": List[Dict],
        "summary": str
    }
    """
    context: Dict[str, Any] = {
        "merchant_id": merchant_id,
        "merchant_profile": {},
        "session": {},
        "recent_transactions": [],
        "active_alerts": [],
        "active_recommendations": [],
        "recent_conversation": [],
        "summary": ""
    }

    # 1. Fetch Session
    try:
        session_data = SessionMemory.get_session(merchant_id)
        context["session"] = session_data or {}
    except Exception as e:
        logger.warning(f"Error fetching session context for {merchant_id}: {e}")

    # 2. Fetch Recent Transactions
    try:
        txns = TransactionMemory.get_recent_transactions(merchant_id, limit=10, db=db)
        context["recent_transactions"] = txns
    except Exception as e:
        logger.warning(f"Error fetching transaction context for {merchant_id}: {e}")

    # 3. Fetch Active Alerts
    try:
        alerts = AlertMemory.get_active_alerts(merchant_id, db=db)
        context["active_alerts"] = alerts
    except Exception as e:
        logger.warning(f"Error fetching alert context for {merchant_id}: {e}")

    # 4. Fetch Active Recommendations
    try:
        recs = RecommendationMemory.list_active_recommendations(merchant_id, db=db)
        context["active_recommendations"] = recs
    except Exception as e:
        logger.warning(f"Error fetching recommendation context for {merchant_id}: {e}")

    # 5. Fetch Recent Conversation
    try:
        conv = ConversationMemory.get_recent_conversation(merchant_id, limit=6, db=db)
        context["recent_conversation"] = conv
    except Exception as e:
        logger.warning(f"Error fetching conversation context for {merchant_id}: {e}")

    # 6. Fetch Permanent Merchant Profile from DB (if db provided)
    if db:
        try:
            from app.models.merchant import Merchant
            merchant = db.query(Merchant).filter(Merchant.id == merchant_id).first()
            if merchant:
                context["merchant_profile"] = {
                    "id": str(merchant.id),
                    "name": getattr(merchant, "name", "") or getattr(merchant, "shop_name", ""),
                    "shop_name": getattr(merchant, "shop_name", "") or getattr(merchant, "name", ""),
                    "category": merchant.category.value if hasattr(merchant.category, "value") else str(merchant.category),
                    "phone": getattr(merchant, "phone", "") or getattr(merchant, "phone_number", ""),
                    "language": getattr(merchant, "language", "Hindi"),
                    "created_at": str(merchant.created_at) if merchant.created_at else None
                }
        except Exception as e:
            logger.warning(f"Error fetching merchant profile for {merchant_id}: {e}")

    # 7. Formulate Context Summary
    txn_count = len(context["recent_transactions"])
    alert_count = len(context["active_alerts"])
    rec_count = len(context["active_recommendations"])
    last_action = context["session"].get("last_action", "none")
    
    context["summary"] = (
        f"Merchant {merchant_id} context: {txn_count} recent txns in memory, "
        f"{alert_count} active alerts, {rec_count} pending recommendations. "
        f"Last session action: {last_action}."
    )

    return context
