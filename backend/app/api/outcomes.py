import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.outcomes.service import OutcomeService
from app.outcomes.schemas import (
    OutcomeResponse,
    OutcomeTraceResponse,
    MerchantOutcomeSummary
)

logger = logging.getLogger("paytm_pulse.api.outcomes")

router = APIRouter(prefix="/outcomes", tags=["Outcomes"])


@router.post(
    "/measure/{action_id}",
    response_model=OutcomeResponse,
    status_code=status.HTTP_200_OK,
    summary="Measure Action Outcome",
    description="Deterministically calculate and record the closed-loop business outcome for an executed action."
)
def measure_action_outcome(
    action_id: str,
    allow_immediate: bool = Query(True, description="Allow immediate/progressive measurement for demo"),
    db: Session = Depends(get_db)
):
    service = OutcomeService(db)
    try:
        return service.measure_action_outcome(action_id, allow_immediate=allow_immediate)
    except ValueError as e:
        logger.warning(f"Failed to measure outcome for action {action_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error measuring outcome for action {action_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error measuring outcome: {str(e)}"
        )


@router.get(
    "/{outcome_id}",
    response_model=OutcomeResponse,
    summary="Get Outcome by ID",
    description="Retrieve specific outcome measurement record by ID."
)
def get_outcome(outcome_id: str, db: Session = Depends(get_db)):
    service = OutcomeService(db)
    outcome = service.get_outcome(outcome_id)
    if not outcome:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Outcome '{outcome_id}' not found."
        )
    return outcome


@router.get(
    "/action/{action_id}",
    response_model=OutcomeResponse,
    summary="Get Outcome for Action",
    description="Retrieve outcome measurement linked to a specific action."
)
def get_outcome_for_action(action_id: str, db: Session = Depends(get_db)):
    service = OutcomeService(db)
    outcome = service.get_outcome_by_action(action_id)
    if not outcome:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Outcome for action '{action_id}' not found."
        )
    return outcome


@router.get(
    "/merchant/{merchant_id}",
    response_model=List[OutcomeResponse],
    summary="Get Recent Merchant Outcomes",
    description="Retrieve recent outcome measurements for a merchant."
)
def get_merchant_outcomes(
    merchant_id: str,
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    service = OutcomeService(db)
    return service.get_merchant_outcomes(merchant_id, limit=limit)


@router.get(
    "/merchant/{merchant_id}/summary",
    response_model=MerchantOutcomeSummary,
    summary="Get Merchant Outcome Summary",
    description="Retrieve aggregate outcome metrics, total revenue impact, stockouts prevented, and recovery counts."
)
def get_merchant_outcome_summary(
    merchant_id: str,
    period_days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    service = OutcomeService(db)
    return service.get_merchant_summary(merchant_id, period_days=period_days)


@router.get(
    "/trace/{action_id}",
    response_model=OutcomeTraceResponse,
    summary="Trace Closed-Loop Lineage",
    description="Retrieve complete lineage: BusinessEvent -> Recommendation -> Action -> Execution -> Outcome."
)
def get_outcome_trace(action_id: str, db: Session = Depends(get_db)):
    service = OutcomeService(db)
    try:
        return service.get_action_trace(action_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
