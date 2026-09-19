"""
Paytm Pulse - Phase 6 Next Best Action Decision Engine
Main orchestrator for candidate generation, multi-factor scoring, deduplication, DB persistence, and approval flows.
"""

import json
import logging
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models.base import utc_now
from app.models.recommendation import Recommendation, RecommendationType, RecommendationStatus
from app.models.action import Action, ActionType, ActionStatus
from app.decision.config import DECISION_COOLDOWN_SECONDS
from app.decision.schemas import (
    NextBestAction,
    EstimatedImpact,
    DecisionResponse,
    DecisionActionResponse
)
from app.decision.context_builder import build_decision_context, DecisionContext
from app.decision.action_generator import generate_candidate_actions
from app.decision.action_scorer import score_and_rank_actions
from app.decision.priority import calibrate_priorities

logger = logging.getLogger("paytm_pulse.decision.engine")

ACTION_TYPE_MAP = {
    "RESTOCK_PRODUCT": (RecommendationType.STOCK_REORDER, ActionType.REORDER),
    "RUN_PROMOTION": (RecommendationType.PROMOTION, ActionType.PROMOTION),
    "CUSTOMER_WINBACK": (RecommendationType.CUSTOMER_WINBACK, ActionType.WINBACK),
    "CUSTOMER_RETENTION": (RecommendationType.CUSTOMER_WINBACK, ActionType.WINBACK),
    "CREATE_BUNDLE": (RecommendationType.GROWTH_OPPORTUNITY, ActionType.SEND_OFFER),
    "CROSS_SELL": (RecommendationType.GROWTH_OPPORTUNITY, ActionType.SEND_OFFER),
    "MONITOR_TREND": (RecommendationType.SALES_RECOVERY, ActionType.SEND_OFFER),
    "INVESTIGATE_ANOMALY": (RecommendationType.SALES_RECOVERY, ActionType.SEND_OFFER),
    "FINANCIAL_PRODUCT_RECOMMENDATION": (RecommendationType.FINANCIAL_PRODUCT, ActionType.FINANCIAL_PRODUCT),
}


class DecisionEngine:
    """
    Evaluates business context, generates candidate actions, scores them,
    enforces safety constraints, and manages approval lifecycles.
    """

    def __init__(self, db: Session):
        self.db = db

    def generate_decision(
        self,
        merchant_id: str,
        event_id: Optional[str] = None
    ) -> DecisionResponse:
        """
        Executes end-to-end decision workflow:
        1. Builds DecisionContext
        2. Checks deduplication cooldown
        3. Generates candidate actions
        4. Scores & resolves conflicts
        5. Prioritizes and selects Next Best Action
        6. Persists Recommendation & Action records in PostgreSQL
        """
        start_time = time.time()
        logger.info(f"Decision Engine invoked for merchant_id: {merchant_id}, event_id: {event_id}")

        # 1. Build Context
        ctx = build_decision_context(merchant_id=merchant_id, event_id=event_id, db=self.db)

        # 2. Check Deduplication Cooldown (15 minutes)
        if event_id:
            recent_cutoff = utc_now() - timedelta(seconds=DECISION_COOLDOWN_SECONDS)
            existing_rec = self.db.query(Recommendation).filter(
                Recommendation.merchant_id == merchant_id,
                Recommendation.event_id == event_id,
                Recommendation.status == RecommendationStatus.PENDING,
                Recommendation.created_at >= recent_cutoff
            ).first()

            if existing_rec:
                logger.info(f"Existing pending recommendation {existing_rec.id} found within cooldown window for event {event_id}.")
                return self._format_decision_response_from_db(existing_rec)

        # 3. Generate Candidate Actions
        candidates = generate_candidate_actions(ctx)

        # 4. Score and Rank Actions
        ranked_actions = score_and_rank_actions(candidates, ctx)

        # 5. Calibrate Priority Tiers
        ranked_actions = calibrate_priorities(ranked_actions)

        if not ranked_actions:
            raise ValueError(f"No valid actions could be generated for merchant {merchant_id}")

        next_best = ranked_actions[0]
        alternatives = ranked_actions[1:]

        # 6. Persist Decision into Database
        rec_type, act_type = ACTION_TYPE_MAP.get(next_best.action_type, (RecommendationType.GROWTH_OPPORTUNITY, ActionType.SEND_OFFER))

        db_recommendation = Recommendation(
            merchant_id=merchant_id,
            event_id=event_id,
            type=rec_type,
            title=next_best.title,
            reason=next_best.reason,
            confidence=round(next_best.confidence, 2),
            urgency=next_best.urgency,
            expected_impact=json.dumps(next_best.estimated_impact.model_dump()),
            status=RecommendationStatus.PENDING
        )
        self.db.add(db_recommendation)
        self.db.flush()

        db_action = Action(
            recommendation_id=db_recommendation.id,
            merchant_id=merchant_id,
            action_type=act_type,
            parameters=next_best.parameters,
            status=ActionStatus.PENDING
        )
        self.db.add(db_action)
        self.db.commit()
        self.db.refresh(db_recommendation)

        # Attach persisted database IDs
        next_best.id = str(db_recommendation.id)
        next_best.recommendation_id = str(db_recommendation.id)
        next_best.status = "PENDING_APPROVAL"
        next_best.created_at = db_recommendation.created_at.isoformat() if db_recommendation.created_at else utc_now().isoformat()

        # Phase 11 Fast Memory hook
        try:
            from app.memory.recommendation_memory import RecommendationMemory
            from app.memory.session_memory import SessionMemory
            RecommendationMemory.cache_recommendation(merchant_id, next_best.model_dump())
            SessionMemory.update_session(merchant_id, last_action="decision_generated")
        except Exception as mem_err:
            logger.warning(f"Memory update non-fatal error: {mem_err}")

        duration = (time.time() - start_time) * 1000
        logger.info(
            f"Decision generated successfully: {next_best.action_type} (Score: {next_best.score}, Priority: {next_best.priority}) in {duration:.2f}ms"
        )

        return DecisionResponse(
            merchant_id=merchant_id,
            event_id=event_id,
            next_best_action=next_best,
            alternative_actions=alternatives,
            total_candidates=len(ranked_actions),
            created_at=next_best.created_at
        )

    def get_merchant_decisions(self, merchant_id: str, limit: int = 20) -> List[NextBestAction]:
        """Returns recent decisions generated for a merchant."""
        records = self.db.query(Recommendation).filter(
            Recommendation.merchant_id == merchant_id
        ).order_by(Recommendation.created_at.desc()).limit(limit).all()

        return [self._convert_db_rec_to_nba(rec) for rec in records]

    def get_pending_decisions(self, merchant_id: str) -> List[NextBestAction]:
        """Returns decisions waiting for merchant review."""
        records = self.db.query(Recommendation).filter(
            Recommendation.merchant_id == merchant_id,
            Recommendation.status == RecommendationStatus.PENDING
        ).order_by(Recommendation.created_at.desc()).all()

        return [self._convert_db_rec_to_nba(rec) for rec in records]

    def get_decision_by_id(self, decision_id: str) -> Optional[NextBestAction]:
        """Retrieves a specific decision by ID."""
        rec = self.db.query(Recommendation).filter(Recommendation.id == decision_id).first()
        if not rec:
            return None
        return self._convert_db_rec_to_nba(rec)

    def approve_decision(self, decision_id: str) -> DecisionActionResponse:
        """
        Transitions decision state from PENDING to APPROVED.
        Does NOT execute external operations in Phase 6.
        """
        rec = self.db.query(Recommendation).filter(Recommendation.id == decision_id).first()
        if not rec:
            raise ValueError(f"Decision '{decision_id}' not found.")

        rec.status = RecommendationStatus.APPROVED
        now_dt = utc_now()

        # Update associated action
        actions = self.db.query(Action).filter(Action.recommendation_id == decision_id).all()
        for act in actions:
            act.status = ActionStatus.APPROVED
            act.approved_at = now_dt

        self.db.commit()
        logger.info(f"Decision {decision_id} successfully APPROVED by merchant.")

        # Phase 11 Fast Memory hook
        try:
            from app.memory.recommendation_memory import RecommendationMemory
            from app.memory.session_memory import SessionMemory
            RecommendationMemory.invalidate_recommendation(str(rec.merchant_id), decision_id)
            SessionMemory.update_session(str(rec.merchant_id), last_action="decision_approved")
        except Exception as mem_err:
            logger.warning(f"Memory update non-fatal error: {mem_err}")

        # Phase 13 Feedback Signal hook
        try:
            from app.feedback.service import FeedbackService
            from app.feedback.config import FeedbackType
            from app.feedback.schemas import FeedbackSignalCreate
            action_id_str = str(actions[0].id) if actions else None
            FeedbackService(self.db).record_signal(
                FeedbackSignalCreate(
                    merchant_id=str(rec.merchant_id),
                    recommendation_id=str(rec.id),
                    action_id=action_id_str,
                    event_id=str(rec.event_id) if rec.event_id else None,
                    feedback_type=FeedbackType.MERCHANT_APPROVED,
                    metadata_payload={"source": "decision_engine_approval"}
                )
            )
        except Exception as fb_err:
            logger.warning(f"Feedback recording non-fatal error on approval: {fb_err}")

        return DecisionActionResponse(
            decision_id=decision_id,
            status="APPROVED",
            message=f"Action '{rec.title}' approved successfully. Ready for scheduled execution."
        )

    def reject_decision(self, decision_id: str) -> DecisionActionResponse:
        """
        Transitions decision state from PENDING to REJECTED.
        """
        rec = self.db.query(Recommendation).filter(Recommendation.id == decision_id).first()
        if not rec:
            raise ValueError(f"Decision '{decision_id}' not found.")

        rec.status = RecommendationStatus.REJECTED

        # Update associated action
        actions = self.db.query(Action).filter(Action.recommendation_id == decision_id).all()
        for act in actions:
            act.status = ActionStatus.REJECTED

        self.db.commit()
        logger.info(f"Decision {decision_id} REJECTED by merchant.")

        # Phase 11 Fast Memory hook
        try:
            from app.memory.recommendation_memory import RecommendationMemory
            from app.memory.session_memory import SessionMemory
            RecommendationMemory.invalidate_recommendation(str(rec.merchant_id), decision_id)
            SessionMemory.update_session(str(rec.merchant_id), last_action="decision_rejected")
        except Exception as mem_err:
            logger.warning(f"Memory update non-fatal error: {mem_err}")

        # Phase 13 Feedback Signal hook
        try:
            from app.feedback.service import FeedbackService
            from app.feedback.config import FeedbackType
            from app.feedback.schemas import FeedbackSignalCreate
            action_id_str = str(actions[0].id) if actions else None
            FeedbackService(self.db).record_signal(
                FeedbackSignalCreate(
                    merchant_id=str(rec.merchant_id),
                    recommendation_id=str(rec.id),
                    action_id=action_id_str,
                    event_id=str(rec.event_id) if rec.event_id else None,
                    feedback_type=FeedbackType.MERCHANT_REJECTED,
                    metadata_payload={"source": "decision_engine_rejection"}
                )
            )
        except Exception as fb_err:
            logger.warning(f"Feedback recording non-fatal error on rejection: {fb_err}")

        return DecisionActionResponse(
            decision_id=decision_id,
            status="REJECTED",
            message=f"Action '{rec.title}' has been rejected."
        )

    # -------------------------------------------------------------------------
    # Helper Converters
    # -------------------------------------------------------------------------

    def _convert_db_rec_to_nba(self, rec: Recommendation) -> NextBestAction:
        """Converts a DB Recommendation record into a NextBestAction schema."""
        action_rec = self.db.query(Action).filter(Action.recommendation_id == rec.id).first()
        parameters = action_rec.parameters if action_rec else {}

        impact_data = {"type": "REVENUE_PROTECTED", "value": 0.0, "currency": "INR"}
        if rec.expected_impact:
            try:
                impact_data = json.loads(rec.expected_impact)
            except Exception:
                pass

        status_str = "PENDING_APPROVAL"
        if rec.status == RecommendationStatus.APPROVED:
            status_str = "APPROVED"
        elif rec.status == RecommendationStatus.REJECTED:
            status_str = "REJECTED"

        # Reverse lookup action_type string
        action_type_str = "MONITOR_TREND"
        for k, v in ACTION_TYPE_MAP.items():
            if v[0] == rec.type:
                action_type_str = k
                break

        return NextBestAction(
            id=str(rec.id),
            merchant_id=str(rec.merchant_id),
            event_id=str(rec.event_id) if rec.event_id else None,
            recommendation_id=str(rec.id),
            action_type=action_type_str,
            title=rec.title,
            description=rec.title,
            reason=rec.reason,
            priority=rec.urgency,
            urgency=rec.urgency,
            confidence=float(rec.confidence),
            estimated_impact=EstimatedImpact(**impact_data),
            parameters=parameters,
            requires_approval=True,
            status=status_str,
            created_at=rec.created_at.isoformat() if rec.created_at else None
        )

    def _format_decision_response_from_db(self, rec: Recommendation) -> DecisionResponse:
        nba = self._convert_db_rec_to_nba(rec)
        return DecisionResponse(
            merchant_id=str(rec.merchant_id),
            event_id=str(rec.event_id) if rec.event_id else None,
            next_best_action=nba,
            alternative_actions=[],
            total_candidates=1,
            created_at=nba.created_at or utc_now().isoformat()
        )
