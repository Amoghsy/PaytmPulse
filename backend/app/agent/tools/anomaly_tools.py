"""
Paytm Pulse - Phase 5 Agent Anomaly Detection Tools
Exposes anomaly detection from Phase 4 to the Google ADK Gemini agent.
"""

from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.database.connection import get_db_context
from app.intelligence.anomaly_detector import detect_sales_anomalies, detect_product_anomalies


def detect_anomalies(
    merchant_id: str,
    product_id: Optional[str] = None,
    db: Optional[Session] = None
) -> Dict[str, Any]:
    """
    Detect statistical and ML-based demand spikes, sales drops, or revenue anomalies for a merchant or specific product.
    
    Args:
        merchant_id: Unique merchant ID.
        product_id: Optional product ID to inspect product-specific anomalies.
        db: Optional active SQLAlchemy session.
        
    Returns:
        Anomaly detection result dictionary.
    """
    def _execute(session: Session) -> Dict[str, Any]:
        if product_id:
            raw = detect_product_anomalies(session, merchant_id=merchant_id, product_id=product_id)
        else:
            raw = detect_sales_anomalies(session, merchant_id=merchant_id)
            
        return {
            "merchant_id": merchant_id,
            "product_id": product_id,
            "anomaly_detected": bool(raw.get("anomaly_detected", False)),
            "type": str(raw.get("type", "NONE")),
            "severity": str(raw.get("severity", "LOW")),
            "confidence": float(raw.get("confidence", 0.0)),
            "observed_value": float(raw.get("observed_value", 0.0)),
            "baseline_value": float(raw.get("baseline_value", 0.0)),
            "explanation": str(raw.get("explanation", ""))
        }

    if db is not None:
        return _execute(db)
    else:
        with get_db_context() as session:
            return _execute(session)
