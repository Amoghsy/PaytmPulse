"""
Paytm Pulse - Phase 6 Decision Engine Configuration
Defines scoring formula weights, safety constraints, discount limits, and cooldown windows.
"""

# Scoring Formula Weights
SCORE_WEIGHT_IMPACT = 0.40
SCORE_WEIGHT_CONFIDENCE = 0.25
SCORE_WEIGHT_URGENCY = 0.25
SCORE_WEIGHT_FEASIBILITY = 0.10

# Urgency Multipliers
URGENCY_FACTORS = {
    "CRITICAL": 1.0,
    "HIGH": 0.85,
    "MEDIUM": 0.60,
    "LOW": 0.35,
}

# Risk and Penalty Constants
RISK_PENALTY_STOCKOUT_PROMOTION = 0.45  # Heavy penalty for running promotions on critically low stock
RISK_PENALTY_HIGH_DISCOUNT = 0.20
RISK_PENALTY_UNKNOWN_SUPPLIER = 0.10

# Operational Constraints
MAX_PROMOTION_DISCOUNT_PERCENT = 25.0
MIN_PROMOTION_DISCOUNT_PERCENT = 5.0
DEFAULT_PROMOTION_DURATION_HOURS = 6

DEFAULT_SAFETY_STOCK_HOURS = 4.0
MIN_REORDER_QUANTITY = 5
MAX_REORDER_QUANTITY_CAP = 500

# Deduplication Cooldown in Seconds (15 minutes)
DECISION_COOLDOWN_SECONDS = 900
