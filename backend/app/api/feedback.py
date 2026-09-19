"""
Paytm Pulse - Phase 13 Feedback Loop & Continuous Learning API
Endpoints for feedback signal ingestion, subjective merchant ratings, effectiveness queries, and offline dataset export.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.feedback.service import FeedbackService
from app.feedback.schemas import (
    FeedbackSignalCreate,
    FeedbackSignalResponse,
    MerchantRatingPayload,
    RecommendationEffectivenessResponse,
    ActionTypePerformanceSummary,
    MerchantFeedbackSummary,
    LearningDatasetRow
)

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("", response_model=FeedbackSignalResponse, status_code=status.HTTP_201_CREATED)
def record_feedback_signal(
    payload: FeedbackSignalCreate,
    db: Session = Depends(get_db)
):
    """
    Ingests an operational feedback signal into the closed-loop learning infrastructure.
    Guarantees state validation and idempotency.
    """
    try:
        service = FeedbackService(db)
        return service.record_signal(payload)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/merchant-rating", response_model=FeedbackSignalResponse, status_code=status.HTTP_201_CREATED)
def record_merchant_rating(
    payload: MerchantRatingPayload,
    db: Session = Depends(get_db)
):
    """
    Records subjective merchant feedback (USEFUL / NOT_USEFUL, star rating, comment)
    on a specific recommendation or action.
    """
    try:
        service = FeedbackService(db)
        return service.record_merchant_rating(payload)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/recommendation/{recommendation_id}/effectiveness", response_model=RecommendationEffectivenessResponse)
def get_recommendation_effectiveness(
    recommendation_id: str,
    db: Session = Depends(get_db)
):
    """
    Evaluates and returns the complete lifecycle journey and effectiveness of a recommendation.
    """
    service = FeedbackService(db)
    result = service.get_recommendation_effectiveness(recommendation_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Recommendation '{recommendation_id}' not found.")
    return result


@router.get("/recommendation/{recommendation_id}", response_model=List[FeedbackSignalResponse])
def get_signals_by_recommendation(
    recommendation_id: str,
    db: Session = Depends(get_db)
):
    """
    Retrieves all feedback signals associated with a specific recommendation ID.
    """
    service = FeedbackService(db)
    return service.get_signals_for_recommendation(recommendation_id)


@router.get("/action/{action_id}", response_model=List[FeedbackSignalResponse])
def get_signals_by_action(
    action_id: str,
    db: Session = Depends(get_db)
):
    """
    Retrieves all feedback signals associated with a specific action ID.
    """
    service = FeedbackService(db)
    return service.get_signals_for_action(action_id)


@router.get("/merchant/{merchant_id}/summary", response_model=MerchantFeedbackSummary)
def get_merchant_feedback_summary(
    merchant_id: str,
    lookback_days: int = Query(90, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """
    Aggregates acceptance rates, execution success, business impact, and subjective ratings for a merchant.
    """
    service = FeedbackService(db)
    return service.get_merchant_summary(merchant_id, lookback_days=lookback_days)


@router.get("/merchant/{merchant_id}", response_model=List[FeedbackSignalResponse])
def get_merchant_signals(
    merchant_id: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Retrieves paginated raw feedback signals for a merchant.
    """
    service = FeedbackService(db)
    return service.get_merchant_signals(merchant_id, limit=limit, offset=offset)


@router.get("/action-types", response_model=List[ActionTypePerformanceSummary])
def get_action_types_performance(
    lookback_days: int = Query(90, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """
    Retrieves system-wide historical performance and scoring adjustments across all action types.
    """
    service = FeedbackService(db)
    return service.get_action_type_performance(lookback_days=lookback_days)


@router.get("/dataset", response_model=List[LearningDatasetRow])
def get_learning_dataset(
    lookback_days: int = Query(90, ge=1, le=365),
    limit: int = Query(500, ge=1, le=5000),
    db: Session = Depends(get_db)
):
    """
    Exports a structured offline ML training dataset connecting recommendation features to observed outcomes.
    """
    service = FeedbackService(db)
    return service.export_learning_dataset(lookback_days=lookback_days, limit=limit)


@router.get("/{feedback_id}", response_model=FeedbackSignalResponse)
def get_feedback_signal(
    feedback_id: str,
    db: Session = Depends(get_db)
):
    """
    Retrieves a single feedback signal by its UUID.
    """
    service = FeedbackService(db)
    signal = service.get_signal(feedback_id)
    if not signal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Feedback signal '{feedback_id}' not found.")
    return signal
