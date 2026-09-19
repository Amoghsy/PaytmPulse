import json
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.feedback_signal import FeedbackSignal
from app.models.recommendation import Recommendation
from app.models.action import Action
from app.models.outcome import Outcome
from app.models.business_event import BusinessEvent
from app.feedback.config import FeedbackType, FEEDBACK_CACHE_TTL_SECONDS
from app.feedback.schemas import (
    FeedbackSignalCreate,
    FeedbackSignalResponse,
    MerchantRatingPayload,
    MerchantFeedbackSummary,
    ActionTypePerformanceSummary,
    RecommendationEffectivenessResponse,
    LearningDatasetRow
)
from app.feedback.effectiveness import EffectivenessCalculator
from app.feedback.aggregator import FeedbackAggregator
from app.core.redis import get_redis_client

logger = logging.getLogger("paytm_pulse.feedback.service")


class FeedbackService:
    """
    Core service managing feedback signal ingestion, validation, idempotency,
    effectiveness calculations, and learning dataset generation.
    """

    def __init__(self, db: Session):
        self.db = db
        self.aggregator = FeedbackAggregator(db)

    def record_feedback(self, payload: FeedbackSignalCreate) -> FeedbackSignalResponse:
        """
        Ingests a new feedback signal with validation, idempotency checks, and cache invalidation.
        """
        fb_type = payload.feedback_type.value if hasattr(payload.feedback_type, "value") else str(payload.feedback_type)
        payload.feedback_type = fb_type

        # 1. State Validation Checks
        if (payload.outcome_id or fb_type in ["POSITIVE_OUTCOME", "NEGATIVE_OUTCOME", "NEUTRAL_OUTCOME", "INSUFFICIENT_DATA"]) and not payload.action_id:
            raise ValueError("Positive outcome feedback requires an associated action_id")

        # 2. Idempotency Check
        query = self.db.query(FeedbackSignal).filter(
            FeedbackSignal.merchant_id == payload.merchant_id,
            FeedbackSignal.feedback_type == payload.feedback_type
        )
        if payload.recommendation_id:
            query = query.filter(FeedbackSignal.recommendation_id == payload.recommendation_id)
        if payload.action_id:
            query = query.filter(FeedbackSignal.action_id == payload.action_id)
        if payload.outcome_id:
            query = query.filter(FeedbackSignal.outcome_id == payload.outcome_id)

        existing = query.first()
        if existing:
            logger.info(f"[FEEDBACK] Idempotency hit: signal {payload.feedback_type} already recorded (ID: {existing.id})")
            return FeedbackSignalResponse.model_validate(existing)

        # 3. Derive Missing Context Fields from Database
        rec = None
        if payload.recommendation_id:
            rec = self.db.query(Recommendation).filter(Recommendation.id == payload.recommendation_id).first()
            if rec and not payload.action_type:
                payload.action_type = rec.suggested_actions if hasattr(rec, "suggested_actions") and rec.suggested_actions else (rec.type.value if hasattr(rec.type, "value") else str(rec.type))
            if rec and payload.recommendation_confidence is None:
                payload.recommendation_confidence = float(rec.confidence) if rec.confidence else 0.85
            if rec and not payload.event_id and rec.event_id:
                payload.event_id = str(rec.event_id)

        if payload.action_id and not payload.action_type:
            action = self.db.query(Action).filter(Action.id == payload.action_id).first()
            if action:
                payload.action_type = action.action_type.value if hasattr(action.action_type, "value") else str(action.action_type)
                if not payload.execution_id and action.execution_id:
                    payload.execution_id = action.execution_id
                if not payload.recommendation_id and action.recommendation_id:
                    payload.recommendation_id = str(action.recommendation_id)

        impact_val = payload.outcome_impact or payload.objective_impact
        meta_dict = payload.metadata_json or payload.metadata_payload or {}
        if payload.revenue_change is not None:
            meta_dict["revenue_change"] = payload.revenue_change
        if payload.stockout_prevented is not None:
            meta_dict["stockout_prevented"] = payload.stockout_prevented
        if payload.customers_recovered is not None:
            meta_dict["customers_recovered"] = payload.customers_recovered

        # 4. Insert Feedback Record
        feedback_obj = FeedbackSignal(
            merchant_id=payload.merchant_id,
            event_id=payload.event_id,
            recommendation_id=payload.recommendation_id,
            action_id=payload.action_id,
            execution_id=payload.execution_id,
            outcome_id=payload.outcome_id,
            action_type=payload.action_type,
            recommendation_confidence=payload.recommendation_confidence,
            merchant_decision=payload.merchant_decision,
            execution_status=payload.execution_status,
            outcome_type=payload.outcome_type,
            outcome_classification=payload.outcome_classification,
            outcome_impact=impact_val,
            outcome_confidence=payload.outcome_confidence,
            feedback_type=payload.feedback_type,
            merchant_rating=payload.merchant_rating,
            merchant_feedback_text=payload.merchant_feedback_text,
            metadata_json=meta_dict
        )
        self.db.add(feedback_obj)
        self.db.commit()
        self.db.refresh(feedback_obj)

        logger.info(
            f"[FEEDBACK] Recorded signal {payload.feedback_type} for merchant {payload.merchant_id} "
            f"(Recommendation: {payload.recommendation_id}, Action: {payload.action_id})"
        )

        # 5. Fast Memory Invalidation & Context Update
        self._invalidate_feedback_cache(payload.merchant_id)

        return FeedbackSignalResponse.model_validate(feedback_obj)

    record_signal = record_feedback

    def record_merchant_rating(
        self,
        payload_or_merchant_id: Any,
        rating: Optional[str] = None,
        recommendation_id: Optional[str] = None,
        action_id: Optional[str] = None,
        feedback_text: Optional[str] = None,
        stars: Optional[int] = None,
        rating_useful: Optional[bool] = None,
        feedback_comment: Optional[str] = None
    ) -> FeedbackSignalResponse:
        """
        Records subjective merchant feedback (e.g. thumbs up / down from WhatsApp or web).
        """
        meta_dict = {}
        if isinstance(payload_or_merchant_id, MerchantRatingPayload):
            m_id = payload_or_merchant_id.merchant_id
            rat = payload_or_merchant_id.rating or ("USEFUL" if payload_or_merchant_id.rating_useful else "NOT_USEFUL")
            rec_id = payload_or_merchant_id.recommendation_id
            act_id = payload_or_merchant_id.action_id
            fb_txt = payload_or_merchant_id.feedback_text or payload_or_merchant_id.feedback_comment
            if payload_or_merchant_id.stars is not None:
                meta_dict["stars"] = payload_or_merchant_id.stars
        elif hasattr(payload_or_merchant_id, "merchant_id"):
            m_id = str(payload_or_merchant_id.merchant_id)
            rat = getattr(payload_or_merchant_id, "rating", None) or ("USEFUL" if getattr(payload_or_merchant_id, "rating_useful", False) else "NOT_USEFUL")
            rec_id = str(payload_or_merchant_id.recommendation_id) if getattr(payload_or_merchant_id, "recommendation_id", None) else None
            act_id = str(payload_or_merchant_id.action_id) if getattr(payload_or_merchant_id, "action_id", None) else None
            fb_txt = getattr(payload_or_merchant_id, "feedback_text", None) or getattr(payload_or_merchant_id, "feedback_comment", None)
            if getattr(payload_or_merchant_id, "stars", None) is not None:
                meta_dict["stars"] = getattr(payload_or_merchant_id, "stars")
        elif isinstance(payload_or_merchant_id, dict):
            m_id = payload_or_merchant_id.get("merchant_id")
            rat = payload_or_merchant_id.get("rating") or ("USEFUL" if payload_or_merchant_id.get("rating_useful") else "NOT_USEFUL")
            rec_id = payload_or_merchant_id.get("recommendation_id")
            act_id = payload_or_merchant_id.get("action_id")
            fb_txt = payload_or_merchant_id.get("feedback_text") or payload_or_merchant_id.get("feedback_comment")
            if payload_or_merchant_id.get("stars") is not None:
                meta_dict["stars"] = payload_or_merchant_id.get("stars")
        else:
            m_id = payload_or_merchant_id
            rat = rating or ("USEFUL" if rating_useful else "NOT_USEFUL")
            rec_id = recommendation_id
            act_id = action_id
            fb_txt = feedback_text or feedback_comment
            if stars is not None:
                meta_dict["stars"] = stars

        rating_upper = str(rat).upper() if rat else "USEFUL"
        is_pos = rating_upper in ["USEFUL", "POSITIVE", "YES", "THUMBS_UP", "TRUE"]
        feedback_type = FeedbackType.MERCHANT_RATING.value if hasattr(FeedbackType, "MERCHANT_RATING") else FeedbackType.MERCHANT_FEEDBACK_POSITIVE.value
        norm_rating = "USEFUL" if is_pos else "NOT_USEFUL"

        payload = FeedbackSignalCreate(
            merchant_id=m_id,
            recommendation_id=rec_id,
            action_id=act_id,
            feedback_type=feedback_type,
            merchant_rating=norm_rating,
            merchant_feedback_text=fb_txt,
            metadata_json=meta_dict
        )
        return self.record_feedback(payload)

    def get_feedback_by_id(self, feedback_id: str) -> Optional[FeedbackSignalResponse]:
        sig = self.db.query(FeedbackSignal).filter(FeedbackSignal.id == feedback_id).first()
        return FeedbackSignalResponse.model_validate(sig) if sig else None

    get_signal = get_feedback_by_id

    def get_feedback_for_recommendation(self, recommendation_id: str) -> List[FeedbackSignalResponse]:
        signals = self.db.query(FeedbackSignal).filter(
            FeedbackSignal.recommendation_id == recommendation_id
        ).order_by(FeedbackSignal.created_at.asc()).all()
        return [FeedbackSignalResponse.model_validate(s) for s in signals]

    get_signals_for_recommendation = get_feedback_for_recommendation

    def get_feedback_for_action(self, action_id: str) -> List[FeedbackSignalResponse]:
        signals = self.db.query(FeedbackSignal).filter(
            FeedbackSignal.action_id == action_id
        ).order_by(FeedbackSignal.created_at.asc()).all()
        return [FeedbackSignalResponse.model_validate(s) for s in signals]

    get_signals_for_action = get_feedback_for_action

    def get_merchant_feedback(
        self,
        merchant_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[FeedbackSignalResponse]:
        signals = self.db.query(FeedbackSignal).filter(
            FeedbackSignal.merchant_id == merchant_id
        ).order_by(FeedbackSignal.created_at.desc()).offset(offset).limit(limit).all()
        return [FeedbackSignalResponse.model_validate(s) for s in signals]

    get_merchant_signals = get_merchant_feedback

    def get_merchant_summary(self, merchant_id: str, lookback_days: int = 90) -> MerchantFeedbackSummary:
        """
        Retrieves aggregated feedback summary with Redis fast-memory caching.
        """
        r = get_redis_client()
        cache_key = f"merchant:{merchant_id}:feedback_summary"
        if r:
            try:
                cached = r.get(cache_key)
                if cached:
                    return MerchantFeedbackSummary.model_validate(json.loads(cached))
            except Exception as e:
                logger.warning(f"Failed to read feedback summary from Redis: {e}")

        summary = self.aggregator.get_merchant_feedback_summary(merchant_id)

        if r:
            try:
                r.set(cache_key, json.dumps(summary.model_dump(mode="json")), ex=FEEDBACK_CACHE_TTL_SECONDS)
            except Exception as e:
                logger.warning(f"Failed to cache feedback summary in Redis: {e}")

        return summary

    def get_action_type_performance(self, action_type: Optional[str] = None, lookback_days: int = 90) -> Any:
        if action_type:
            return self.aggregator.get_action_type_performance(action_type)
        return self.get_all_action_type_performances()

    def get_all_action_type_performances(self) -> List[ActionTypePerformanceSummary]:
        action_types = ["RESTOCK_PRODUCT", "RUN_PROMOTION", "CUSTOMER_WINBACK", "CREATE_BUNDLE", "CROSS_SELL", "MONITOR_TREND"]
        return [self.aggregator.get_action_type_performance(at) for at in action_types]

    def get_recommendation_effectiveness(self, recommendation_id: str) -> RecommendationEffectivenessResponse:
        """
        Calculates end-to-end effectiveness for a recommendation.
        """
        rec = self.db.query(Recommendation).filter(Recommendation.id == recommendation_id).first()
        if not rec:
            raise ValueError(f"Recommendation '{recommendation_id}' not found.")

        action = self.db.query(Action).filter(Action.recommendation_id == recommendation_id).first()
        outcome = self.db.query(Outcome).filter(Outcome.action_id == action.id).first() if action else None
        
        all_signals = self.db.query(FeedbackSignal).filter(
            FeedbackSignal.recommendation_id == recommendation_id
        ).all()
        has_expired = any(s.feedback_type in ["EXPIRED", "RECOMMENDATION_EXPIRED"] or s.merchant_decision == "EXPIRED" for s in all_signals)
        subj_sig = next((s for s in all_signals if s.merchant_rating is not None), None)

        return EffectivenessCalculator.calculate(
            rec=rec,
            action=action,
            outcome=outcome,
            merchant_feedback_signal=subj_sig,
            has_expired_signal=has_expired
        )

    def get_learning_dataset(self, lookback_days: int = 90, limit: int = 500) -> List[LearningDatasetRow]:
        """
        Generates structured dataset for offline ML model analysis and ranking improvement.
        """
        records = self.db.query(FeedbackSignal).filter(
            FeedbackSignal.outcome_id.isnot(None)
        ).order_by(FeedbackSignal.created_at.desc()).limit(limit).all()

        rows = []
        for sig in records:
            event_type = None
            if sig.event_id:
                ev = self.db.query(BusinessEvent).filter(BusinessEvent.id == sig.event_id).first()
                if ev:
                    event_type = ev.event_type.value if hasattr(ev.event_type, "value") else str(ev.event_type)

            rows.append(LearningDatasetRow(
                merchant_id=sig.merchant_id,
                event_type=event_type,
                action_type=sig.action_type,
                recommendation_confidence=float(sig.recommendation_confidence) if sig.recommendation_confidence else None,
                urgency=sig.metadata_json.get("urgency") if sig.metadata_json else None,
                estimated_impact=sig.metadata_json.get("estimated_impact") if sig.metadata_json else None,
                merchant_decision=sig.merchant_decision,
                execution_status=sig.execution_status,
                outcome_type=sig.outcome_type,
                outcome_classification=sig.outcome_classification,
                observed_impact=sig.outcome_impact,
                outcome_confidence=sig.outcome_confidence,
                merchant_feedback=sig.merchant_rating,
                effectiveness=sig.metadata_json.get("effectiveness") if sig.metadata_json else None,
                created_at=sig.created_at
            ))

        return rows

    export_learning_dataset = get_learning_dataset

    def _invalidate_feedback_cache(self, merchant_id: str):
        r = get_redis_client()
        if not r:
            return
        try:
            r.delete(f"merchant:{merchant_id}:feedback_summary")
        except Exception as e:
            logger.warning(f"Failed to invalidate feedback cache for {merchant_id}: {e}")
