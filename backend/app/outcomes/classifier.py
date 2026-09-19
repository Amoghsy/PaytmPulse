import logging
from typing import Dict, Any, Tuple
from app.outcomes.schemas import (
    ImpactCalculationResult,
    ObservedMetrics,
    BaselineSnapshot,
    OutcomeImpact,
    OutcomeConfidence,
    OutcomeType,
    LearningSignal
)

logger = logging.getLogger("paytm_pulse.outcomes.classifier")


class OutcomeClassifier:
    """
    Deterministically classifies outcome impacts, confidence tiers, and learning signals.
    """

    def classify(
        self,
        result: ImpactCalculationResult,
        observed: ObservedMetrics,
        baseline: BaselineSnapshot,
        action_type: str
    ) -> Tuple[OutcomeImpact, OutcomeConfidence, LearningSignal]:
        # 1. Determine Confidence
        if result.outcome_type == OutcomeType.INSUFFICIENT_DATA:
            confidence = OutcomeConfidence.INSUFFICIENT
            impact = OutcomeImpact.INSUFFICIENT_DATA
        elif observed.transactions_count >= 10 and observed.window_hours_observed >= 6.0:
            confidence = OutcomeConfidence.HIGH
            impact = self._classify_impact(result)
        elif observed.transactions_count >= 3 or observed.window_hours_observed >= 1.0:
            confidence = OutcomeConfidence.MEDIUM
            impact = self._classify_impact(result)
        elif observed.transactions_count > 0:
            confidence = OutcomeConfidence.LOW
            impact = self._classify_impact(result)
        else:
            confidence = OutcomeConfidence.INSUFFICIENT
            impact = OutcomeImpact.INSUFFICIENT_DATA

        # 2. Derive Learning Signal
        signal = self._generate_learning_signal(action_type, impact, result)

        return impact, confidence, signal

    def _classify_impact(self, result: ImpactCalculationResult) -> OutcomeImpact:
        if result.outcome_type in [
            OutcomeType.STOCKOUT_PREVENTED,
            OutcomeType.POTENTIAL_STOCKOUT_PREVENTED,
            OutcomeType.CUSTOMERS_RECOVERED,
            OutcomeType.PROMOTION_CONVERSION,
            OutcomeType.DEMAND_SATISFIED,
            OutcomeType.REVENUE_INCREASE,
            OutcomeType.REVENUE_PROTECTED,
            OutcomeType.TREND_RESOLVED
        ]:
            return OutcomeImpact.POSITIVE

        if result.outcome_type in [
            OutcomeType.STOCKOUT_OCCURRED,
            OutcomeType.NEGATIVE_IMPACT,
            OutcomeType.TREND_ESCALATED
        ]:
            return OutcomeImpact.NEGATIVE

        if result.stockout_prevented or result.customers_recovered > 0 or result.revenue_change > 0:
            return OutcomeImpact.POSITIVE

        if result.revenue_change < -100:
            return OutcomeImpact.NEGATIVE

        return OutcomeImpact.NEUTRAL

    def _generate_learning_signal(
        self,
        action_type: str,
        impact: OutcomeImpact,
        result: ImpactCalculationResult
    ) -> LearningSignal:
        act_upper = action_type.upper()
        
        if impact == OutcomeImpact.POSITIVE:
            if act_upper in ["REORDER", "RESTOCK_PRODUCT"]:
                sig = "Restocking under elevated demand successfully protected stock availability and captured ongoing sales."
                adapt = "Maintain or increase restock recommendation confidence for similar surge triggers."
            elif act_upper in ["PROMOTION", "SEND_OFFER", "RUN_PROMOTION"]:
                sig = f"Promotion converted with positive incremental revenue (₹{result.revenue_change})."
                adapt = "Re-target similar discount structures for matching product categories."
            elif act_upper in ["WINBACK", "CUSTOMER_WINBACK", "CUSTOMER_RETENTION"]:
                sig = f"Winback successfully recovered {result.customers_recovered} customer(s)."
                adapt = "Incorporate similar voucher incentives for churning segments."
            else:
                sig = f"Action {action_type} demonstrated measurable positive business impact."
                adapt = "Reinforce recommendation pattern for equivalent merchant state."
        elif impact == OutcomeImpact.NEGATIVE:
            if act_upper in ["REORDER", "RESTOCK_PRODUCT"]:
                sig = "Inventory stockout still occurred post-execution."
                adapt = "Increase safety buffer multiplier or accelerate lead time forecast in Next Best Action."
            elif act_upper in ["PROMOTION", "SEND_OFFER"]:
                sig = "Promotion generated sub-baseline revenue or poor conversion."
                adapt = "Reduce promotion priority or recommend tighter bundle rather than direct markdown."
            else:
                sig = f"Action {action_type} failed to produce intended uplift."
                adapt = "De-prioritize action priority score under similar triggering conditions."
        elif impact == OutcomeImpact.INSUFFICIENT_DATA:
            sig = "Insufficient post-action transactions in observation window to substantiate outcome."
            adapt = "Extend observation window before triggering downstream model adjustments."
        else:
            sig = f"Action {action_type} yielded neutral variance within normal baseline noise."
            adapt = "Keep current scoring weights unchanged."

        confidence_val = 0.90 if impact == OutcomeImpact.POSITIVE else (0.75 if impact == OutcomeImpact.NEGATIVE else 0.50)

        return LearningSignal(
            action_type=action_type,
            recommended=True,
            approved=True,
            executed=True,
            outcome_type=result.outcome_type.value if hasattr(result.outcome_type, "value") else str(result.outcome_type),
            impact=impact.value if hasattr(impact, "value") else str(impact),
            confidence=confidence_val,
            signal=sig,
            adaptation_rule=adapt
        )
