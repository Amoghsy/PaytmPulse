import logging
from typing import Optional, Dict, Any
from app.models.recommendation import Recommendation, RecommendationStatus
from app.models.action import Action, ActionStatus
from app.models.outcome import Outcome
from app.models.feedback_signal import FeedbackSignal
from app.feedback.config import RecommendationEffectiveness
from app.feedback.schemas import RecommendationEffectivenessResponse

logger = logging.getLogger("paytm_pulse.feedback.effectiveness")


class EffectivenessCalculator:
    """
    Computes deterministic recommendation effectiveness based on the full lifecycle journey:
    Recommendation -> Merchant Decision -> Execution -> Measured Business Outcome -> Merchant Feedback.
    """

    @classmethod
    def calculate(
        cls,
        rec: Recommendation,
        action: Optional[Action] = None,
        outcome: Optional[Outcome] = None,
        merchant_feedback_signal: Optional[FeedbackSignal] = None,
        has_expired_signal: bool = False
    ) -> RecommendationEffectivenessResponse:
        rec_id = str(rec.id)
        merchant_id = str(rec.merchant_id)
        action_type = rec.suggested_actions if hasattr(rec, "suggested_actions") and rec.suggested_actions else (rec.type.value if hasattr(rec.type, "value") else str(rec.type))
        rec_title = rec.title or (rec.recommendation_text[:40] if hasattr(rec, "recommendation_text") and rec.recommendation_text else "Recommendation")
        
        # Determine Decision
        rec_status_str = str(rec.status.value if hasattr(rec.status, "value") else rec.status).upper()
        merchant_decision = "EXPIRED" if has_expired_signal else rec_status_str

        # Timeline snapshot
        timeline: Dict[str, Any] = {
            "recommended_at": rec.created_at.isoformat() if rec.created_at else None,
            "decision": merchant_decision,
            "executed": False,
            "measured": False,
        }

        # 1. Check Rejection / Expiration
        if rec_status_str == "REJECTED":
            return RecommendationEffectivenessResponse(
                recommendation_id=rec_id,
                action_id=str(action.id) if action else None,
                merchant_id=merchant_id,
                action_type=action_type,
                title=rec_title,
                merchant_decision="REJECTED",
                execution_status=None,
                outcome_classification=None,
                merchant_rating=None,
                effectiveness=RecommendationEffectiveness.REJECTED.value,
                explanation=f"Recommendation '{rec_title}' was rejected by the merchant; action was not executed.",
                timeline=timeline
            )

        if rec_status_str == "EXPIRED" or has_expired_signal:
            return RecommendationEffectivenessResponse(
                recommendation_id=rec_id,
                action_id=str(action.id) if action else None,
                merchant_id=merchant_id,
                action_type=action_type,
                title=rec_title,
                merchant_decision="EXPIRED",
                execution_status=None,
                outcome_classification=None,
                merchant_rating=None,
                effectiveness=RecommendationEffectiveness.EXPIRED.value,
                explanation=f"Recommendation '{rec_title}' expired before merchant response.",
                timeline=timeline
            )

        # 2. Check Execution
        if action:
            act_status_str = str(action.status.value if hasattr(action.status, "value") else action.status).upper()
            timeline["action_id"] = str(action.id)
            timeline["execution_status"] = act_status_str
            timeline["executed_at"] = action.executed_at.isoformat() if action.executed_at else None

            if act_status_str == "FAILED":
                return RecommendationEffectivenessResponse(
                    recommendation_id=rec_id,
                    action_id=str(action.id),
                    merchant_id=merchant_id,
                    action_type=action_type,
                    title=rec_title,
                    merchant_decision="APPROVED",
                    execution_status="FAILED",
                    outcome_classification=None,
                    merchant_rating=None,
                    effectiveness=RecommendationEffectiveness.EXECUTION_FAILED.value,
                    explanation=f"Recommendation '{rec_title}' was approved, but execution encountered a technical failure.",
                    timeline=timeline
                )

            if act_status_str != "EXECUTED":
                return RecommendationEffectivenessResponse(
                    recommendation_id=rec_id,
                    action_id=str(action.id),
                    merchant_id=merchant_id,
                    action_type=action_type,
                    title=rec_title,
                    merchant_decision="APPROVED",
                    execution_status=act_status_str,
                    outcome_classification=None,
                    merchant_rating=None,
                    effectiveness=RecommendationEffectiveness.NOT_MEASURED.value,
                    explanation=f"Action '{rec_title}' is currently {act_status_str.lower()}.",
                    timeline=timeline
                )

            timeline["executed"] = True

        # 3. Check Outcome
        merchant_rating = merchant_feedback_signal.merchant_rating if merchant_feedback_signal else None
        if merchant_feedback_signal and merchant_feedback_signal.merchant_feedback_text:
            timeline["merchant_notes"] = merchant_feedback_signal.merchant_feedback_text

        if not outcome or str(outcome.status).upper() in ["PENDING", "MEASURING", "INSUFFICIENT_DATA"]:
            outcome_stat = str(outcome.status) if outcome else "UNMEASURED"
            timeline["outcome_status"] = outcome_stat
            return RecommendationEffectivenessResponse(
                recommendation_id=rec_id,
                action_id=str(action.id) if action else None,
                merchant_id=merchant_id,
                action_type=action_type,
                title=rec_title,
                merchant_decision="APPROVED",
                execution_status="EXECUTED",
                outcome_classification=outcome_stat,
                merchant_rating=merchant_rating,
                effectiveness=RecommendationEffectiveness.NOT_MEASURED.value,
                explanation=f"Action executed; observation window is in progress ({outcome_stat}).",
                timeline=timeline
            )

        timeline["measured"] = True
        timeline["outcome_id"] = str(outcome.id)
        timeline["measured_at"] = outcome.measured_at.isoformat() if outcome.measured_at else None
        timeline["impact"] = str(outcome.impact)
        timeline["revenue_change"] = float(outcome.revenue_change or 0.0)
        timeline["stockout_prevented"] = bool(outcome.stockout_prevented)

        impact_str = str(outcome.impact).upper()

        if impact_str == "POSITIVE":
            eff = RecommendationEffectiveness.SUCCESSFUL.value
            expl = f"Recommendation '{rec_title}' achieved its intended business objective with positive measured impact."
        elif impact_str == "NEGATIVE":
            eff = RecommendationEffectiveness.UNSUCCESSFUL.value
            expl = f"Recommendation '{rec_title}' resulted in a negative measured impact vs baseline."
        else:
            eff = RecommendationEffectiveness.PARTIALLY_SUCCESSFUL.value
            expl = f"Recommendation '{rec_title}' executed with neutral baseline variance."

        return RecommendationEffectivenessResponse(
            recommendation_id=rec_id,
            action_id=str(action.id) if action else None,
            merchant_id=merchant_id,
            action_type=action_type,
            title=rec_title,
            merchant_decision="APPROVED",
            execution_status="EXECUTED",
            outcome_classification=impact_str,
            merchant_rating=merchant_rating,
            effectiveness=eff,
            explanation=expl,
            timeline=timeline
        )
