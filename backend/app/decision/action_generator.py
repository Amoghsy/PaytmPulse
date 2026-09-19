"""
Paytm Pulse - Phase 6 Action Candidate Generator
Maps real-time business events and Phase 4/5 intelligence signals to potential candidate actions.
"""

from typing import List, Dict, Any, Optional
import uuid

from app.decision.schemas import NextBestAction, EstimatedImpact
from app.decision.context_builder import DecisionContext
from app.decision.rules import (
    calculate_recommended_restock_quantity,
    build_promotion_parameters,
    build_customer_winback_parameters,
    build_cross_sell_parameters
)
from app.decision.impact_estimator import (
    estimate_stockout_protection_impact,
    estimate_promotion_impact,
    estimate_customer_winback_impact,
    estimate_cross_sell_impact,
    estimate_trend_monitoring_impact
)


def generate_candidate_actions(ctx: DecisionContext) -> List[NextBestAction]:
    """
    Scans the decision context, active event, and merchant intelligence to generate supported candidate actions.
    """
    candidates: List[NextBestAction] = []
    merchant_id = ctx.merchant_id
    event = ctx.event or {}
    event_id = event.get("event_id")
    event_type = event.get("event_type")

    # -------------------------------------------------------------------------
    # 1. Event-Driven Candidate Generation
    # -------------------------------------------------------------------------
    if event_type == "DEMAND_SPIKE":
        payload = event.get("payload", {})
        prod_id = payload.get("product_id") or (list(ctx.products.keys())[0] if ctx.products else None)
        prod = ctx.products.get(prod_id) if prod_id else None
        prod_name = prod.name if prod else "Primary Product"
        price = float(prod.price) if prod else 50.0
        current_stock = prod.current_stock if prod else 10
        reorder_lvl = prod.reorder_level if prod else 15
        
        # A. Restock Action (Critical/High to sustain surge)
        reorder_qty = calculate_recommended_restock_quantity(
            current_stock=current_stock,
            reorder_level=reorder_lvl,
            maximum_stock=100,
            forecast_hourly_demand=8.0,
            average_daily_sales_units=20.0
        )
        impact_restock = estimate_stockout_protection_impact(
            product_price=price,
            current_stock=current_stock,
            forecast_hourly_demand=8.0,
            hours_runway=2.4
        )
        candidates.append(NextBestAction(
            id=f"act_restock_{uuid.uuid4().hex[:8]}",
            merchant_id=merchant_id,
            event_id=event_id,
            action_type="RESTOCK_PRODUCT",
            title=f"Restock {prod_name}",
            description=f"Order {reorder_qty} units of {prod_name} to fulfill surging customer demand.",
            reason=f"Demand is surging and existing inventory of {current_stock} units may deplete within ~2-3 hours.",
            priority="HIGH",
            urgency="HIGH",
            confidence=0.91,
            estimated_impact=impact_restock,
            parameters={"product_id": prod_id, "quantity": reorder_qty, "supplier": prod.supplier if prod else "Default Supplier"},
            requires_approval=True,
            status="PENDING_APPROVAL"
        ))

        # B. Run Promotion Action (Alternative)
        promo_params = build_promotion_parameters(product_id=prod_id or "p1", product_price=price, suggested_discount=10.0)
        impact_promo = estimate_promotion_impact(product_price=price, average_daily_sales=float(ctx.sales.get("average_daily_sales", 1000.0)), discount_percentage=10.0)
        candidates.append(NextBestAction(
            id=f"act_promo_{uuid.uuid4().hex[:8]}",
            merchant_id=merchant_id,
            event_id=event_id,
            action_type="RUN_PROMOTION",
            title=f"Launch Surge Flash Deal on {prod_name}",
            description=f"Run a short 10% discount on {prod_name} to maximize evening footfall.",
            reason=f"Capitalize on high customer velocity and surge interest for {prod_name}.",
            priority="MEDIUM",
            urgency="MEDIUM",
            confidence=0.82,
            estimated_impact=impact_promo,
            parameters=promo_params,
            requires_approval=True,
            status="PENDING_APPROVAL"
        ))

        # C. Monitor Trend Action
        impact_mon = estimate_trend_monitoring_impact(daily_sales=float(ctx.sales.get("today_sales", 500.0)))
        candidates.append(NextBestAction(
            id=f"act_mon_{uuid.uuid4().hex[:8]}",
            merchant_id=merchant_id,
            event_id=event_id,
            action_type="MONITOR_TREND",
            title="Monitor Peak Hour Velocity",
            description="Track hourly sales velocity without immediate inventory changes.",
            reason="Observe whether the demand surge continues into evening peak hours.",
            priority="LOW",
            urgency="LOW",
            confidence=0.75,
            estimated_impact=impact_mon,
            parameters={"monitoring_horizon_hours": 3},
            requires_approval=True,
            status="PENDING_APPROVAL"
        ))

    elif event_type in ["STOCKOUT_RISK", "INVENTORY_LOW"]:
        payload = event.get("payload", {})
        prod_id = payload.get("product_id") or (list(ctx.products.keys())[0] if ctx.products else None)
        prod = ctx.products.get(prod_id) if prod_id else None
        prod_name = prod.name if prod else "Product"
        price = float(prod.price) if prod else 50.0
        current_stock = prod.current_stock if prod else 5

        reorder_qty = calculate_recommended_restock_quantity(
            current_stock=current_stock,
            reorder_level=prod.reorder_level if prod else 20,
            maximum_stock=100,
            forecast_hourly_demand=3.0,
            average_daily_sales_units=15.0
        )
        impact_stockout = estimate_stockout_protection_impact(
            product_price=price,
            current_stock=current_stock,
            forecast_hourly_demand=3.0,
            hours_runway=1.5
        )
        candidates.append(NextBestAction(
            id=f"act_stockout_{uuid.uuid4().hex[:8]}",
            merchant_id=merchant_id,
            event_id=event_id,
            action_type="RESTOCK_PRODUCT",
            title=f"Urgent Restock: {prod_name}",
            description=f"Replenish {reorder_qty} units of {prod_name} to prevent impending stockout.",
            reason=f"Current stock of {current_stock} units is below safety threshold with ~1.5h runway remaining.",
            priority="CRITICAL",
            urgency="CRITICAL",
            confidence=0.95,
            estimated_impact=impact_stockout,
            parameters={"product_id": prod_id, "quantity": reorder_qty, "supplier": prod.supplier if prod else "Default Supplier"},
            requires_approval=True,
            status="PENDING_APPROVAL"
        ))

    elif event_type == "SALES_DECLINE":
        top_prods = ctx.sales.get("top_products", [])
        prod_id = top_prods[0].get("product_id") if top_prods else (list(ctx.products.keys())[0] if ctx.products else None)
        prod = ctx.products.get(prod_id) if prod_id else None
        prod_name = prod.name if prod else "Best Seller"
        price = float(prod.price) if prod else 40.0

        # A. Promotion Offer
        promo_params = build_promotion_parameters(product_id=prod_id or "p1", product_price=price, suggested_discount=15.0)
        impact_promo = estimate_promotion_impact(product_price=price, average_daily_sales=float(ctx.sales.get("average_daily_sales", 1200.0)), discount_percentage=15.0)
        candidates.append(NextBestAction(
            id=f"act_decline_promo_{uuid.uuid4().hex[:8]}",
            merchant_id=merchant_id,
            event_id=event_id,
            action_type="RUN_PROMOTION",
            title=f"Afternoon Flash Discount on {prod_name}",
            description=f"Launch a 15% discount on {prod_name} to revive store footfall.",
            reason="Today's sales volume is trailing behind the baseline daily average.",
            priority="HIGH",
            urgency="HIGH",
            confidence=0.88,
            estimated_impact=impact_promo,
            parameters=promo_params,
            requires_approval=True,
            status="PENDING_APPROVAL"
        ))

        # B. Customer Winback
        winback_params = build_customer_winback_parameters(customer_segment="AT_RISK", discount_percentage=10.0)
        impact_winback = estimate_customer_winback_impact(
            at_risk_customers_count=len(ctx.customers.get("at_risk_customers", [])),
            avg_customer_historical_spend=1500.0
        )
        candidates.append(NextBestAction(
            id=f"act_decline_winback_{uuid.uuid4().hex[:8]}",
            merchant_id=merchant_id,
            event_id=event_id,
            action_type="CUSTOMER_WINBACK",
            title="Re-engage Inactive Regular Customers",
            description="Send a 10% loyalty discount voucher to lapsed regular customers.",
            reason="Reactivating repeat customers quickly brings footfall back to normal levels.",
            priority="MEDIUM",
            urgency="MEDIUM",
            confidence=0.84,
            estimated_impact=impact_winback,
            parameters=winback_params,
            requires_approval=True,
            status="PENDING_APPROVAL"
        ))

    elif event_type == "CUSTOMER_RISK":
        winback_params = build_customer_winback_parameters(customer_segment="AT_RISK", discount_percentage=12.0)
        impact_winback = estimate_customer_winback_impact(
            at_risk_customers_count=len(ctx.customers.get("at_risk_customers", [])),
            avg_customer_historical_spend=2200.0
        )
        candidates.append(NextBestAction(
            id=f"act_cust_risk_{uuid.uuid4().hex[:8]}",
            merchant_id=merchant_id,
            event_id=event_id,
            action_type="CUSTOMER_WINBACK",
            title="Send Loyalty Winback Offer",
            description="Offer 12% discount to at-risk regular customers whose visit interval has doubled.",
            reason="High-value repeat shoppers have not visited in over 30 days.",
            priority="HIGH",
            urgency="HIGH",
            confidence=0.89,
            estimated_impact=impact_winback,
            parameters=winback_params,
            requires_approval=True,
            status="PENDING_APPROVAL"
        ))

    # -------------------------------------------------------------------------
    # 2. General Opportunities & Proactive Candidates
    # -------------------------------------------------------------------------
    stockout_data = ctx.stockout_risks if isinstance(ctx.stockout_risks, dict) else {}
    opps_data = ctx.opportunities if isinstance(ctx.opportunities, dict) else {}
    cust_data = ctx.customers if isinstance(ctx.customers, dict) else {}
    sales_data = ctx.sales if isinstance(ctx.sales, dict) else {}

    if not candidates:
        # Check Stockout Risks
        at_risk_list = stockout_data.get("at_risk_products", []) or []
        if at_risk_list:
            top_risk = at_risk_list[0]
            prod = ctx.products.get(top_risk.get("product_id")) if ctx.products else None
            price = float(prod.price) if prod else 50.0
            reorder_qty = top_risk.get("reorder_quantity_suggested", 20)
            impact_stockout = estimate_stockout_protection_impact(
                product_price=price,
                current_stock=top_risk.get("current_stock", 5),
                forecast_hourly_demand=top_risk.get("forecast_hourly_demand", 2.0),
                hours_runway=top_risk.get("estimated_hours_to_stockout", 3.0)
            )
            candidates.append(NextBestAction(
                id=f"act_gen_restock_{uuid.uuid4().hex[:8]}",
                merchant_id=merchant_id,
                event_id=None,
                action_type="RESTOCK_PRODUCT",
                title=f"Restock {top_risk.get('product_name') or 'Inventory'}",
                description=f"Order {reorder_qty} units of {top_risk.get('product_name') or 'stock'} before depletion.",
                reason=f"Item has only {top_risk.get('current_stock', 5)} units remaining with estimated runway of {top_risk.get('estimated_hours_to_stockout', 3.0)} hours.",
                priority="HIGH" if top_risk.get("stockout_risk") == "CRITICAL" else "MEDIUM",
                urgency="HIGH",
                confidence=0.90,
                estimated_impact=impact_stockout,
                parameters={"product_id": top_risk.get("product_id"), "quantity": reorder_qty},
                requires_approval=True,
                status="PENDING_APPROVAL"
            ))

        # Check Cross-Sell Opportunities
        opps = opps_data.get("opportunities", []) or []
        cross_opps = [o for o in opps if isinstance(o, dict) and o.get("type") == "CROSS_SELL"]
        if cross_opps:
            co = cross_opps[0]
            prod_pair = co.get("details", {}).get("pair", []) if isinstance(co.get("details"), dict) else []
            p1_id = prod_pair[0] if len(prod_pair) > 0 else (list(ctx.products.keys())[0] if ctx.products else "p1")
            p2_id = prod_pair[1] if len(prod_pair) > 1 else (list(ctx.products.keys())[1] if len(ctx.products) > 1 else "p2")
            bundle_name = co.get('product_name') or co.get('headline') or "Top Complementary Products"
            impact_bundle = estimate_cross_sell_impact(primary_price=40.0, paired_price=20.0)
            candidates.append(NextBestAction(
                id=f"act_bundle_{uuid.uuid4().hex[:8]}",
                merchant_id=merchant_id,
                event_id=None,
                action_type="CREATE_BUNDLE",
                title=f"Create Combo Bundle: {bundle_name}" if co.get('product_name') else "Create Popular Items Combo Bundle",
                description="Pair frequently co-purchased items with a 5% combo discount.",
                reason=co.get("reason", "Customers frequently buy these complementary items together."),
                priority="MEDIUM",
                urgency="MEDIUM",
                confidence=0.85,
                estimated_impact=impact_bundle,
                parameters=build_cross_sell_parameters(p1_id, p2_id),
                requires_approval=True,
                status="PENDING_APPROVAL"
            ))

        # Check Customer Winback
        if cust_data.get("at_risk_customers"):
            winback_params = build_customer_winback_parameters(customer_segment="AT_RISK", discount_percentage=10.0)
            impact_winback = estimate_customer_winback_impact(
                at_risk_customers_count=len(cust_data.get("at_risk_customers", [])),
                avg_customer_historical_spend=1200.0
            )
            candidates.append(NextBestAction(
                id=f"act_gen_winback_{uuid.uuid4().hex[:8]}",
                merchant_id=merchant_id,
                event_id=None,
                action_type="CUSTOMER_WINBACK",
                title="Re-engage Lapsed Regular Customers",
                description="Send a 10% coupon to re-activate churn-risk shoppers.",
                reason="Identified inactive customers who were previously frequent buyers.",
                priority="MEDIUM",
                urgency="MEDIUM",
                confidence=0.80,
                estimated_impact=impact_winback,
                parameters=winback_params,
                requires_approval=True,
                status="PENDING_APPROVAL"
            ))

    # Default fallback candidate if none generated
    if not candidates:
        today_sales_val = float(sales_data.get("today_sales", 500.0)) if isinstance(sales_data, dict) else 500.0
        impact_mon = estimate_trend_monitoring_impact(daily_sales=today_sales_val)
        candidates.append(NextBestAction(
            id=f"act_def_mon_{uuid.uuid4().hex[:8]}",
            merchant_id=merchant_id,
            event_id=event_id,
            action_type="MONITOR_TREND",
            title="Monitor Daily Sales & Footfall",
            description="Continue monitoring transactions and catalog velocity.",
            reason="Store operations and inventory levels are currently in healthy steady state.",
            priority="LOW",
            urgency="LOW",
            confidence=0.90,
            estimated_impact=impact_mon,
            parameters={"status": "STEADY_STATE"},
            requires_approval=True,
            status="PENDING_APPROVAL"
        ))

    return candidates
