import logging
from sqlalchemy.orm import Session

from app.models.business_event import BusinessEvent, EventType
from app.intelligence.anomaly_detector import detect_sales_anomalies, detect_product_anomalies
from app.intelligence.demand_forecaster import forecast_product_demand
from app.intelligence.stockout_predictor import predict_product_stockout, predict_merchant_stockouts
from app.intelligence.opportunity_detector import detect_merchant_opportunities

logger = logging.getLogger("paytm_pulse.intelligence.event_analyzer")


def analyze_business_event(session: Session, event_id: str) -> dict:
    """
    Enriches a Phase 3 BusinessEvent with deep ML Intelligence (anomaly score, demand forecast, stockout prediction, and revenue exposure).
    """
    event = session.query(BusinessEvent).filter(BusinessEvent.id == event_id).first()
    if not event:
        return {"error": f"BusinessEvent with ID '{event_id}' not found."}

    m_id = event.merchant_id
    payload = event.payload or {}
    product_id = payload.get("product_id")

    # 1. Anomaly Intelligence
    if product_id:
        anomaly_info = detect_product_anomalies(session, m_id, product_id)
    else:
        anomaly_info = detect_sales_anomalies(session, m_id)

    # 2. Demand Forecast
    if product_id:
        forecast_info = forecast_product_demand(session, m_id, product_id)
    else:
        forecast_info = {"status": "merchant_level_event", "details": "Product-specific forecast not applicable"}

    # 3. Stockout Risk Assessment
    if product_id:
        stockout_info = predict_product_stockout(session, m_id, product_id)
    else:
        stockout_info = predict_merchant_stockouts(session, m_id)

    # 4. Revenue Exposure Calculation
    revenue_exposure = 0.0
    if product_id and isinstance(stockout_info, dict):
        unit_price = float(payload.get("unit_price", 50.0))
        reorder_qty = stockout_info.get("reorder_quantity_suggested", 0)
        revenue_exposure = round(reorder_qty * unit_price, 2)
    elif event.event_type == EventType.SALES_DECLINE:
        prev_sales = float(payload.get("previous_7d_sales", 0.0))
        curr_sales = float(payload.get("recent_7d_sales", 0.0))
        revenue_exposure = round(max(0.0, prev_sales - curr_sales), 2)

    # 5. Associated Opportunities
    all_opps = detect_merchant_opportunities(session, m_id)
    relevant_opps = [
        opp for opp in all_opps.get("opportunities", [])
        if (product_id and opp.get("product_id") == product_id) or opp["type"] in ["RESTOCK", "REVENUE_OPPORTUNITY"]
    ]

    return {
        "event_id": event.id,
        "merchant_id": m_id,
        "event_type": event.event_type.value if hasattr(event.event_type, "value") else str(event.event_type),
        "severity": event.severity.value if hasattr(event.severity, "value") else str(event.severity),
        "detected_at": event.detected_at.isoformat() if event.detected_at else None,
        "analysis": {
            "anomaly": anomaly_info,
            "forecast": forecast_info,
            "inventory": stockout_info,
            "expected_revenue_exposure": revenue_exposure,
            "opportunities": relevant_opps[:2]
        }
    }
