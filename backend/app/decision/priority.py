"""
Paytm Pulse - Phase 6 Action Priority Classifier
Assigns standardized priority tiers (CRITICAL, HIGH, MEDIUM, LOW) based on composite score and urgency.
"""

from app.decision.schemas import NextBestAction


def assign_priority_tier(action: NextBestAction) -> str:
    """
    Classifies an action into CRITICAL, HIGH, MEDIUM, or LOW based on composite score, urgency, and action type.
    """
    if action.urgency == "CRITICAL" or action.score >= 0.85:
        return "CRITICAL"
    elif action.urgency == "HIGH" or action.score >= 0.65:
        return "HIGH"
    elif action.score >= 0.40:
        return "MEDIUM"
    else:
        return "LOW"


def calibrate_priorities(ranked_actions: list[NextBestAction]) -> list[NextBestAction]:
    """
    Calibrates priority labels across a list of ranked actions.
    """
    for act in ranked_actions:
        act.priority = assign_priority_tier(act)
    return ranked_actions
