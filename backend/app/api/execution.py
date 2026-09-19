"""
Paytm Pulse - Phase 8 Execution API Router
FastAPI endpoints for executing merchant actions, checking execution status, retrying, and querying history.
"""

import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.action import Action
from app.execution.engine import ExecutionEngine
from app.execution.schemas import (
    ExecutionResponse,
    ActionExecutionStatusResponse,
    ExecutionHistoryItem
)
from app.execution.exceptions import (
    ActionValidationError,
    ActionNotApprovedError,
    ActionAlreadyExecutedError,
    ExecutionLockError,
    ActionRetryExhaustedError
)

logger = logging.getLogger("paytm_pulse.api.execution")

router = APIRouter(tags=["Action Execution - Closed-Loop & Paytm"])


@router.post("/execution/{action_id}", response_model=ExecutionResponse, status_code=status.HTTP_200_OK)
def execute_action_endpoint(
    action_id: str,
    db: Session = Depends(get_db)
):
    """
    Executes an approved merchant action through the appropriate domain/Paytm adapter.
    """
    engine = ExecutionEngine(db)
    try:
        return engine.execute_action(action_id)
    except ActionNotApprovedError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ActionAlreadyExecutedError as e:
        # Idempotent return if already executed
        return engine.execute_action(action_id)
    except ActionValidationError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ExecutionLockError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        logger.error(f"Execution failed unexpectedly for action {action_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Execution pipeline error")


@router.post("/execution/{action_id}/retry", response_model=ExecutionResponse, status_code=status.HTTP_200_OK)
def retry_action_endpoint(
    action_id: str,
    db: Session = Depends(get_db)
):
    """
    Retries a previously failed action.
    """
    engine = ExecutionEngine(db)
    try:
        return engine.retry_action(action_id)
    except ActionRetryExhaustedError as e:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(e))
    except ActionValidationError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Retry failed for action {action_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Retry execution error")


@router.get("/execution/{execution_id}", response_model=ExecutionResponse, status_code=status.HTTP_200_OK)
def get_execution_by_id_endpoint(
    execution_id: str,
    db: Session = Depends(get_db)
):
    """
    Retrieves execution details by execution ID.
    """
    action = db.query(Action).filter(Action.execution_id == execution_id).first()
    if not action:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Execution '{execution_id}' not found.")

    return ExecutionResponse(
        action_id=action.id,
        execution_id=action.execution_id,
        merchant_id=action.merchant_id,
        action_type=action.action_type.value,
        status=action.status.value,
        executed_at=action.executed_at,
        details=action.execution_result or {},
        message=f"Action '{action.action_type.value}' execution record.",
        retry_count=int(action.retry_count or 0),
        is_mock=True
    )


@router.get("/execution/{action_id}/status", response_model=ActionExecutionStatusResponse, status_code=status.HTTP_200_OK)
def get_action_execution_status_endpoint(
    action_id: str,
    db: Session = Depends(get_db)
):
    """
    Retrieves the execution status and timestamps for a specific action.
    """
    engine = ExecutionEngine(db)
    try:
        return engine.get_action_status(action_id)
    except ActionValidationError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/execution/merchant/{merchant_id}", response_model=List[ExecutionHistoryItem], status_code=status.HTTP_200_OK)
def get_merchant_executions_endpoint(
    merchant_id: str,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """
    Retrieves execution history for a merchant.
    """
    engine = ExecutionEngine(db)
    return engine.get_merchant_history(merchant_id=merchant_id, limit=limit)
