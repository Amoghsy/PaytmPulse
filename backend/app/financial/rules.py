from typing import Dict, Any, Optional
from app.financial.schemas import FinancialNeedType, FinancialNeedDetectionResult
from app.financial.config import (
    DEMAND_GROWTH_THRESHOLD,
    RESTOCK_FREQUENCY_THRESHOLD,
    SALES_GROWTH_THRESHOLD,
    CUSTOMER_GROWTH_THRESHOLD
)


class FinancialRulesEngine:
    """
    Deterministic evaluation of merchant business data to identify contextual financial needs.
    """

    @staticmethod
    def evaluate(merchant_id: str, metrics: Dict[str, Any]) -> FinancialNeedDetectionResult:
        """
        Evaluate business signals in priority order:
        1. Working Capital (demand surge + restocking frequency)
        2. Inventory Financing (frequent stock cycles + high velocity)
        3. Business Expansion (sustained revenue & customer expansion)
        4. Cash Flow Support (short-term sales dip with ongoing reorders)
        """
        demand_growth = float(metrics.get("demand_growth", 0.0))
        restock_count = int(metrics.get("restock_count_last_7_days", 0))
        sales_growth = float(metrics.get("sales_growth", 0.0))
        customer_growth = float(metrics.get("customer_growth", 0.0))
        avg_daily_sales = float(metrics.get("average_daily_sales", 0.0))
        recent_restock_spend = float(metrics.get("recent_restock_spend", 0.0))

        # 1. Working Capital Check
        if demand_growth >= DEMAND_GROWTH_THRESHOLD and restock_count >= RESTOCK_FREQUENCY_THRESHOLD:
            conf = min(0.95, round(0.70 + (demand_growth * 0.3) + (min(restock_count, 5) * 0.03), 2))
            estimated_amt = max(10000.0, min(50000.0, round(avg_daily_sales * 14, -2)))
            return FinancialNeedDetectionResult(
                merchant_id=merchant_id,
                need_detected=True,
                need_type=FinancialNeedType.WORKING_CAPITAL,
                reason="Your inventory demand has increased significantly and restocking frequency is high.",
                supporting_signals=[
                    f"Product demand surge: +{demand_growth * 100:.1f}% above historical baseline",
                    f"Frequent replenishment: {restock_count} reorders recorded in the last 7 days",
                    f"Average daily business revenue: ₹{avg_daily_sales:,.2f}"
                ],
                confidence=conf,
                estimated_requirement_amount=estimated_amt
            )

        # 2. Inventory Financing Check
        if restock_count >= RESTOCK_FREQUENCY_THRESHOLD and (recent_restock_spend > 1000.0 or demand_growth > 0.15):
            conf = min(0.90, round(0.70 + (restock_count * 0.05), 2))
            estimated_amt = max(15000.0, min(75000.0, round(recent_restock_spend * 2.5 if recent_restock_spend > 0 else avg_daily_sales * 20, -2)))
            return FinancialNeedDetectionResult(
                merchant_id=merchant_id,
                need_detected=True,
                need_type=FinancialNeedType.INVENTORY_FINANCING,
                reason="High inventory turnover and recurring restocking indicate ongoing inventory financing value.",
                supporting_signals=[
                    f"Replenishment frequency: {restock_count} restocks in last 7 days",
                    f"Estimated recent inventory spend: ₹{recent_restock_spend:,.2f}",
                    "Rapid product turnover in key categories"
                ],
                confidence=conf,
                estimated_requirement_amount=estimated_amt
            )

        # 3. Business Expansion Check
        if sales_growth >= SALES_GROWTH_THRESHOLD and customer_growth >= CUSTOMER_GROWTH_THRESHOLD:
            conf = min(0.92, round(0.75 + (sales_growth * 0.2) + (customer_growth * 0.2), 2))
            estimated_amt = max(25000.0, min(150000.0, round(avg_daily_sales * 30, -2)))
            return FinancialNeedDetectionResult(
                merchant_id=merchant_id,
                need_detected=True,
                need_type=FinancialNeedType.BUSINESS_EXPANSION,
                reason="Sustained sales and customer growth indicate potential business expansion opportunities.",
                supporting_signals=[
                    f"Sales revenue growth: +{sales_growth * 100:.1f}% vs previous cycle",
                    f"Customer base expansion: +{customer_growth * 100:.1f}% new/active customers",
                    f"Consistent daily revenue baseline: ₹{avg_daily_sales:,.2f}"
                ],
                confidence=conf,
                estimated_requirement_amount=estimated_amt
            )

        # 4. Cash Flow Support Check
        if sales_growth < -0.15 and restock_count >= 1:
            conf = min(0.85, round(0.70 + abs(sales_growth) * 0.3, 2))
            estimated_amt = max(10000.0, min(35000.0, round(avg_daily_sales * 10, -2)))
            return FinancialNeedDetectionResult(
                merchant_id=merchant_id,
                need_detected=True,
                need_type=FinancialNeedType.CASH_FLOW_SUPPORT,
                reason="Temporary sales dip observed alongside continuing operational inventory commitments.",
                supporting_signals=[
                    f"Sales variance: {sales_growth * 100:.1f}% during recent period",
                    f"Ongoing inventory replenishment: {restock_count} reorders maintained",
                    "Short-term working buffer to bridge revenue cycles"
                ],
                confidence=conf,
                estimated_requirement_amount=estimated_amt
            )

        # No financial need detected
        return FinancialNeedDetectionResult(
            merchant_id=merchant_id,
            need_detected=False,
            need_type=None,
            reason="Merchant business signals indicate normal operational steady-state with no additional financial requirements.",
            supporting_signals=[
                f"Sales growth: {sales_growth * 100:.1f}% within normal variance",
                f"Restock count: {restock_count} in last 7 days"
            ],
            confidence=0.50,
            estimated_requirement_amount=0.0
        )
