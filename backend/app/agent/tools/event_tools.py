"""
Paytm Pulse - Phase 5 Agent Business Event Tools
Inspects Phase 3 real-time business events for Google ADK Gemini agent reasoning.
"""

from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.database.connection import get_db_context
from app.models.business_event import BusinessEvent


def get_business_event(
    event_id: str,
    db: Optional[Session] = None
) -> Dict[str, Any]:
    """
    Retrieve real-time business event payload, trigger severity, source, and associated metadata.
    
    Args:
        event_id: Unique BusinessEvent ID.
        db: Optional active SQLAlchemy session.
        
    Returns:
        Structured business event dictionary.
    """
    def _execute(session: Session) -> Dict[str, Any]:
        event = session.query(BusinessEvent).filter(BusinessEvent.id == event_id).first()
        if not event:
            return {
                "event_id": event_id,
                "found": False,
                "error": f"Business event '{event_id}' not found"
            }
        
        payload = event.payload or {}
        product_id = payload.get("product_id")
        
        return {
            "event_id": str(event.id),
            "found": True,
            "event_type": str(event.event_type.value if hasattr(event.event_type, "value") else event.event_type),
            "merchant_id": str(event.merchant_id),
            "product_id": product_id,
            "severity": str(event.severity.value if hasattr(event.severity, "value") else event.severity),
            "source": str(event.source),
            "detected_at": event.detected_at.isoformat() if event.detected_at else None,
            "payload": payload
        }

    if db is not None:
        return _execute(db)
    else:
        with get_db_context() as session:
            return _execute(session)
