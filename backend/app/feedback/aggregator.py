import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.feedback_signal import FeedbackSignal
from app.models.recommendation import Recommendation, RecommendationStatus
from app.models.action import Action, ActionStatus
from app.models.outcome import Outcome
from app.feedback.config import FEEDBACK_WEIGHT, MAX_FEEDBACK_ADJUSTMENT
from app.feedback.schemas import ActionTypePerformanceSummary, MerchantFeedbackSummary

logger = logging.getLogger("paytm_pulse.feedback.aggregator")


class FeedbackAggregator:
    """
    Aggregates historical recommendation outcomes, approval rates, and computes
    bounded heuristic adjustments for the Next Best Action decision engine.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_action_type_performance(self, action_type: str) -> ActionTypePerformanceSummary:
        """
        Calculates historical performance metrics for a specific action type.
        """
        act_upper = action_type.upper()

        # Query all feedback signals for this action type
        signals = self.db.query(FeedbackSignal).filter(
            func.upper(FeedbackSignal.action_type) == act_upper
        ).all()

        gen_count = sum(1 for s in signals if s.feedback_type in ["MERCHANT_APPROVED", "MERCHANT_REJECTED", "RECOMMENDATION_EXPIRED", "ACTION_EXECUTED"])
        app_count = sum(1 for s in signals if s.feedback_type == "MERCHANT_APPROVED" or s.merchant_decision == "APPROVED")
        rej_count = sum(1 for s in signals if s.feedback_type == "MERCHANT_REJECTED" or s.merchant_decision == "REJECTED")
        exp_count = sum(1 for s in signals if s.feedback_type in ["RECOMMENDATION_EXPIRED", "MERCHANT_IGNORED"] or s.merchant_decision == "EXPIRED")

        exec_count = sum(1 for s in signals if s.feedback_type == "ACTION_EXECUTED" or s.execution_status == "EXECUTED")
        fail_count = sum(1 for s in signals if s.feedback_type == "ACTION_FAILED" or s.execution_status == "FAILED")

        pos_count = sum(1 for s in signals if s.feedback_type in ["POSITIVE_OUTCOME", "HIGH_CONFIDENCE_SUCCESS", "LOW_CONFIDENCE_SUCCESS"] or s.outcome_impact == "POSITIVE")
        neu_count = sum(1 for s in signals if s.feedback_type == "NEUTRAL_OUTCOME" or s.outcome_impact == "NEUTRAL")
        neg_count = sum(1 for s in signals if s.feedback_type in ["NEGATIVE_OUTCOME", "HIGH_CONFIDENCE_FAILURE", "LOW_CONFIDENCE_FAILURE"] or s.outcome_impact == "NEGATIVE")
        ins_count = sum(1 for s in signals if s.feedback_type == "INSUFFICIENT_DATA" or s.outcome_impact == "INSUFFICIENT_DATA")

        total_decisions = app_count + rej_count + exp_count
        app_rate = round(app_count / max(1, total_decisions), 2) if total_decisions > 0 else 0.0

        total_measured = pos_count + neu_count + neg_count
        succ_rate = round(pos_count / max(1, total_measured), 2) if total_measured > 0 else 0.0

        # Calculate Bounded Score Adjustment
        score_adj = self.calculate_score_adjustment(action_type, total_measured, pos_count, neg_count, app_rate)

        return ActionTypePerformanceSummary(
            action_type=act_upper,
            recommendations_generated=max(gen_count, total_decisions),
            recommendations_approved=app_count,
            recommendations_rejected=rej_count,
            recommendations_expired=exp_count,
            actions_executed=exec_count,
            actions_failed=fail_count,
            positive_outcomes=pos_count,
            neutral_outcomes=neu_count,
            negative_outcomes=neg_count,
            insufficient_data=ins_count,
            approval_rate=app_rate,
            success_rate=succ_rate,
            average_outcome_confidence=0.85 if total_measured > 0 else None,
            performance_score_adjustment=score_adj
        )

    def calculate_score_adjustment(
        self,
        action_type: str,
        total_measured: int,
        pos_count: int,
        neg_count: int,
        approval_rate: float
    ) -> float:
        """
        Calculates a strictly bounded performance adjustment: [-MAX_FEEDBACK_ADJUSTMENT, +MAX_FEEDBACK_ADJUSTMENT].
        Requires at least 2 historical measured records to apply adjustments.
        """
        if total_measured < 2:
            return 0.0

        # Outcome ratio delta: (pos - neg) / total
        outcome_ratio = (pos_count - neg_count) / float(total_measured)
        # Approval delta relative to 50% baseline
        approval_delta = approval_rate - 0.50

        raw_adjustment = (outcome_ratio * 0.08) + (approval_delta * 0.04)
        bounded = max(-MAX_FEEDBACK_ADJUSTMENT, min(MAX_FEEDBACK_ADJUSTMENT, raw_adjustment))
        return round(bounded, 4)

    def get_merchant_feedback_summary(self, merchant_id: str) -> MerchantFeedbackSummary:
        """
        Calculates overall feedback and recommendation metrics for a merchant.
        """
        signals = self.db.query(FeedbackSignal).filter(
            FeedbackSignal.merchant_id == merchant_id
        ).all()

        app_count = sum(1 for s in signals if s.feedback_type == "MERCHANT_APPROVED" or s.merchant_decision == "APPROVED")
        rej_count = sum(1 for s in signals if s.feedback_type == "MERCHANT_REJECTED" or s.merchant_decision == "REJECTED")
        exp_count = sum(1 for s in signals if s.feedback_type in ["RECOMMENDATION_EXPIRED", "MERCHANT_IGNORED"] or s.merchant_decision == "EXPIRED")

        exec_count = sum(1 for s in signals if s.feedback_type == "ACTION_EXECUTED" or s.execution_status == "EXECUTED")
        fail_count = sum(1 for s in signals if s.feedback_type == "ACTION_FAILED" or s.execution_status == "FAILED")

        pos_count = sum(1 for s in signals if s.feedback_type in ["POSITIVE_OUTCOME", "HIGH_CONFIDENCE_SUCCESS", "LOW_CONFIDENCE_SUCCESS"] or s.outcome_impact == "POSITIVE")
        neu_count = sum(1 for s in signals if s.feedback_type == "NEUTRAL_OUTCOME" or s.outcome_impact == "NEUTRAL")
        neg_count = sum(1 for s in signals if s.feedback_type in ["NEGATIVE_OUTCOME", "HIGH_CONFIDENCE_FAILURE", "LOW_CONFIDENCE_FAILURE"] or s.outcome_impact == "NEGATIVE")
        ins_count = sum(1 for s in signals if s.feedback_type == "INSUFFICIENT_DATA" or s.outcome_impact == "INSUFFICIENT_DATA")

        useful_count = sum(1 for s in signals if s.merchant_rating == "USEFUL" or s.feedback_type == "MERCHANT_FEEDBACK_POSITIVE")
        not_useful_count = sum(1 for s in signals if s.merchant_rating == "NOT_USEFUL" or s.feedback_type == "MERCHANT_FEEDBACK_NEGATIVE")

        total_recs = app_count + rej_count + exp_count
        app_rate = round(app_count / max(1, total_recs), 2) if total_recs > 0 else 0.0

        total_measured = pos_count + neu_count + neg_count
        succ_rate = round(pos_count / max(1, total_measured), 2) if total_measured > 0 else 0.0

        net_rev = 0.0
        try:
            outcomes = self.db.query(Outcome).join(Action, Outcome.action_id == Action.id).filter(
                Action.merchant_id == merchant_id
            ).all()
            for o in outcomes:
                if o.revenue_change:
                    net_rev += float(o.revenue_change)
        except Exception:
            pass

        return MerchantFeedbackSummary(
            merchant_id=merchant_id,
            total_recommendations=total_recs,
            recommendations_generated=total_recs,
            total_approved=app_count,
            approved=app_count,
            total_rejected=rej_count,
            rejected=rej_count,
            total_expired=exp_count,
            expired=exp_count,
            total_executed=exec_count,
            executed=exec_count,
            total_execution_failed=fail_count,
            execution_failed=fail_count,
            total_measured=total_measured,
            successful_actions=pos_count,
            positive_outcomes=pos_count,
            neutral_outcomes=neu_count,
            negative_outcomes=neg_count,
            insufficient_data=ins_count,
            merchant_useful_ratings=useful_count,
            merchant_not_useful_ratings=not_useful_count,
            approval_rate=app_rate,
            success_rate=succ_rate,
            outcome_success_rate=succ_rate,
            net_revenue_change=round(net_rev, 2)
        )
