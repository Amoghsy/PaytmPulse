"""
Paytm Pulse - Phase 6 Business Impact Estimator
Calculates estimated monetary impact for candidate merchant actions.
"""

from typing import Dict, Any, Optional
from app.decision.schemas import EstimatedImpact


def estimate_stockout_protection_impact(
    product_price: float,
    current_stock: int,
    forecast_hourly_demand: float,
    hours_runway: float
) -> EstimatedImpact:
    """
    Estimates potential revenue protected by preventing a stockout during high demand.
    Formula: Forecasted units at risk * Unit Price
    """
    # Units at risk over the next 12-24 hours after inventory depletion
    shortage_hours = max(0.0, 12.0 - max(0.0, hours_runway))
    units_at_risk = round(shortage_hours * max(1.0, forecast_hourly_demand))
    units_to_protect = max(5, units_at_risk)
    value = round(units_to_protect * max(10.0, product_price), 2)
    
    return EstimatedImpact(
        type="REVENUE_PROTECTED",
        value=value,
        currency="INR",
        details=f"Estimated {units_to_protect} units protected at ₹{product_price:.2f}/unit."
    )


def estimate_promotion_impact(
    product_price: float,
    average_daily_sales: float,
    discount_percentage: float,
    duration_hours: int = 6
) -> EstimatedImpact:
    """
    Estimates incremental gross revenue from a targeted promotional campaign.
    """
    # Expected demand elasticity: ~1.5x lift on discounted volume
    hourly_rate = (average_daily_sales / 24.0) if average_daily_sales > 0 else 2.0
    incremental_units = round(hourly_rate * duration_hours * 1.5)
    effective_price = product_price * (1.0 - (discount_percentage / 100.0))
    value = round(incremental_units * effective_price, 2)

    return EstimatedImpact(
        type="INCREMENTAL_REVENUE",
        value=max(200.0, value),
        currency="INR",
        details=f"Estimated {incremental_units} incremental units sold with {discount_percentage:.0f}% discount over {duration_hours}h."
    )


def estimate_customer_winback_impact(
    at_risk_customers_count: int,
    avg_customer_historical_spend: float
) -> EstimatedImpact:
    """
    Estimates recovered revenue from re-engaging churn-risk customers.
    Assumes a realistic 20-30% recovery conversion rate.
    """
    target_count = max(1, at_risk_customers_count)
    avg_spend = max(500.0, avg_customer_historical_spend)
    estimated_recovered_value = round(target_count * avg_spend * 0.25, 2)

    return EstimatedImpact(
        type="RECOVERED_REVENUE",
        value=estimated_recovered_value,
        currency="INR",
        details=f"Estimated 25% recovery on {target_count} at-risk customer(s) with baseline spend ₹{avg_spend:.2f}."
    )


def estimate_cross_sell_impact(
    primary_price: float,
    paired_price: float,
    weekly_frequency: int = 15
) -> EstimatedImpact:
    """
    Estimates incremental basket expansion revenue from cross-selling complementary products.
    """
    expected_pair_attachments = max(5, int(weekly_frequency * 0.30))
    bundle_incremental = round(expected_pair_attachments * paired_price, 2)

    return EstimatedImpact(
        type="INCREMENTAL_REVENUE",
        value=bundle_incremental,
        currency="INR",
        details=f"Estimated {expected_pair_attachments} add-on purchases of secondary product at ₹{paired_price:.2f}."
    )


def estimate_trend_monitoring_impact(daily_sales: float) -> EstimatedImpact:
    """
    General trend monitoring baseline impact.
    """
    value = round(max(100.0, daily_sales * 0.05), 2)
    return EstimatedImpact(
        type="OPERATIONAL_EFFICIENCY",
        value=value,
        currency="INR",
        details="Gains from active operational monitoring and loss prevention."
    )
