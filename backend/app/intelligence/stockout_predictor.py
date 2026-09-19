import logging
from sqlalchemy.orm import Session

from app.models.inventory import Inventory
from app.models.product import Product
from app.intelligence.data_loader import load_inventory_data, load_hourly_aggregation
from app.intelligence.demand_forecaster import forecast_product_demand
from app.intelligence.config import STOCKOUT_CRITICAL_HOURS, STOCKOUT_HIGH_HOURS, STOCKOUT_MEDIUM_HOURS

logger = logging.getLogger("paytm_pulse.intelligence.stockout_predictor")


def predict_product_stockout(session: Session, merchant_id: str, product_id: str) -> dict:
    """
    Predicts stockout risk and estimated time to stockout for a specific product.
    Combines live inventory stock with forecasted and historical consumption rates.
    """
    prod = session.query(Product).filter(Product.id == product_id, Product.merchant_id == merchant_id).first()
    if not prod:
        return {
            "product_id": product_id,
            "product_name": "Unknown",
            "current_stock": 0,
            "average_hourly_demand": 0.0,
            "forecast_hourly_demand": 0.0,
            "estimated_hours_to_stockout": 0.0,
            "estimated_minutes_to_stockout": 0,
            "stockout_risk": "UNKNOWN",
            "reorder_recommended": False
        }

    inv = session.query(Inventory).filter(Inventory.product_id == product_id).first()
    current_stock = inv.current_stock if inv else 0
    reorder_level = inv.reorder_level if inv else 10
    max_stock = inv.maximum_stock if inv else 100

    # Retrieve forecast
    fc = forecast_product_demand(session, merchant_id, product_id)
    forecast_hourly = float(fc.get("forecast_next_hour", 0.0))
    baseline_hourly = float(fc.get("baseline_demand", 0.0))

    # Determine consumption rate (prioritize active forecast, fallback to baseline or min velocity)
    consumption_rate = max(forecast_hourly, baseline_hourly)

    if current_stock <= 0:
        est_hours = 0.0
        risk = "CRITICAL"
    elif consumption_rate > 0:
        est_hours = round(current_stock / consumption_rate, 1)
        if est_hours <= STOCKOUT_CRITICAL_HOURS:
            risk = "CRITICAL"
        elif est_hours <= STOCKOUT_HIGH_HOURS:
            risk = "HIGH"
        elif est_hours <= STOCKOUT_MEDIUM_HOURS or current_stock <= reorder_level:
            risk = "MEDIUM"
        else:
            risk = "LOW"
    else:
        est_hours = 999.0
        risk = "LOW"

    est_minutes = int(est_hours * 60)
    reorder_recommended = (risk in ["CRITICAL", "HIGH", "MEDIUM"]) or (current_stock <= reorder_level)
    reorder_qty = max(0, max_stock - current_stock) if reorder_recommended else 0

    return {
        "product_id": product_id,
        "product_name": prod.name,
        "current_stock": current_stock,
        "reorder_level": reorder_level,
        "average_hourly_demand": round(baseline_hourly, 2),
        "forecast_hourly_demand": round(forecast_hourly, 2),
        "estimated_hours_to_stockout": est_hours,
        "estimated_minutes_to_stockout": est_minutes,
        "stockout_risk": risk,
        "reorder_recommended": reorder_recommended,
        "reorder_quantity_suggested": reorder_qty
    }


def predict_merchant_stockouts(session: Session, merchant_id: str) -> list[dict]:
    """
    Evaluates stockout risk across all active products for a merchant, sorted by urgency.
    """
    products = session.query(Product).filter(
        Product.merchant_id == merchant_id,
        Product.is_active.is_(True)
    ).all()

    results = []
    for prod in products:
        pred = predict_product_stockout(session, merchant_id, prod.id)
        results.append(pred)

    risk_rank = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "UNKNOWN": 4}
    results.sort(key=lambda x: (risk_rank.get(x["stockout_risk"], 5), x["estimated_hours_to_stockout"]))
    return results
