"""
Paytm Pulse - Phase 6 Action Scorer & Conflict Resolver
Evaluates multi-factor scoring formula and resolves operational conflicts between candidate actions.
"""

from typing import List
from app.decision.schemas import NextBestAction
from app.decision.context_builder import DecisionContext
from app.decision.rules import validate_action_parameters
from app.decision.config import (
    SCORE_WEIGHT_IMPACT,
    SCORE_WEIGHT_CONFIDENCE,
    SCORE_WEIGHT_URGENCY,
    SCORE_WEIGHT_FEASIBILITY,
    URGENCY_FACTORS,
    RISK_PENALTY_STOCKOUT_PROMOTION
)


def score_and_rank_actions(
    candidates: List[NextBestAction],
    ctx: DecisionContext
) -> List[NextBestAction]:
    """
    Evaluates each candidate action against business constraints, resolves conflicts,
    applies the composite scoring formula, and returns actions ranked by descending score.
    """
    scored_actions: List[NextBestAction] = []

    # Check products with severe stockout risk for conflict resolution
    critically_low_product_ids = set()
    for item in ctx.stockout_risks.get("at_risk_products", []):
        if item.get("stockout_risk") in ["CRITICAL", "HIGH"]:
            critically_low_product_ids.add(str(item.get("product_id")))

    for action in candidates:
        params = action.parameters or {}

        # 1. Parameter Validation
        is_valid, validation_err = validate_action_parameters(action.action_type, params)
        if not is_valid:
            action.score = 0.0
            scored_actions.append(action)
            continue

        # 2. Normalized Component Scores
        impact_val = 0.0
        if hasattr(action.estimated_impact, "value"):
            impact_val = float(action.estimated_impact.value or 0.0)
        elif isinstance(action.estimated_impact, dict):
            impact_val = float(action.estimated_impact.get("value", 0.0))
        elif isinstance(action.estimated_impact, (int, float)):
            impact_val = float(action.estimated_impact)

        impact_normalized = min(1.0, max(0.0, impact_val / 3000.0))
        
        confidence_val = max(0.0, min(1.0, float(action.confidence or 0.85)))
        urgency_factor = URGENCY_FACTORS.get(action.urgency, 0.50)
        
        feasibility = 1.0
        # Check if product is available in merchant catalog
        target_prod_id = params.get("product_id") or params.get("primary_product_id")
        if target_prod_id and target_prod_id not in ctx.products:
            feasibility = 0.50

        # 3. Conflict & Risk Penalties
        risk_penalty = 0.0
        # Conflict: Running a promotion on an item that is already nearly out of stock
        if action.action_type in ["RUN_PROMOTION", "CREATE_BUNDLE"] and target_prod_id in critically_low_product_ids:
            risk_penalty += RISK_PENALTY_STOCKOUT_PROMOTION

        # 4. Bounded Historical Feedback Adjustment (Phase 13)
        feedback_adjustment = 0.0
        if getattr(ctx, "db", None):
            try:
                from app.feedback.aggregator import FeedbackAggregator
                agg = FeedbackAggregator(ctx.db)
                perf = agg.get_action_type_performance(action.action_type)
                feedback_adjustment = getattr(perf, "performance_score_adjustment", 0.0)
            except Exception:
                feedback_adjustment = 0.0

        # 5. Composite Formula
        composite_score = (
            (impact_normalized * SCORE_WEIGHT_IMPACT) +
            (confidence_val * SCORE_WEIGHT_CONFIDENCE) +
            (urgency_factor * SCORE_WEIGHT_URGENCY) +
            (feasibility * SCORE_WEIGHT_FEASIBILITY) +
            feedback_adjustment -
            risk_penalty
        )
        action.score = round(max(0.01, composite_score), 4)
        scored_actions.append(action)

    # Sort descending by composite score
    scored_actions.sort(key=lambda x: x.score, reverse=True)
    return scored_actions
