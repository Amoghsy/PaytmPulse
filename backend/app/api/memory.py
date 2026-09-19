"""Paytm Pulse - Phase 11 Developer & Debug Memory Endpoints.

Provides REST endpoints to inspect, verify, and debug Redis-backed fast memory states
(sessions, recent transactions, active alerts, recommendations, conversation history).
"""
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.core.redis import check_redis_health, get_redis_client
from app.memory.transaction_memory import TransactionMemory
from app.memory.alert_memory import AlertMemory
from app.memory.session_memory import SessionMemory
from app.memory.conversation_memory import ConversationMemory
from app.memory.recommendation_memory import RecommendationMemory
from app.memory.cache import IntelligenceCache
from app.memory.context_builder import build_agent_context

router = APIRouter(prefix="/memory", tags=["Redis & Fast Memory"])


@router.get("/health", response_model=Dict[str, Any])
def get_memory_health() -> Dict[str, Any]:
    """Check Redis health and operational status."""
    healthy = check_redis_health()
    client = get_redis_client()
    info = {}
    if healthy and client:
        try:
            info = {
                "redis_connected": True,
                "ping": "PONG"
            }
        except Exception as e:
            info = {"redis_connected": False, "error": str(e)}
    else:
        info = {"redis_connected": False, "note": "Operating in PostgreSQL fallback mode"}

    return {
        "status": "healthy" if healthy else "degraded",
        "redis_health": info
    }


@router.get("/{merchant_id}/context", response_model=Dict[str, Any])
def get_merchant_full_context(
    merchant_id: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Retrieve full unified context (Redis fast memory + DB profile) for an agent."""
    return build_agent_context(merchant_id, db=db)


@router.get("/{merchant_id}/transactions", response_model=List[Dict[str, Any]])
def get_merchant_cached_transactions(
    merchant_id: str,
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """Retrieve recent short-term transactions cached in Redis."""
    return TransactionMemory.get_recent_transactions(merchant_id, limit=limit, db=db)


@router.get("/{merchant_id}/alerts", response_model=List[Dict[str, Any]])
def get_merchant_cached_alerts(
    merchant_id: str,
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """Retrieve active alerts stored in Redis."""
    return AlertMemory.get_active_alerts(merchant_id, db=db)


@router.get("/{merchant_id}/session", response_model=Dict[str, Any])
def get_merchant_cached_session(
    merchant_id: str
) -> Dict[str, Any]:
    """Retrieve current session state from Redis."""
    session = SessionMemory.get_session(merchant_id)
    if not session:
        return {"merchant_id": merchant_id, "session_active": False}
    return {"merchant_id": merchant_id, "session_active": True, "session": session}


@router.get("/{merchant_id}/conversation", response_model=List[Dict[str, Any]])
def get_merchant_cached_conversation(
    merchant_id: str,
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """Retrieve recent conversation turns cached in Redis."""
    return ConversationMemory.get_recent_conversation(merchant_id, limit=limit, db=db)


@router.delete("/{merchant_id}/conversation", response_model=Dict[str, Any])
def clear_merchant_cached_conversation(
    merchant_id: str
) -> Dict[str, Any]:
    """Clear active conversation history in Redis."""
    cleared = ConversationMemory.clear_conversation(merchant_id)
    return {"merchant_id": merchant_id, "conversation_cleared": cleared}


@router.get("/{merchant_id}/recommendations", response_model=List[Dict[str, Any]])
def get_merchant_cached_recommendations(
    merchant_id: str,
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """Retrieve active recommendations in Redis fast memory."""
    return RecommendationMemory.list_active_recommendations(merchant_id, db=db)
