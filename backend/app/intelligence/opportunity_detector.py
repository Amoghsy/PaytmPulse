import logging
from sqlalchemy.orm import Session

from app.intelligence.sales_analyzer import analyze_merchant_sales
from app.intelligence.stockout_predictor import predict_merchant_stockouts
from app.intelligence.customer_intelligence import analyze_merchant_customers
from app.intelligence.data_loader import load_product_sales

logger = logging.getLogger("paytm_pulse.intelligence.opportunity_detector")


def detect_merchant_opportunities(session: Session, merchant_id: str) -> dict:
    """
    Scans sales patterns, inventory risks, customer segments, and product pairs
    to detect structured revenue, restocking, cross-sell, and retention opportunities.
    """
    opportunities = []

    # 1. RESTOCK & REVENUE Opportunities (from Stockout Predictor)
    stockouts = predict_merchant_stockouts(session, merchant_id)
    for item in stockouts:
        if item["stockout_risk"] in ["CRITICAL", "HIGH"]:
            opportunities.append({
                "type": "RESTOCK",
                "product_id": item["product_id"],
                "product_name": item["product_name"],
                "priority": "HIGH" if item["stockout_risk"] == "CRITICAL" else "MEDIUM",
                "reason": f"High stockout risk for '{item['product_name']}': Stock ({item['current_stock']}) will run out in approx {item['estimated_hours_to_stockout']}h.",
                "potential_revenue_impact": round(item["reorder_quantity_suggested"] * item.get("forecast_hourly_demand", 1.0) * 50.0, 2),
                "details": {
                    "current_stock": item["current_stock"],
                    "reorder_quantity": item["reorder_quantity_suggested"],
                    "estimated_hours_to_stockout": item["estimated_hours_to_stockout"]
                }
            })

    # 2. DEMAND_GROWTH Opportunities (from Top Selling & Rising Products)
    sales_info = analyze_merchant_sales(session, merchant_id)
    top_products = sales_info.get("top_products", [])
    if top_products:
        top_item = top_products[0]
        opportunities.append({
            "type": "DEMAND_GROWTH",
            "product_id": top_item["product_id"],
            "product_name": top_item["product_name"],
            "priority": "MEDIUM",
            "reason": f"Strong demand growth for #{1} best seller '{top_item['product_name']}': {top_item['units_sold']} units sold recently.",
            "potential_revenue_impact": round(float(top_item["revenue"]) * 0.20, 2),
            "details": {
                "units_sold": top_item["units_sold"],
                "revenue": float(top_item["revenue"])
            }
        })

    # 3. CUSTOMER_WINBACK Opportunities (from At-Risk High Value Customers)
    cust_info = analyze_merchant_customers(session, merchant_id)
    at_risk_customers = [c for c in cust_info.get("customers", []) if c["segment"] in ["AT_RISK", "INACTIVE"] and c["total_spend"] >= 1000.0]

    for c in at_risk_customers[:3]:
        opportunities.append({
            "type": "CUSTOMER_WINBACK",
            "customer_id": c["customer_id"],
            "customer_name": c["name"],
            "priority": "HIGH" if c["total_spend"] >= 2000.0 else "MEDIUM",
            "reason": f"High-value customer '{c['name']}' (spent ₹{c['total_spend']}) has been inactive for {c['days_since_last_purchase']} days.",
            "potential_revenue_impact": round(c["average_order_value"] * 2.0, 2),
            "details": {
                "days_since_last_purchase": c["days_since_last_purchase"],
                "average_order_value": c["average_order_value"],
                "total_spend": c["total_spend"]
            }
        })

    # 4. CROSS_SELL Opportunities (Top product bundled with complementary categories)
    if len(top_products) >= 2:
        prod_a = top_products[0]
        prod_b = top_products[1]
        opportunities.append({
            "type": "CROSS_SELL",
            "primary_product_id": prod_a["product_id"],
            "complementary_product_id": prod_b["product_id"],
            "priority": "MEDIUM",
            "reason": f"High bundle synergy between top sellers '{prod_a['product_name']}' and '{prod_b['product_name']}'.",
            "potential_revenue_impact": round((float(prod_a["revenue"]) + float(prod_b["revenue"])) * 0.10, 2),
            "details": {
                "primary_product": prod_a["product_name"],
                "complementary_product": prod_b["product_name"]
            }
        })

    # Rank opportunities by priority (HIGH before MEDIUM)
    prio_rank = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    opportunities.sort(key=lambda x: (prio_rank.get(x["priority"], 3), -x.get("potential_revenue_impact", 0.0)))

    return {
        "merchant_id": merchant_id,
        "total_opportunities": len(opportunities),
        "opportunities": opportunities
    }
