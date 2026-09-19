"""
Paytm Pulse - Phase 6 Decision Engine API Endpoints
Provides REST APIs for Next Best Action generation, decision history, and merchant approval workflows.
"""

import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.decision.engine import DecisionEngine
from app.decision.schemas import (
    GenerateDecisionRequest,
    DecisionResponse,
    NextBestAction,
    DecisionActionResponse
)

logger = logging.getLogger("paytm_pulse.api.decisions")

router = APIRouter(tags=["Decision Engine - Next Best Action"])


@router.post("/decisions/generate", response_model=DecisionResponse, status_code=status.HTTP_200_OK)
def generate_decision_endpoint(
    payload: GenerateDecisionRequest,
    db: Session = Depends(get_db)
):
    """
    Evaluates business events, ML intelligence, and constraints to generate the Next Best Action for a merchant.
    """
    try:
        engine = DecisionEngine(db)
        decision = engine.generate_decision(merchant_id=payload.merchant_id, event_id=payload.event_id)
        return decision
    except ValueError as e:
        logger.warning(f"Validation error in decision generation: {str(e)}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating decision for merchant {payload.merchant_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Decision generation failed: {str(e)}")


@router.get("/decisions/{merchant_id}/pending", response_model=List[NextBestAction], status_code=status.HTTP_200_OK)
def get_pending_decisions_endpoint(
    merchant_id: str,
    db: Session = Depends(get_db)
):
    """
    Retrieves all pending Next Best Actions awaiting merchant approval.
    """
    try:
        engine = DecisionEngine(db)
        return engine.get_pending_decisions(merchant_id)
    except Exception as e:
        logger.error(f"Error fetching pending decisions for merchant {merchant_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch pending decisions")


@router.get("/decisions/{merchant_id}", response_model=List[NextBestAction], status_code=status.HTTP_200_OK)
def get_merchant_decisions_endpoint(
    merchant_id: str,
    db: Session = Depends(get_db)
):
    """
    Retrieves recent decision history for a merchant.
    """
    try:
        engine = DecisionEngine(db)
        return engine.get_merchant_decisions(merchant_id)
    except Exception as e:
        logger.error(f"Error fetching decisions for merchant {merchant_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch decisions")


@router.get("/decisions/detail/{decision_id}", response_model=NextBestAction, status_code=status.HTTP_200_OK)
def get_decision_by_id_endpoint(
    decision_id: str,
    db: Session = Depends(get_db)
):
    """
    Retrieves a specific decision / recommendation by ID.
    """
    try:
        engine = DecisionEngine(db)
        decision = engine.get_decision_by_id(decision_id)
        if not decision:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Decision '{decision_id}' not found.")
        return decision
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching decision {decision_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch decision")


@router.post("/decisions/{decision_id}/approve", response_model=DecisionActionResponse, status_code=status.HTTP_200_OK)
def approve_decision_endpoint(
    decision_id: str,
    db: Session = Depends(get_db)
):
    """
    Merchant approves a Next Best Action (state transition: PENDING -> APPROVED).
    Does NOT trigger external action execution in Phase 6.
    """
    try:
        engine = DecisionEngine(db)
        return engine.approve_decision(decision_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error approving decision {decision_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to approve decision")


@router.post("/decisions/{decision_id}/reject", response_model=DecisionActionResponse, status_code=status.HTTP_200_OK)
def reject_decision_endpoint(
    decision_id: str,
    db: Session = Depends(get_db)
):
    """
    Merchant rejects a Next Best Action (state transition: PENDING -> REJECTED).
    """
    try:
        engine = DecisionEngine(db)
        return engine.reject_decision(decision_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error rejecting decision {decision_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to reject decision")
