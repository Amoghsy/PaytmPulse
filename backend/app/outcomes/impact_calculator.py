import logging
from typing import Dict, Any, Optional
from app.models.action import Action
from app.outcomes.schemas import (
    BaselineSnapshot,
    ObservedMetrics,
    ImpactCalculationResult,
    OutcomeType,
    OutcomeImpact,
    OutcomeConfidence
)
from app.outcomes.config import MIN_TRANSACTIONS_FOR_MEASUREMENT

logger = logging.getLogger("paytm_pulse.outcomes.impact_calculator")


class ImpactCalculator:
    """
    Computes baseline-adjusted impact and empirical outcome measurements.
    Distinguishes observed, estimated, and predicted numbers.
    """

    def calculate(
        self,
        action: Action,
        baseline: BaselineSnapshot,
        observed: ObservedMetrics
    ) -> ImpactCalculationResult:
        action_type = str(action.action_type.value if hasattr(action.action_type, "value") else action.action_type).upper()
        
        # Check for insufficient data
        if observed.transactions_count < MIN_TRANSACTIONS_FOR_MEASUREMENT and observed.window_hours_observed < 0.5:
            return ImpactCalculationResult(
                outcome_type=OutcomeType.INSUFFICIENT_DATA,
                impact=OutcomeImpact.INSUFFICIENT_DATA,
                confidence=OutcomeConfidence.INSUFFICIENT,
                sales_before=baseline.historical_daily_revenue or 0.0,
                sales_after=observed.actual_sales_revenue,
                expected_sales=baseline.expected_sales_window or 0.0,
                revenue_change=0.0,
                baseline_adjusted_revenue_change=0.0,
                stockout_prevented=False,
                customers_recovered=0,
                offer_conversion=None,
                reasoning="Observation window incomplete or insufficient transactions recorded."
            )

        if action_type in ["REORDER", "RESTOCK_PRODUCT"]:
            return self._calculate_restock_impact(action, baseline, observed)
        elif action_type in ["PROMOTION", "SEND_OFFER", "RUN_PROMOTION"]:
            return self._calculate_promotion_impact(action, baseline, observed)
        elif action_type in ["WINBACK", "CUSTOMER_WINBACK", "CUSTOMER_RETENTION"]:
            return self._calculate_winback_impact(action, baseline, observed)
        elif action_type in ["CROSS_SELL", "CREATE_BUNDLE"]:
            return self._calculate_cross_sell_impact(action, baseline, observed)
        else:
            return self._calculate_general_impact(action, baseline, observed)

    def _calculate_restock_impact(
        self,
        action: Action,
        baseline: BaselineSnapshot,
        observed: ObservedMetrics
    ) -> ImpactCalculationResult:
        stock_before = baseline.stock_level_before or 0
        restock_qty = baseline.metadata.get("restock_quantity") or action.parameters.get("quantity") or 24
        units_sold = observed.units_sold
        final_stock = observed.final_stock_level if observed.final_stock_level is not None else (stock_before + restock_qty - units_sold)
        
        sales_before = baseline.historical_daily_revenue or 0.0
        sales_after = observed.actual_sales_revenue
        expected_sales = baseline.expected_sales_window or sales_before
        rev_change = round(sales_after - sales_before, 2)
        baseline_adj_change = round(sales_after - expected_sales, 2)

        stockout_prevented = False
        outcome_type = OutcomeType.NO_MEASURABLE_IMPACT
        reasoning = ""

        if observed.stockout_occurred or final_stock <= 0:
            stockout_prevented = False
            outcome_type = OutcomeType.STOCKOUT_OCCURRED
            reasoning = "Inventory depleted despite restocking; higher reorder volume needed."
        elif units_sold > stock_before:
            # Sales exceeded initial stock level without stocking out — definitive stockout prevented!
            stockout_prevented = True
            outcome_type = OutcomeType.STOCKOUT_PREVENTED
            reasoning = f"Restocked {restock_qty} units directly prevented stockout. Sold {units_sold} units (exceeding initial stock of {stock_before})."
        elif final_stock > 0 and units_sold > 0:
            # Positive demand satisfied, stock preserved
            stockout_prevented = True
            outcome_type = OutcomeType.POTENTIAL_STOCKOUT_PREVENTED
            reasoning = f"Restocked {restock_qty} units maintained buffer with {units_sold} units sold and {final_stock} units remaining."
        else:
            outcome_type = OutcomeType.NO_MEASURABLE_IMPACT
            reasoning = f"No demand surge observed during observation window ({units_sold} units sold)."

        return ImpactCalculationResult(
            outcome_type=outcome_type,
            sales_before=sales_before,
            sales_after=sales_after,
            expected_sales=expected_sales,
            revenue_change=rev_change,
            baseline_adjusted_revenue_change=baseline_adj_change,
            stockout_prevented=stockout_prevented,
            customers_recovered=0,
            offer_conversion=None,
            reasoning=reasoning
        )

    def _calculate_promotion_impact(
        self,
        action: Action,
        baseline: BaselineSnapshot,
        observed: ObservedMetrics
    ) -> ImpactCalculationResult:
        sales_before = baseline.historical_daily_revenue or 0.0
        sales_after = observed.actual_sales_revenue
        expected_sales = baseline.expected_sales_window or sales_before
        rev_change = round(sales_after - sales_before, 2)
        baseline_adj_change = round(sales_after - expected_sales, 2)

        conversion = None
        if observed.transactions_count > 0:
            conversion = round(min(1.0, observed.units_sold / max(1, observed.transactions_count * 2)), 2)

        if baseline_adj_change > 0 or rev_change > 0:
            outcome_type = OutcomeType.PROMOTION_CONVERSION
            reasoning = f"Observed revenue increase of ₹{rev_change} during promotion window."
        elif rev_change < -50:
            outcome_type = OutcomeType.NEGATIVE_IMPACT
            reasoning = f"Sales declined by ₹{abs(rev_change)} during promotion window."
        else:
            outcome_type = OutcomeType.NO_MEASURABLE_IMPACT
            reasoning = "Promotion showed neutral revenue impact compared to baseline."

        return ImpactCalculationResult(
            outcome_type=outcome_type,
            sales_before=sales_before,
            sales_after=sales_after,
            expected_sales=expected_sales,
            revenue_change=rev_change,
            baseline_adjusted_revenue_change=baseline_adj_change,
            stockout_prevented=False,
            customers_recovered=0,
            offer_conversion=conversion,
            reasoning=reasoning
        )

    def _calculate_winback_impact(
        self,
        action: Action,
        baseline: BaselineSnapshot,
        observed: ObservedMetrics
    ) -> ImpactCalculationResult:
        target_count = baseline.target_customer_count or len(baseline.target_customer_ids or []) or 1
        recovered = observed.returning_customers_count
        conversion = round(recovered / max(1, target_count), 2)
        sales_after = observed.actual_sales_revenue
        
        outcome_type = OutcomeType.CUSTOMERS_RECOVERED if recovered > 0 else OutcomeType.NO_MEASURABLE_IMPACT
        reasoning = f"Winback targeted {target_count} customers; {recovered} returned ({int(conversion * 100)}% conversion) generating ₹{sales_after}."

        return ImpactCalculationResult(
            outcome_type=outcome_type,
            sales_before=0.0,
            sales_after=sales_after,
            expected_sales=0.0,
            revenue_change=sales_after,
            baseline_adjusted_revenue_change=sales_after,
            stockout_prevented=False,
            customers_recovered=recovered,
            offer_conversion=conversion,
            reasoning=reasoning
        )

    def _calculate_cross_sell_impact(
        self,
        action: Action,
        baseline: BaselineSnapshot,
        observed: ObservedMetrics
    ) -> ImpactCalculationResult:
        sec_units = observed.secondary_units_sold
        sales_after = observed.actual_sales_revenue
        rev_change = round(sales_after - (baseline.historical_daily_revenue or 0.0), 2)
        conversion = round(sec_units / max(1, observed.transactions_count), 2) if observed.transactions_count > 0 else 0.0

        outcome_type = OutcomeType.DEMAND_SATISFIED if sec_units > 0 else OutcomeType.NO_MEASURABLE_IMPACT
        reasoning = f"Cross-sell generated {sec_units} secondary unit sales across {observed.transactions_count} orders."

        return ImpactCalculationResult(
            outcome_type=outcome_type,
            sales_before=baseline.historical_daily_revenue or 0.0,
            sales_after=sales_after,
            expected_sales=baseline.expected_sales_window or 0.0,
            revenue_change=rev_change,
            baseline_adjusted_revenue_change=rev_change,
            stockout_prevented=False,
            customers_recovered=0,
            offer_conversion=conversion,
            reasoning=reasoning
        )

    def _calculate_general_impact(
        self,
        action: Action,
        baseline: BaselineSnapshot,
        observed: ObservedMetrics
    ) -> ImpactCalculationResult:
        sales_before = baseline.historical_daily_revenue or 0.0
        sales_after = observed.actual_sales_revenue
        rev_change = round(sales_after - sales_before, 2)
        
        outcome_type = OutcomeType.REVENUE_INCREASE if rev_change > 0 else OutcomeType.NO_MEASURABLE_IMPACT
        reasoning = f"General action observed revenue difference of ₹{rev_change}."

        return ImpactCalculationResult(
            outcome_type=outcome_type,
            sales_before=sales_before,
            sales_after=sales_after,
            expected_sales=baseline.expected_sales_window or sales_before,
            revenue_change=rev_change,
            baseline_adjusted_revenue_change=rev_change,
            stockout_prevented=False,
            customers_recovered=0,
            offer_conversion=None,
            reasoning=reasoning
        )
