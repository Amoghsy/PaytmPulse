"""
Paytm Pulse - Phase 6 Business Decision Rules & Parameter Builders
Deterministic mathematical models for restock sizing, promotion bounding, and safety constraints.
"""

from typing import Dict, Any, Tuple
from app.decision.config import (
    DEFAULT_SAFETY_STOCK_HOURS,
    MIN_REORDER_QUANTITY,
    MAX_REORDER_QUANTITY_CAP,
    MIN_PROMOTION_DISCOUNT_PERCENT,
    MAX_PROMOTION_DISCOUNT_PERCENT,
    DEFAULT_PROMOTION_DURATION_HOURS
)


def calculate_recommended_restock_quantity(
    current_stock: int,
    reorder_level: int,
    maximum_stock: int,
    forecast_hourly_demand: float,
    average_daily_sales_units: float,
    safety_hours: float = DEFAULT_SAFETY_STOCK_HOURS
) -> int:
    """
    Computes optimal restocking batch size respecting safety stock buffers and maximum warehouse/shelf limits.
    """
    hourly_rate = max(1.0, forecast_hourly_demand, (average_daily_sales_units / 24.0) if average_daily_sales_units > 0 else 1.0)
    
    # 24 hours of operational demand + safety stock runway
    target_stock = (hourly_rate * 24.0) + (hourly_rate * safety_hours)
    
    needed = int(round(target_stock - current_stock))
    reorder_qty = max(MIN_REORDER_QUANTITY, needed)

    # Respect maximum inventory capacity if defined
    if maximum_stock > 0 and (current_stock + reorder_qty) > maximum_stock:
        reorder_qty = max(MIN_REORDER_QUANTITY, maximum_stock - current_stock)

    # Cap at configured hard ceiling
    return min(MAX_REORDER_QUANTITY_CAP, max(MIN_REORDER_QUANTITY, reorder_qty))


def build_promotion_parameters(
    product_id: str,
    product_price: float,
    suggested_discount: float = 10.0,
    duration_hours: int = DEFAULT_PROMOTION_DURATION_HOURS,
    target_segment: str = "ALL_WALK_INS"
) -> Dict[str, Any]:
    """
    Constructs bounded promotion campaign parameters.
    """
    bounded_discount = max(MIN_PROMOTION_DISCOUNT_PERCENT, min(MAX_PROMOTION_DISCOUNT_PERCENT, suggested_discount))
    effective_discount_price = round(product_price * (1.0 - (bounded_discount / 100.0)), 2)

    return {
        "product_id": product_id,
        "discount_percentage": bounded_discount,
        "original_price": product_price,
        "promotional_price": effective_discount_price,
        "duration_hours": duration_hours,
        "target_segment": target_segment
    }


def build_customer_winback_parameters(
    customer_segment: str = "AT_RISK",
    discount_percentage: float = 10.0,
    offer_type: str = "PERCENTAGE_DISCOUNT"
) -> Dict[str, Any]:
    """
    Constructs customer winback incentive parameters.
    """
    bounded_discount = max(MIN_PROMOTION_DISCOUNT_PERCENT, min(MAX_PROMOTION_DISCOUNT_PERCENT, discount_percentage))
    return {
        "customer_segment": customer_segment,
        "offer_type": offer_type,
        "discount_percentage": bounded_discount,
        "validity_days": 7
    }


def build_cross_sell_parameters(
    primary_product_id: str,
    secondary_product_id: str,
    bundle_discount_percentage: float = 5.0
) -> Dict[str, Any]:
    """
    Constructs bundle / cross-selling attachment parameters.
    """
    return {
        "primary_product_id": primary_product_id,
        "secondary_product_id": secondary_product_id,
        "bundle_type": "COMPLEMENTARY_PRODUCTS",
        "bundle_discount_percentage": bundle_discount_percentage
    }


def validate_action_parameters(action_type: str, parameters: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Guarantees action safety and rejects invalid or out-of-bounds parameters.
    """
    if action_type == "RESTOCK_PRODUCT":
        qty = parameters.get("quantity", 0)
        if not isinstance(qty, (int, float)) or qty <= 0:
            return False, f"Invalid restock quantity: {qty}. Must be positive."
        if not parameters.get("product_id"):
            return False, "Missing product_id for restock action."

    elif action_type == "RUN_PROMOTION":
        disc = parameters.get("discount_percentage", 0)
        if disc <= 0 or disc > MAX_PROMOTION_DISCOUNT_PERCENT:
            return False, f"Invalid discount percentage: {disc}%. Must be between 1% and {MAX_PROMOTION_DISCOUNT_PERCENT}%."

    elif action_type == "CUSTOMER_WINBACK":
        if not parameters.get("customer_segment"):
            return False, "Missing customer_segment in winback parameters."

    return True, "Valid"
