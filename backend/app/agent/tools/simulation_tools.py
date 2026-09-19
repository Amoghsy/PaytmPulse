"""
Paytm Pulse - Phase 5 Agent What-If Business Simulation Tools
Read-only business scenario simulator for the Google ADK Gemini agent.
"""

from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.database.connection import get_db_context
from app.models.product import Product
from app.models.customer import Customer
from app.models.transaction import Transaction
from app.intelligence.demand_forecaster import forecast_product_demand
from app.intelligence.stockout_predictor import predict_product_stockout
from app.intelligence.sales_analyzer import analyze_merchant_sales
from app.intelligence.customer_intelligence import analyze_merchant_customers


def simulate_business_action(
    merchant_id: str,
    action_type: str,
    product_id: Optional[str] = None,
    parameters: Optional[Dict[str, Any]] = None,
    db: Optional[Session] = None
) -> Dict[str, Any]:
    """
    Simulate the projected business and financial impact of a potential merchant action without executing it.
    Strictly read-only and uses actual project data and ML models.
    
    Supported action_type values:
      - RESTOCK_PRODUCT / RESTOCK
      - RUN_PROMOTION / LAUNCH_PROMOTION
      - CUSTOMER_WINBACK
      - CREATE_BUNDLE
      - ADJUST_OFFER
      - MONITOR_TREND
      - DO_NOTHING
      
    Args:
        merchant_id: Unique merchant identifier.
        action_type: Business action to simulate.
        product_id: Optional product identifier for product-specific actions.
        parameters: Optional dictionary of scenario parameters (e.g. quantity, discount_percent, horizon).
        db: Optional active SQLAlchemy session.
        
    Returns:
        Structured simulation response with predicted impact, assumptions, and executed=False.
    """
    params = parameters or {}
    action_upper = action_type.strip().upper()

    def _execute(session: Session) -> Dict[str, Any]:
        # Normalise action type aliases
        if action_upper in ["RESTOCK_PRODUCT", "RESTOCK"]:
            return _simulate_restock(session, merchant_id, product_id, params)
        elif action_upper in ["RUN_PROMOTION", "LAUNCH_PROMOTION", "PROMOTION"]:
            return _simulate_promotion(session, merchant_id, product_id, params)
        elif action_upper in ["CUSTOMER_WINBACK", "WINBACK"]:
            return _simulate_customer_winback(session, merchant_id, params)
        elif action_upper in ["CREATE_BUNDLE", "BUNDLE"]:
            return _simulate_bundle(session, merchant_id, product_id, params)
        elif action_upper in ["ADJUST_OFFER", "OFFER"]:
            return _simulate_adjust_offer(session, merchant_id, params)
        elif action_upper in ["DO_NOTHING", "INACTION"]:
            return _simulate_do_nothing(session, merchant_id, product_id, params)
        else: # MONITOR_TREND or default
            return _simulate_monitor(session, merchant_id, product_id, params)

    if db is not None:
        return _execute(db)
    else:
        with get_db_context() as session:
            return _execute(session)


def _simulate_restock(session: Session, merchant_id: str, product_id: Optional[str], params: Dict[str, Any]) -> Dict[str, Any]:
    """Simulates restocking a product."""
    product = None
    if product_id:
        product = session.query(Product).filter(Product.id == product_id, Product.merchant_id == merchant_id).first()
    
    if not product:
        # Pick the most vulnerable product for this merchant if not provided
        stockouts = predict_product_stockout(session, merchant_id=merchant_id, product_id=product_id) if product_id else None
        product = session.query(Product).filter(Product.merchant_id == merchant_id, Product.is_active == True).first()

    if not product:
        return {
            "action_type": "RESTOCK_PRODUCT",
            "merchant_id": merchant_id,
            "product_id": product_id,
            "status": "INSUFFICIENT_DATA",
            "message": f"No active product found for merchant '{merchant_id}' to simulate restock.",
            "executed": False
        }

    # Gather real forecasting and stockout metrics
    stockout_data = predict_product_stockout(session, merchant_id=merchant_id, product_id=str(product.id))
    forecast_data = forecast_product_demand(session, merchant_id=merchant_id, product_id=str(product.id))

    current_stock = stockout_data.get("current_stock", product.current_stock)
    unit_price = float(product.price)
    cost_price = float(product.cost_price or (unit_price * 0.75))
    hourly_demand = max(0.1, float(stockout_data.get("forecast_hourly_demand") or stockout_data.get("average_hourly_demand") or 1.0))
    
    reorder_qty = int(params.get("quantity") or max(24, int(hourly_demand * 12)))
    hours_runway_current = float(stockout_data.get("estimated_hours_to_stockout", 1.0))
    hours_runway_after = round(hours_runway_current + (reorder_qty / hourly_demand), 1)

    # Calculate prevented lost sales
    # If current runway is < 4 hours, without restock we lose (4 - runway) * hourly_demand sales
    unmet_demand_units = max(0.0, (12.0 - min(12.0, hours_runway_current)) * hourly_demand)
    protected_units = min(float(reorder_qty), unmet_demand_units)
    estimated_revenue_protected = round(protected_units * unit_price, 2)
    reorder_cost = round(reorder_qty * cost_price, 2)
    expected_profit_protected = round(protected_units * (unit_price - cost_price), 2)

    confidence = min(0.95, max(0.60, 0.70 + (0.1 if current_stock > 0 else 0.0) + (0.1 if hourly_demand > 0 else 0.0)))

    return {
        "action_type": "RESTOCK_PRODUCT",
        "merchant_id": merchant_id,
        "product_id": str(product.id),
        "product_name": product.name,
        "inputs": {
            "reorder_quantity": reorder_qty,
            "unit_price": unit_price,
            "unit_cost": cost_price
        },
        "assumptions": [
            f"Forecasted hourly demand continues at {hourly_demand:.1f} units/hour",
            f"Stock replenishment arrives before total stock depletion ({hours_runway_current}h runway)",
            "Supplier pricing remains at regular wholesale tier"
        ],
        "predicted_impact": {
            "type": "POTENTIAL_REVENUE_LOSS_PREVENTED",
            "estimated_value": estimated_revenue_protected,
            "gross_profit_protected": expected_profit_protected,
            "reorder_capital_required": reorder_cost,
            "currency": "INR"
        },
        "inventory_implications": {
            "current_stock": current_stock,
            "projected_post_restock_stock": current_stock + reorder_qty,
            "current_runway_hours": hours_runway_current,
            "projected_runway_hours": hours_runway_after
        },
        "demand_implications": {
            "hourly_demand_velocity": round(hourly_demand, 2),
            "forecast_horizon": "next_12_hours"
        },
        "stockout_implications": {
            "stockout_prevented": True,
            "unmet_demand_without_restock_units": round(unmet_demand_units, 1)
        },
        "confidence": round(confidence, 2),
        "executed": False,
        "status": "SIMULATED_ONLY"
    }


def _simulate_promotion(session: Session, merchant_id: str, product_id: Optional[str], params: Dict[str, Any]) -> Dict[str, Any]:
    """Simulates launching a promotional discount or flash offer."""
    discount_pct = float(params.get("discount_percentage", 10.0))
    duration_hours = int(params.get("duration_hours", 4))

    sales_raw = analyze_merchant_sales(session, merchant_id=merchant_id, days=14)
    avg_daily_sales = float(sales_raw.get("sales", {}).get("average_daily_sales", 0.0))
    baseline_hourly_revenue = avg_daily_sales / 12.0 if avg_daily_sales > 0 else 100.0

    # Elasticity assumption: 10% discount yields ~25% volume increase for FMCG/retail
    volume_lift_factor = 1.0 + ((discount_pct / 10.0) * 0.25)
    effective_price_factor = 1.0 - (discount_pct / 100.0)
    
    projected_revenue_lift = round(baseline_hourly_revenue * duration_hours * ((volume_lift_factor * effective_price_factor) - 1.0), 2)
    # Ensure positive growth projection if volume offset is net positive
    net_revenue_change = max(0.0, projected_revenue_lift)

    return {
        "action_type": "RUN_PROMOTION",
        "merchant_id": merchant_id,
        "product_id": product_id,
        "inputs": {
            "discount_percentage": discount_pct,
            "duration_hours": duration_hours
        },
        "assumptions": [
            f"Price elasticity yields {((volume_lift_factor - 1.0) * 100):.1f}% volume lift during promotion",
            f"Promotion is active for {duration_hours} peak store hours"
        ],
        "predicted_impact": {
            "type": "REVENUE_GROWTH",
            "estimated_value": net_revenue_change,
            "projected_volume_lift_pct": round((volume_lift_factor - 1.0) * 100, 1),
            "currency": "INR"
        },
        "inventory_implications": {
            "inventory_drain_accelerated": True,
            "recommended_buffer_stock": "Ensure adequate inventory before launching promotion"
        },
        "demand_implications": {
            "baseline_hourly_revenue": round(baseline_hourly_revenue, 2),
            "projected_promotion_hourly_revenue": round(baseline_hourly_revenue * volume_lift_factor * effective_price_factor, 2)
        },
        "stockout_implications": {
            "risk_increased": True
        },
        "confidence": 0.82,
        "executed": False,
        "status": "SIMULATED_ONLY"
    }


def _simulate_customer_winback(session: Session, merchant_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Simulates sending a re-engagement offer to at-risk and inactive customers."""
    cust_data = analyze_merchant_customers(session, merchant_id=merchant_id)
    customers = cust_data.get("customers", [])
    at_risk = [c for c in customers if c.get("segment") in ["AT_RISK", "INACTIVE"]]
    
    target_count = len(at_risk) if at_risk else 5
    avg_customer_spend = float(sum(c.get("total_spend", 0.0) for c in at_risk) / max(len(at_risk), 1)) if at_risk else 350.0

    # Re-engagement response rate assumption: ~25% of targeted at-risk customers return
    expected_reactivation_rate = 0.25
    expected_reengaged_customers = max(1, int(round(target_count * expected_reactivation_rate)))
    projected_recovered_revenue = round(expected_reengaged_customers * avg_customer_spend * 0.8, 2)

    return {
        "action_type": "CUSTOMER_WINBACK",
        "merchant_id": merchant_id,
        "product_id": None,
        "inputs": {
            "target_segment": "AT_RISK_AND_INACTIVE",
            "target_customer_count": target_count,
            "average_historical_spend": round(avg_customer_spend, 2)
        },
        "assumptions": [
            f"Expected re-engagement coupon redemption rate of {expected_reactivation_rate * 100:.0f}%",
            f"Average order value for returning customer matches baseline (₹{avg_customer_spend:.2f})"
        ],
        "predicted_impact": {
            "type": "CUSTOMER_RETENTION_REVENUE",
            "estimated_value": projected_recovered_revenue,
            "projected_reactivated_customers": expected_reengaged_customers,
            "currency": "INR"
        },
        "inventory_implications": {
            "inventory_impact": "Standard catalog rotation"
        },
        "demand_implications": {
            "repeat_footfall_increase": f"+{expected_reengaged_customers} visits over next 7 days"
        },
        "stockout_implications": {
            "risk_increased": False
        },
        "confidence": 0.78,
        "executed": False,
        "status": "SIMULATED_ONLY"
    }


def _simulate_bundle(session: Session, merchant_id: str, product_id: Optional[str], params: Dict[str, Any]) -> Dict[str, Any]:
    """Simulates creating a cross-sell product bundle."""
    products = session.query(Product).filter(Product.merchant_id == merchant_id, Product.is_active == True).limit(2).all()
    if len(products) < 2:
        return {
            "action_type": "CREATE_BUNDLE",
            "merchant_id": merchant_id,
            "status": "INSUFFICIENT_DATA",
            "message": "At least 2 active products are required to simulate a bundle.",
            "executed": False
        }
    
    p1, p2 = products[0], products[1]
    combined_price = float(p1.price + p2.price)
    discount_pct = float(params.get("bundle_discount_pct", 8.0))
    bundle_price = round(combined_price * (1.0 - (discount_pct / 100.0)), 2)
    projected_weekly_units = int(params.get("projected_weekly_bundles", 15))
    incremental_revenue = round(projected_weekly_units * bundle_price * 0.35, 2)

    return {
        "action_type": "CREATE_BUNDLE",
        "merchant_id": merchant_id,
        "product_id": str(p1.id),
        "inputs": {
            "product_a": p1.name,
            "product_b": p2.name,
            "bundle_price": bundle_price,
            "discount_percentage": discount_pct
        },
        "assumptions": [
            f"Bundle cross-selling increases average basket size by ₹{bundle_price - float(p1.price):.2f}",
            f"Projected uptake: {projected_weekly_units} bundle purchases per week"
        ],
        "predicted_impact": {
            "type": "REVENUE_GROWTH",
            "estimated_value": incremental_revenue,
            "currency": "INR"
        },
        "inventory_implications": {
            "synchronized_depletion": f"{p1.name} and {p2.name} inventory will deplete simultaneously"
        },
        "demand_implications": {
            "basket_size_increase_pct": round((bundle_price / float(p1.price) - 1.0) * 100, 1)
        },
        "stockout_implications": {
            "risk_increased": False
        },
        "confidence": 0.75,
        "executed": False,
        "status": "SIMULATED_ONLY"
    }


def _simulate_adjust_offer(session: Session, merchant_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Simulates adjusting an existing merchant discount offer."""
    curr_discount = float(params.get("current_discount", 10.0))
    new_discount = float(params.get("new_discount", 15.0))
    sales_raw = analyze_merchant_sales(session, merchant_id=merchant_id, days=7)
    today_sales = float(sales_raw.get("sales", {}).get("today", 0.0))

    marginal_gain = round(today_sales * (new_discount - curr_discount) * 0.015, 2)

    return {
        "action_type": "ADJUST_OFFER",
        "merchant_id": merchant_id,
        "inputs": {
            "current_discount": curr_discount,
            "new_discount": new_discount
        },
        "assumptions": [
            f"Offer adjustment from {curr_discount}% to {new_discount}% stimulates additional marginal conversions"
        ],
        "predicted_impact": {
            "type": "REVENUE_GROWTH",
            "estimated_value": max(100.0, marginal_gain),
            "currency": "INR"
        },
        "inventory_implications": {},
        "demand_implications": {},
        "stockout_implications": {},
        "confidence": 0.70,
        "executed": False,
        "status": "SIMULATED_ONLY"
    }


def _simulate_do_nothing(session: Session, merchant_id: str, product_id: Optional[str], params: Dict[str, Any]) -> Dict[str, Any]:
    """Simulates the cost of inaction if current trends / stockout risk continue without intervention."""
    product = None
    if product_id:
        product = session.query(Product).filter(Product.id == product_id, Product.merchant_id == merchant_id).first()
    if not product:
        product = session.query(Product).filter(Product.merchant_id == merchant_id, Product.is_active == True).first()

    if not product:
        return {
            "action_type": "DO_NOTHING",
            "merchant_id": merchant_id,
            "status": "INSUFFICIENT_DATA",
            "message": "No product data available to simulate inaction cost.",
            "executed": False
        }

    stockout_data = predict_product_stockout(session, merchant_id=merchant_id, product_id=str(product.id))
    hourly_demand = max(0.1, float(stockout_data.get("forecast_hourly_demand") or 1.0))
    runway_hours = float(stockout_data.get("estimated_hours_to_stockout", 1.0))
    unit_price = float(product.price)

    # Opportunity cost of inaction: If stock runs out, lost sales over remainder of operating window
    hours_stockout = max(0.0, 10.0 - runway_hours)
    lost_revenue = round(hours_stockout * hourly_demand * unit_price, 2)

    return {
        "action_type": "DO_NOTHING",
        "merchant_id": merchant_id,
        "product_id": str(product.id),
        "product_name": product.name,
        "inputs": {},
        "assumptions": [
            "Current demand rate continues without any merchant intervention",
            f"Inventory exhausts in {runway_hours} hours leading to zero sales during stockout period"
        ],
        "predicted_impact": {
            "type": "POTENTIAL_REVENUE_LOSS",
            "estimated_value": lost_revenue,
            "lost_operating_hours": round(hours_stockout, 1),
            "currency": "INR"
        },
        "inventory_implications": {
            "current_stock": stockout_data.get("current_stock", product.current_stock),
            "projected_exhaustion_hours": runway_hours
        },
        "demand_implications": {
            "unserved_demand_units": round(hours_stockout * hourly_demand, 1)
        },
        "stockout_implications": {
            "stockout_will_occur": runway_hours < 8.0,
            "hours_to_stockout": runway_hours
        },
        "confidence": 0.85,
        "executed": False,
        "status": "SIMULATED_ONLY"
    }


def _simulate_monitor(session: Session, merchant_id: str, product_id: Optional[str], params: Dict[str, Any]) -> Dict[str, Any]:
    """Simulates monitoring store signals without active intervention."""
    return {
        "action_type": "MONITOR_TREND",
        "merchant_id": merchant_id,
        "product_id": product_id,
        "inputs": {},
        "assumptions": [
            "Continuous telemetry observation without inventory or promotion adjustments"
        ],
        "predicted_impact": {
            "type": "OPERATIONAL_STABILITY",
            "estimated_value": 0.0,
            "currency": "INR"
        },
        "inventory_implications": {
            "state": "Unchanged"
        },
        "demand_implications": {
            "state": "Tracking realtime trends"
        },
        "stockout_implications": {
            "state": "Monitored"
        },
        "confidence": 0.90,
        "executed": False,
        "status": "SIMULATED_ONLY"
    }
