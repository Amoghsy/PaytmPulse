"""
Paytm Pulse - Phase 13 Feedback Loop & Continuous Learning Test Suite
Validates 6-stage lineage, objective vs subjective feedback, lifecycle effectiveness,
decision scoring adjustments, agent tools, REST APIs, and merchant isolation.
"""

import uuid
import json
import pytest
from datetime import datetime, timezone, timedelta

from app.models.merchant import Merchant, MerchantCategory
from app.models.recommendation import Recommendation, RecommendationType, RecommendationStatus
from app.models.action import Action, ActionType, ActionStatus
from app.models.outcome import Outcome
from app.outcomes.schemas import OutcomeType
from app.models.feedback_signal import FeedbackSignal
from app.feedback.config import FeedbackType, RecommendationEffectiveness, MAX_FEEDBACK_ADJUSTMENT
from app.feedback.schemas import FeedbackSignalCreate, MerchantRatingPayload
from app.feedback.service import FeedbackService
from app.feedback.effectiveness import EffectivenessCalculator
from app.feedback.aggregator import FeedbackAggregator
from app.decision.action_scorer import score_and_rank_actions
from app.decision.schemas import NextBestAction, EstimatedImpact
from app.decision.context_builder import build_decision_context, DecisionContext
from app.agent.tools.feedback_tools import get_recommendation_feedback, get_merchant_feedback_summary


@pytest.fixture
def sample_merchant(db_session):
    merchant = Merchant(
        name="Sharmaji",
        shop_name="Sharma General Store",
        category=MerchantCategory.KIRANA,
        location="Delhi",
        phone="9876543210"
    )
    db_session.add(merchant)
    db_session.commit()
    db_session.refresh(merchant)
    return merchant


@pytest.fixture
def sample_merchant_b(db_session):
    merchant = Merchant(
        name="Guptaji",
        shop_name="Gupta Electronics",
        category=MerchantCategory.ELECTRONICS,
        location="Noida",
        phone="9876543211"
    )
    db_session.add(merchant)
    db_session.commit()
    db_session.refresh(merchant)
    return merchant


def test_positive_outcome_feedback_lifecycle(db_session, sample_merchant):
    """Test full cycle: Generated -> Approved -> Executed -> Positive Outcome -> SUCCESSFUL"""
    m_id = str(sample_merchant.id)
    rec = Recommendation(
        merchant_id=m_id,
        type=RecommendationType.STOCK_REORDER,
        title="Restock Atta 10kg",
        reason="Demand spike expected",
        confidence=0.88,
        urgency="HIGH",
        status=RecommendationStatus.APPROVED
    )
    db_session.add(rec)
    db_session.flush()

    action = Action(
        recommendation_id=rec.id,
        merchant_id=m_id,
        action_type=ActionType.REORDER,
        parameters={"product_id": "p1", "quantity": 10},
        status=ActionStatus.EXECUTED,
        execution_id="exec_101"
    )
    db_session.add(action)
    db_session.flush()

    outcome = Outcome(
        action_id=action.id,
        outcome_type=OutcomeType.REVENUE_INCREASE.value,
        status="MEASURED",
        impact="POSITIVE",
        confidence="HIGH",
        sales_before=1000.0,
        sales_after=1500.0,
        revenue_change=500.0,
        stockout_prevented=True,
        measured_at=datetime.now(timezone.utc)
    )
    db_session.add(outcome)
    db_session.commit()

    service = FeedbackService(db_session)
    # Record approval, execution, and positive outcome signals
    service.record_signal(FeedbackSignalCreate(
        merchant_id=m_id,
        recommendation_id=str(rec.id),
        action_id=str(action.id),
        feedback_type=FeedbackType.MERCHANT_APPROVED
    ))
    service.record_signal(FeedbackSignalCreate(
        merchant_id=m_id,
        recommendation_id=str(rec.id),
        action_id=str(action.id),
        execution_id=str(action.execution_id),
        feedback_type=FeedbackType.ACTION_EXECUTED
    ))
    sig_out = service.record_signal(FeedbackSignalCreate(
        merchant_id=m_id,
        recommendation_id=str(rec.id),
        action_id=str(action.id),
        execution_id=str(action.execution_id),
        outcome_id=str(outcome.id),
        feedback_type=FeedbackType.POSITIVE_OUTCOME,
        objective_impact="POSITIVE",
        revenue_change=500.0,
        stockout_prevented=True
    ))

    assert sig_out.feedback_type == "POSITIVE_OUTCOME"
    assert sig_out.objective_impact == "POSITIVE"

    # Verify effectiveness
    eff = service.get_recommendation_effectiveness(str(rec.id))
    assert eff.effectiveness == RecommendationEffectiveness.SUCCESSFUL.value
    assert eff.is_terminal is True
    assert eff.was_approved is True
    assert eff.was_executed is True
    assert eff.net_revenue_change == 500.0
    assert eff.stockout_prevented is True


def test_negative_outcome_feedback_lifecycle(db_session, sample_merchant):
    """Test cycle: Approved -> Executed -> Negative Outcome -> UNSUCCESSFUL"""
    m_id = str(sample_merchant.id)
    rec = Recommendation(
        merchant_id=m_id,
        type=RecommendationType.PROMOTION,
        title="Run 10% Discount Campaign",
        reason="Sales lull",
        confidence=0.75,
        urgency="MEDIUM",
        status=RecommendationStatus.APPROVED
    )
    db_session.add(rec)
    db_session.flush()

    action = Action(
        recommendation_id=rec.id,
        merchant_id=m_id,
        action_type=ActionType.PROMOTION,
        status=ActionStatus.EXECUTED,
        execution_id="exec_102"
    )
    db_session.add(action)
    db_session.flush()

    outcome = Outcome(
        action_id=action.id,
        outcome_type=OutcomeType.PROMOTION_CONVERSION.value,
        status="MEASURED",
        impact="NEGATIVE",
        confidence="MEDIUM",
        sales_before=2000.0,
        sales_after=1700.0,
        revenue_change=-300.0,
        measured_at=datetime.now(timezone.utc)
    )
    db_session.add(outcome)
    db_session.commit()

    service = FeedbackService(db_session)
    service.record_signal(FeedbackSignalCreate(
        merchant_id=m_id,
        recommendation_id=str(rec.id),
        action_id=str(action.id),
        outcome_id=str(outcome.id),
        feedback_type=FeedbackType.NEGATIVE_OUTCOME,
        objective_impact="NEGATIVE",
        revenue_change=-300.0
    ))

    eff = service.get_recommendation_effectiveness(str(rec.id))
    assert eff.effectiveness == RecommendationEffectiveness.UNSUCCESSFUL.value
    assert eff.net_revenue_change == -300.0


def test_rejection_feedback_lifecycle(db_session, sample_merchant):
    """Test cycle: Generated -> Rejected -> REJECTED"""
    m_id = str(sample_merchant.id)
    rec = Recommendation(
        merchant_id=m_id,
        type=RecommendationType.CUSTOMER_WINBACK,
        title="Send SMS Offer to Lapsed Shoppers",
        reason="Churn prevention",
        confidence=0.60,
        urgency="LOW",
        status=RecommendationStatus.REJECTED
    )
    db_session.add(rec)
    db_session.commit()

    service = FeedbackService(db_session)
    service.record_signal(FeedbackSignalCreate(
        merchant_id=m_id,
        recommendation_id=str(rec.id),
        feedback_type=FeedbackType.MERCHANT_REJECTED
    ))

    eff = service.get_recommendation_effectiveness(str(rec.id))
    assert eff.effectiveness == RecommendationEffectiveness.REJECTED.value
    assert eff.was_approved is False
    assert eff.was_executed is False


def test_expiration_feedback_lifecycle(db_session, sample_merchant):
    """Test cycle: Pending -> Timeout -> EXPIRED"""
    m_id = str(sample_merchant.id)
    rec = Recommendation(
        merchant_id=m_id,
        type=RecommendationType.STOCK_REORDER,
        title="Urgent Milk Reorder",
        reason="Stockout in 30 mins",
        confidence=0.95,
        urgency="CRITICAL",
        status=RecommendationStatus.PENDING
    )
    db_session.add(rec)
    db_session.commit()

    service = FeedbackService(db_session)
    service.record_signal(FeedbackSignalCreate(
        merchant_id=m_id,
        recommendation_id=str(rec.id),
        feedback_type=FeedbackType.EXPIRED
    ))

    eff = service.get_recommendation_effectiveness(str(rec.id))
    assert eff.effectiveness == RecommendationEffectiveness.EXPIRED.value


def test_execution_failure_lifecycle(db_session, sample_merchant):
    """Test cycle: Approved -> Execution Throws Error -> EXECUTION_FAILED"""
    m_id = str(sample_merchant.id)
    rec = Recommendation(
        merchant_id=m_id,
        type=RecommendationType.GROWTH_OPPORTUNITY,
        title="Send Evening Tea Combo Offer",
        reason="Peak footfall",
        confidence=0.82,
        urgency="HIGH",
        status=RecommendationStatus.APPROVED
    )
    db_session.add(rec)
    db_session.flush()

    action = Action(
        recommendation_id=rec.id,
        merchant_id=m_id,
        action_type=ActionType.SEND_OFFER,
        status=ActionStatus.FAILED,
        failure_reason="Gateway connection timeout"
    )
    db_session.add(action)
    db_session.commit()

    service = FeedbackService(db_session)
    service.record_signal(FeedbackSignalCreate(
        merchant_id=m_id,
        recommendation_id=str(rec.id),
        action_id=str(action.id),
        feedback_type=FeedbackType.ACTION_FAILED,
        metadata_payload={"error": "Gateway connection timeout"}
    ))

    eff = service.get_recommendation_effectiveness(str(rec.id))
    assert eff.effectiveness == RecommendationEffectiveness.EXECUTION_FAILED.value
    assert eff.was_executed is False


def test_subjective_merchant_rating(db_session, sample_merchant):
    """Test recording subjective rating and verify separation from objective outcomes"""
    m_id = str(sample_merchant.id)
    rec = Recommendation(
        merchant_id=m_id,
        type=RecommendationType.STOCK_REORDER,
        title="Restock Bread",
        reason="Morning rush",
        confidence=0.90,
        urgency="HIGH",
        status=RecommendationStatus.APPROVED
    )
    db_session.add(rec)
    db_session.commit()

    service = FeedbackService(db_session)
    sig = service.record_merchant_rating(MerchantRatingPayload(
        merchant_id=m_id,
        recommendation_id=str(rec.id),
        rating_useful=True,
        stars=5,
        feedback_comment="Great timing, saved my morning sales!"
    ))

    assert sig.feedback_type == "MERCHANT_RATING"
    assert sig.is_useful is True
    assert sig.user_rating == 5
    assert sig.feedback_notes == "Great timing, saved my morning sales!"

    # Verify effectiveness incorporates subjective rating
    eff = service.get_recommendation_effectiveness(str(rec.id))
    assert eff.merchant_rating == "USEFUL"
    assert eff.merchant_notes == "Great timing, saved my morning sales!"


def test_duplicate_signal_idempotency(db_session, sample_merchant):
    """Test that submitting identical feedback signals does not create duplicate entries"""
    m_id = str(sample_merchant.id)
    rec = Recommendation(
        merchant_id=m_id,
        type=RecommendationType.STOCK_REORDER,
        title="Restock Eggs",
        reason="Low inventory",
        confidence=0.85,
        urgency="MEDIUM",
        status=RecommendationStatus.APPROVED
    )
    db_session.add(rec)
    db_session.commit()

    service = FeedbackService(db_session)
    payload = FeedbackSignalCreate(
        merchant_id=m_id,
        recommendation_id=str(rec.id),
        feedback_type=FeedbackType.MERCHANT_APPROVED
    )

    sig1 = service.record_signal(payload)
    sig2 = service.record_signal(payload)

    assert sig1.id == sig2.id
    signals_count = db_session.query(FeedbackSignal).filter(
        FeedbackSignal.merchant_id == m_id,
        FeedbackSignal.recommendation_id == str(rec.id)
    ).count()
    assert signals_count == 1


def test_state_validation_constraints(db_session, sample_merchant):
    """Test validation errors on invalid signal states (e.g. positive outcome without action)"""
    m_id = str(sample_merchant.id)
    service = FeedbackService(db_session)

    with pytest.raises(ValueError, match="Positive outcome feedback requires an associated action_id"):
        service.record_signal(FeedbackSignalCreate(
            merchant_id=m_id,
            feedback_type=FeedbackType.POSITIVE_OUTCOME,
            objective_impact="POSITIVE"
        ))


def test_bounded_decision_scoring_adjustment(db_session, sample_merchant):
    """Test that feedback adjustments are bounded within [-0.10, +0.10] and require min 2 samples"""
    m_id = str(sample_merchant.id)

    # 1. Action type with NO historical samples -> 0.0 adjustment
    ctx = build_decision_context(merchant_id=m_id, db=db_session)
    candidates = [
        NextBestAction(
            merchant_id=m_id,
            action_type="RESTOCK_PRODUCT",
            title="Restock Tea",
            description="Restock Tea",
            reason="Demand",
            priority="HIGH",
            urgency="HIGH",
            confidence=0.85,
            estimated_impact=EstimatedImpact(type="REVENUE_PROTECTED", value=1500.0),
            parameters={"product_id": "p_tea", "quantity": 10},
            requires_approval=True
        )
    ]
    ranked = score_and_rank_actions(candidates, ctx)
    initial_score = ranked[0].score

    # 2. Insert 3 successful historical outcomes for REORDER
    for i in range(3):
        rec_i = Recommendation(
            merchant_id=m_id,
            type=RecommendationType.STOCK_REORDER,
            title=f"Restock {i}",
            reason="Spike",
            confidence=0.9,
            urgency="HIGH",
            status=RecommendationStatus.APPROVED
        )
        db_session.add(rec_i)
        db_session.flush()

        act_i = Action(
            recommendation_id=rec_i.id,
            merchant_id=m_id,
            action_type=ActionType.REORDER,
            status=ActionStatus.EXECUTED
        )
        db_session.add(act_i)
        db_session.flush()

        out_i = Outcome(
            action_id=act_i.id,
            outcome_type=OutcomeType.STOCKOUT_PREVENTED.value,
            status="MEASURED",
            impact="POSITIVE",
            confidence="HIGH",
            measured_at=datetime.now(timezone.utc)
        )
        db_session.add(out_i)
        db_session.flush()

        sig_i = FeedbackSignal(
            merchant_id=m_id,
            recommendation_id=str(rec_i.id),
            action_id=str(act_i.id),
            action_type="RESTOCK_PRODUCT",
            outcome_id=str(out_i.id),
            feedback_type=FeedbackType.POSITIVE_OUTCOME.value,
            outcome_impact="POSITIVE"
        )
        db_session.add(sig_i)

    db_session.commit()

    # Re-evaluate with historical feedback
    ranked_after = score_and_rank_actions(candidates, ctx)
    # Success rate is 100% (1.0). Adjustment = min(0.10, 0.10 * (1.0 - 0.50)) = +0.05
    assert ranked_after[0].score > initial_score
    assert ranked_after[0].score <= initial_score + MAX_FEEDBACK_ADJUSTMENT + 0.001


def test_merchant_data_isolation(db_session, sample_merchant, sample_merchant_b):
    """Test that Merchant A feedback metrics do not contaminate Merchant B summary"""
    m_a = str(sample_merchant.id)
    m_b = str(sample_merchant_b.id)

    service = FeedbackService(db_session)
    rec_a = Recommendation(
        merchant_id=m_a,
        type=RecommendationType.STOCK_REORDER,
        title="Restock A",
        reason="A",
        confidence=0.8,
        urgency="HIGH",
        status=RecommendationStatus.APPROVED
    )
    db_session.add(rec_a)
    db_session.commit()

    service.record_signal(FeedbackSignalCreate(
        merchant_id=m_a,
        recommendation_id=str(rec_a.id),
        feedback_type=FeedbackType.MERCHANT_APPROVED
    ))

    summary_a = service.get_merchant_summary(m_a)
    summary_b = service.get_merchant_summary(m_b)

    assert summary_a.total_approved == 1
    assert summary_b.total_approved == 0
    assert summary_b.total_recommendations == 0


def test_agent_feedback_tools(db_session, sample_merchant):
    """Test ADK tools for recommendation effectiveness and merchant summary"""
    m_id = str(sample_merchant.id)
    rec = Recommendation(
        merchant_id=m_id,
        type=RecommendationType.STOCK_REORDER,
        title="Restock Rice 5kg",
        reason="Spike",
        confidence=0.85,
        urgency="HIGH",
        status=RecommendationStatus.APPROVED
    )
    db_session.add(rec)
    db_session.commit()

    service = FeedbackService(db_session)
    service.record_signal(FeedbackSignalCreate(
        merchant_id=m_id,
        recommendation_id=str(rec.id),
        feedback_type=FeedbackType.MERCHANT_APPROVED
    ))

    rec_fb_json = get_recommendation_feedback(str(rec.id), db=db_session)
    rec_fb = json.loads(rec_fb_json)
    assert rec_fb["recommendation_id"] == str(rec.id)
    assert rec_fb["was_approved"] is True

    m_summary_json = get_merchant_feedback_summary(m_id, db=db_session)
    m_summary = json.loads(m_summary_json)
    assert m_summary["merchant_id"] == m_id
    assert m_summary["total_approved"] == 1


def test_feedback_rest_api_endpoints(client, db_session, sample_merchant):
    """Test REST API routes: POST signal, POST rating, GET summary, GET action-types, GET dataset"""
    m_id = str(sample_merchant.id)
    rec = Recommendation(
        merchant_id=m_id,
        type=RecommendationType.STOCK_REORDER,
        title="Restock Ghee 1L",
        reason="Festival demand",
        confidence=0.92,
        urgency="HIGH",
        status=RecommendationStatus.APPROVED
    )
    db_session.add(rec)
    db_session.commit()

    # 1. POST /api/v1/feedback
    resp_post = client.post("/api/v1/feedback", json={
        "merchant_id": m_id,
        "recommendation_id": str(rec.id),
        "feedback_type": "MERCHANT_APPROVED"
    })
    assert resp_post.status_code == 201
    created_sig = resp_post.json()
    assert created_sig["feedback_type"] == "MERCHANT_APPROVED"

    # 2. POST /api/v1/feedback/merchant-rating
    resp_rating = client.post("/api/v1/feedback/merchant-rating", json={
        "merchant_id": m_id,
        "recommendation_id": str(rec.id),
        "rating_useful": True,
        "stars": 5,
        "feedback_comment": "Super useful recommendation!"
    })
    assert resp_rating.status_code == 201
    rating_data = resp_rating.json()
    assert rating_data["is_useful"] is True

    # 3. GET /api/v1/feedback/{feedback_id}
    resp_get_sig = client.get(f"/api/v1/feedback/{created_sig['id']}")
    assert resp_get_sig.status_code == 200

    # 4. GET /api/v1/feedback/recommendation/{rec_id}/effectiveness
    resp_eff = client.get(f"/api/v1/feedback/recommendation/{rec.id}/effectiveness")
    assert resp_eff.status_code == 200
    assert resp_eff.json()["was_approved"] is True

    # 5. GET /api/v1/feedback/merchant/{merchant_id}/summary
    resp_sum = client.get(f"/api/v1/feedback/merchant/{m_id}/summary")
    assert resp_sum.status_code == 200
    assert resp_sum.json()["total_approved"] >= 1

    # 6. GET /api/v1/feedback/action-types
    resp_types = client.get("/api/v1/feedback/action-types")
    assert resp_types.status_code == 200
    assert isinstance(resp_types.json(), list)

    # 7. GET /api/v1/feedback/dataset
    resp_ds = client.get("/api/v1/feedback/dataset")
    assert resp_ds.status_code == 200
    assert isinstance(resp_ds.json(), list)
