import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.action import Action, ActionStatus
from app.models.outcome import Outcome
from app.models.recommendation import Recommendation
from app.models.business_event import BusinessEvent
from app.outcomes.baseline import BaselineCapturer
from app.outcomes.collector import OutcomeDataCollector
from app.outcomes.impact_calculator import ImpactCalculator
from app.outcomes.classifier import OutcomeClassifier
from app.outcomes.scheduler import OutcomeScheduler
from app.outcomes.schemas import (
    OutcomeResponse,
    OutcomeTraceResponse,
    MerchantOutcomeSummary,
    OutcomeStatus as StatusEnum,
    OutcomeImpact
)

logger = logging.getLogger("paytm_pulse.outcomes.service")


class OutcomeService:
    """
    Main closed-loop outcome measurement orchestrator.
    """

    def __init__(self, db: Session):
        self.db = db
        self.baseline_capturer = BaselineCapturer(db)
        self.data_collector = OutcomeDataCollector(db)
        self.impact_calculator = ImpactCalculator()
        self.classifier = OutcomeClassifier()

    def measure_action_outcome(
        self,
        action_id: str,
        allow_immediate: bool = True
    ) -> OutcomeResponse:
        """
        Measure and record the empirical business outcome of an executed action.
        """
        action = self.db.query(Action).filter(Action.id == action_id).first()
        if not action:
            raise ValueError(f"Action '{action_id}' not found.")

        # Check readiness
        ready, elapsed_hours, reason = OutcomeScheduler.is_action_ready_for_measurement(
            action, allow_immediate_demo=allow_immediate
        )
        if not ready:
            raise ValueError(f"Action '{action_id}' is not ready for measurement: {reason}")

        # Acquire lock
        if not OutcomeScheduler.acquire_measurement_lock(action_id):
            logger.warning(f"Measurement lock active for action {action_id}. Fetching existing outcome.")
            existing = self.get_outcome_by_action(action_id)
            if existing:
                return existing

        try:
            # 1. Capture / recover baseline
            baseline = self.baseline_capturer.capture_baseline(action)

            # 2. Collect post-action observation data
            observed = self.data_collector.collect(action, baseline)

            # 3. Calculate baseline-adjusted impact
            impact_res = self.impact_calculator.calculate(action, baseline, observed)

            # 4. Classify outcome & confidence
            action_type = str(action.action_type.value if hasattr(action.action_type, "value") else action.action_type)
            impact, confidence, learning_signal = self.classifier.classify(
                impact_res, observed, baseline, action_type
            )

            # 5. Persist to PostgreSQL (Upsert to prevent duplicate outcome records)
            outcome = self.db.query(Outcome).filter(Outcome.action_id == action_id).first()
            now = datetime.now(timezone.utc)

            if not outcome:
                outcome = Outcome(
                    action_id=action_id,
                    outcome_type=impact_res.outcome_type.value,
                    status=StatusEnum.MEASURED.value if impact != OutcomeImpact.INSUFFICIENT_DATA else StatusEnum.INSUFFICIENT_DATA.value,
                    confidence=confidence.value,
                    sales_before=impact_res.sales_before,
                    sales_after=impact_res.sales_after,
                    revenue_change=impact_res.revenue_change,
                    stockout_prevented=impact_res.stockout_prevented,
                    customers_recovered=impact_res.customers_recovered,
                    offer_conversion=impact_res.offer_conversion,
                    impact=impact.value,
                    baseline_metrics=baseline.model_dump(mode="json"),
                    observed_metrics=observed.model_dump(mode="json"),
                    learning_signals=learning_signal.model_dump(mode="json"),
                    measured_at=now
                )
                self.db.add(outcome)
            else:
                outcome.outcome_type = impact_res.outcome_type.value
                outcome.status = StatusEnum.MEASURED.value if impact != OutcomeImpact.INSUFFICIENT_DATA else StatusEnum.INSUFFICIENT_DATA.value
                outcome.confidence = confidence.value
                outcome.sales_before = impact_res.sales_before
                outcome.sales_after = impact_res.sales_after
                outcome.revenue_change = impact_res.revenue_change
                outcome.stockout_prevented = impact_res.stockout_prevented
                outcome.customers_recovered = impact_res.customers_recovered
                outcome.offer_conversion = impact_res.offer_conversion
                outcome.impact = impact.value
                outcome.baseline_metrics = baseline.model_dump(mode="json")
                outcome.observed_metrics = observed.model_dump(mode="json")
                outcome.learning_signals = learning_signal.model_dump(mode="json")
                outcome.measured_at = now

            self.db.commit()
            self.db.refresh(outcome)

            # Phase 11 & 12 Fast Memory update & invalidation hooks
            try:
                from app.core.redis import get_redis_client
                from app.memory.cache import IntelligenceCache
                from app.memory.session_memory import SessionMemory
                import json

                r = get_redis_client()
                if r:
                    m_id = str(action.merchant_id)
                    # Cache status for fast lookup
                    r.set(f"action:{action_id}:measurement_status", outcome.status, ex=86400)
                    r.hset(f"merchant:{m_id}:active_outcomes", str(outcome.id), json.dumps({
                        "id": str(outcome.id),
                        "action_id": str(action_id),
                        "outcome_type": str(outcome.outcome_type),
                        "status": str(outcome.status),
                        "impact": str(outcome.impact),
                        "revenue_change": float(outcome.revenue_change or 0.0),
                        "stockout_prevented": bool(outcome.stockout_prevented),
                        "customers_recovered": int(outcome.customers_recovered or 0),
                        "measured_at": outcome.measured_at.isoformat()
                    }))
                    r.expire(f"merchant:{m_id}:active_outcomes", 86400)

                IntelligenceCache.invalidate_all(str(action.merchant_id))
                SessionMemory.update_session(str(action.merchant_id), last_action="outcome_measured")
            except Exception as mem_err:
                logger.warning(f"Memory update non-fatal error on outcome measurement: {mem_err}")

            # Phase 13 Feedback Signal hook
            try:
                from app.feedback.service import FeedbackService
                from app.feedback.config import FeedbackType
                from app.feedback.schemas import FeedbackSignalCreate

                fb_type = FeedbackType.NEUTRAL_OUTCOME
                if outcome.impact == "POSITIVE":
                    fb_type = FeedbackType.POSITIVE_OUTCOME
                elif outcome.impact == "NEGATIVE":
                    fb_type = FeedbackType.NEGATIVE_OUTCOME
                elif outcome.impact == "INSUFFICIENT_DATA":
                    fb_type = FeedbackType.INSUFFICIENT_DATA

                # Fetch rec event_id if available
                rec_event_id = None
                if action.recommendation_id:
                    rec_obj = self.db.query(Recommendation).filter(Recommendation.id == action.recommendation_id).first()
                    if rec_obj and rec_obj.event_id:
                        rec_event_id = str(rec_obj.event_id)

                FeedbackService(self.db).record_signal(
                    FeedbackSignalCreate(
                        merchant_id=str(action.merchant_id),
                        recommendation_id=str(action.recommendation_id) if action.recommendation_id else None,
                        action_id=str(action.id),
                        execution_id=str(action.execution_id) if action.execution_id else None,
                        outcome_id=str(outcome.id),
                        event_id=rec_event_id,
                        feedback_type=fb_type,
                        objective_impact=str(outcome.impact),
                        revenue_change=float(outcome.revenue_change or 0.0),
                        stockout_prevented=bool(outcome.stockout_prevented),
                        customers_recovered=int(outcome.customers_recovered or 0),
                        offer_conversion_rate=float(outcome.offer_conversion) if outcome.offer_conversion is not None else None,
                        metadata_payload={"confidence": str(outcome.confidence), "outcome_type": str(outcome.outcome_type)}
                    )
                )
            except Exception as fb_err:
                logger.warning(f"Feedback recording non-fatal error on outcome measurement: {fb_err}")

            logger.info(
                f"Action {action_id} outcome measured: Impact={outcome.impact}, "
                f"RevenueChange=₹{outcome.revenue_change}, StockoutPrevented={outcome.stockout_prevented}"
            )

            return OutcomeResponse.model_validate(outcome)

        finally:
            OutcomeScheduler.release_measurement_lock(action_id)

    def get_outcome(self, outcome_id: str) -> Optional[OutcomeResponse]:
        outcome = self.db.query(Outcome).filter(Outcome.id == outcome_id).first()
        return OutcomeResponse.model_validate(outcome) if outcome else None

    def get_outcome_by_action(self, action_id: str) -> Optional[OutcomeResponse]:
        outcome = self.db.query(Outcome).filter(Outcome.action_id == action_id).first()
        return OutcomeResponse.model_validate(outcome) if outcome else None

    def get_merchant_outcomes(self, merchant_id: str, limit: int = 50) -> List[OutcomeResponse]:
        outcomes = self.db.query(Outcome).join(Action, Outcome.action_id == Action.id).filter(
            Action.merchant_id == merchant_id
        ).order_by(Outcome.measured_at.desc()).limit(limit).all()

        return [OutcomeResponse.model_validate(o) for o in outcomes]

    def get_merchant_summary(self, merchant_id: str, period_days: int = 30) -> MerchantOutcomeSummary:
        lookback = datetime.now(timezone.utc) - timedelta(days=period_days)
        
        # Total executed actions
        executed_count = self.db.query(func.count(Action.id)).filter(
            Action.merchant_id == merchant_id,
            Action.status == ActionStatus.EXECUTED,
            Action.created_at >= lookback
        ).scalar() or 0

        # Outcomes
        outcomes = self.db.query(Outcome).join(Action, Outcome.action_id == Action.id).filter(
            Action.merchant_id == merchant_id,
            Outcome.measured_at >= lookback
        ).all()

        pos_count = sum(1 for o in outcomes if str(o.impact).upper() == "POSITIVE")
        neu_count = sum(1 for o in outcomes if str(o.impact).upper() == "NEUTRAL")
        neg_count = sum(1 for o in outcomes if str(o.impact).upper() == "NEGATIVE")
        ins_count = sum(1 for o in outcomes if str(o.impact).upper() == "INSUFFICIENT_DATA")

        stockouts_prevented = sum(1 for o in outcomes if o.stockout_prevented)
        customers_recovered = sum(o.customers_recovered or 0 for o in outcomes)
        rev_change = sum(float(o.revenue_change or 0.0) for o in outcomes)

        conversions = [float(o.offer_conversion) for o in outcomes if o.offer_conversion is not None]
        avg_conversion = round(sum(conversions) / len(conversions), 2) if conversions else None

        return MerchantOutcomeSummary(
            merchant_id=merchant_id,
            period=f"last_{period_days}_days",
            actions_executed=executed_count,
            outcomes_measured=len(outcomes),
            positive_outcomes=pos_count,
            neutral_outcomes=neu_count,
            negative_outcomes=neg_count,
            insufficient_data_outcomes=ins_count,
            stockouts_prevented=stockouts_prevented,
            customers_recovered=customers_recovered,
            observed_revenue_change=round(rev_change, 2),
            avg_conversion_rate=avg_conversion
        )

    def get_action_trace(self, action_id: str) -> OutcomeTraceResponse:
        """
        Trace full lineage: BusinessEvent -> Recommendation -> Action -> Execution -> Outcome.
        """
        action = self.db.query(Action).filter(Action.id == action_id).first()
        if not action:
            raise ValueError(f"Action '{action_id}' not found.")

        outcome = self.db.query(Outcome).filter(Outcome.action_id == action_id).first()
        recommendation = self.db.query(Recommendation).filter(
            Recommendation.id == action.recommendation_id
        ).first() if action.recommendation_id else None

        event = self.db.query(BusinessEvent).filter(
            BusinessEvent.id == recommendation.event_id
        ).first() if (recommendation and recommendation.event_id) else None

        learning_summary = None
        if outcome and outcome.learning_signals:
            learning_summary = outcome.learning_signals.get("signal")

        return OutcomeTraceResponse(
            outcome_id=outcome.id if outcome else "UNMEASURED",
            action_id=action.id,
            execution_id=action.execution_id,
            recommendation_id=action.recommendation_id,
            event_id=event.id if event else None,
            merchant_id=action.merchant_id,
            action_type=str(action.action_type.value if hasattr(action.action_type, "value") else action.action_type),
            status=str(action.status.value if hasattr(action.status, "value") else action.status),
            impact=outcome.impact if outcome else None,
            revenue_change=float(outcome.revenue_change) if outcome and outcome.revenue_change else None,
            stockout_prevented=outcome.stockout_prevented if outcome else False,
            customers_recovered=outcome.customers_recovered if outcome else 0,
            learning_summary=learning_summary,
            action_details={
                "parameters": action.parameters,
                "executed_at": action.executed_at.isoformat() if action.executed_at else None,
                "execution_result": action.execution_result
            },
            recommendation_details={
                "title": recommendation.title,
                "urgency": recommendation.urgency,
                "impact": recommendation.expected_impact,
                "reasoning": recommendation.reason
            } if recommendation else None,
            event_details={
                "event_type": event.event_type.value if hasattr(event.event_type, "value") else event.event_type,
                "severity": event.severity.value if hasattr(event.severity, "value") else event.severity,
                "payload": event.payload
            } if event else None
        )

    def format_whatsapp_followup(self, outcome: Outcome) -> str:
        """
        Generates a concise, WhatsApp-friendly outcome follow-up message for the merchant.
        """
        action = outcome.action
        act_type = str(action.action_type.value if hasattr(action.action_type, "value") else action.action_type).upper() if action else "ACTION"
        product_name = (action.parameters or {}).get("product_name") if action else None
        action_desc = f"{product_name} reorder" if (act_type in ["REORDER", "RESTOCK_PRODUCT"] and product_name) else act_type.lower()
        
        lines = ["📊 *Action Result*", ""]
        
        if outcome.impact == "POSITIVE":
            lines.append(f"Your {action_desc} was completed.")
            lines.append("\nDuring the measurement period:")
            if outcome.stockout_prevented:
                lines.append("• No stockout was observed")
                lines.append("• Sales remained above the baseline")
            elif outcome.customers_recovered > 0:
                lines.append(f"• {outcome.customers_recovered} customer(s) returned")
                lines.append("• Sales activity recovered")
            else:
                lines.append("• Positive business response recorded")

            if outcome.revenue_change and float(outcome.revenue_change) > 0:
                lines.append(f"• Estimated revenue protected/gained: ₹{float(outcome.revenue_change):,.2f}")
            lines.append("\n*Result: Positive*")

        elif outcome.impact == "NEGATIVE":
            lines.append(f"The {action_desc} was executed.")
            lines.append("\nDuring the measurement period:")
            if outcome.outcome_type == "STOCKOUT_OCCURRED":
                lines.append("• Stockout occurred before demand subsided")
            else:
                lines.append("• Performance trailed behind historical baseline")
            lines.append("\n*Result: Negative*")

        elif outcome.impact == "INSUFFICIENT_DATA":
            lines.append(f"The {action_desc} was completed successfully.")
            lines.append("\nThere isn't enough new sales data yet to measure the business impact.")
            lines.append("I'll continue tracking it.")

        else:
            lines.append(f"Your {action_desc} was completed.")
            lines.append("\nObserved metrics remained in line with normal baseline variance.")
            lines.append("\n*Result: Neutral*")

        return "\n".join(lines)
