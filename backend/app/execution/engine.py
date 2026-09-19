"""
Paytm Pulse - Phase 8 Action Execution Engine
Coordinates validation, distributed locking, adapter routing, state persistence, and merchant notification.
"""

import uuid
import logging
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

from app.models.base import utc_now
from app.models.action import Action, ActionStatus
from app.models.merchant import Merchant
from app.models.recommendation import Recommendation
from app.adapters.mock_paytm import MockPaytmAdapter
from app.adapters.paytm import PaytmAdapter
from app.execution.config import MAX_EXECUTION_RETRIES, PAYTM_ENABLED
from app.execution.validator import ActionValidator
from app.execution.idempotency import ExecutionIdempotencyManager
from app.execution.schemas import ExecutionResponse, ActionExecutionStatusResponse, ExecutionHistoryItem
from app.execution.exceptions import (
    ActionValidationError,
    ActionNotApprovedError,
    ActionAlreadyExecutedError,
    ExecutionLockError,
    ActionRetryExhaustedError
)
from app.communication.notification_service import NotificationService
from app.whatsapp.client import whatsapp_client

logger = logging.getLogger("paytm_pulse.execution.engine")


class ExecutionEngine:
    """
    Main orchestrator for executing merchant-approved business actions.
    """

    def __init__(self, db: Session):
        self.db = db
        self.paytm_adapter = PaytmAdapter() if PAYTM_ENABLED else MockPaytmAdapter()
        self.notifications = NotificationService(db)

    def execute_action(
        self,
        action_id: str,
        is_retry: bool = False
    ) -> ExecutionResponse:
        """
        Executes an approved action through the configured adapter with idempotency and state guarantees.
        """
        # 1. Action Lookup
        action = self.db.query(Action).filter(Action.id == action_id).first()
        if not action:
            raise ActionValidationError(f"Action '{action_id}' not found.")

        # 2. Idempotent short-circuit if already EXECUTED
        if action.status == ActionStatus.EXECUTED:
            logger.info(f"Action {action_id} was already executed. Returning persisted execution result.")
            return ExecutionResponse(
                action_id=action.id,
                execution_id=action.execution_id or f"exec_prev_{action.id[:8]}",
                merchant_id=action.merchant_id,
                action_type=action.action_type.value,
                status="EXECUTED",
                executed_at=action.executed_at,
                details=action.execution_result or {},
                message=f"Action '{action.action_type.value}' was previously executed successfully.",
                retry_count=int(action.retry_count or 0),
                is_mock=True
            )

        # 3. Pre-execution Validation
        ActionValidator.validate_for_execution(action, self.db, is_retry=is_retry)

        # 4. Acquire Distributed Lock
        lock_acquired = ExecutionIdempotencyManager.acquire_lock(action.id)
        if not lock_acquired:
            raise ExecutionLockError(f"Execution already in progress for action '{action_id}'.")

        try:
            # 5. State Transition: APPROVED -> EXECUTING
            action.status = ActionStatus.EXECUTING
            self.db.commit()
            self.db.refresh(action)

            # 6. Execute through Adapter
            result = self.paytm_adapter.execute(action, self.db)

            # 7. State Transition based on result
            now_dt = utc_now()
            if result.success:
                action.status = ActionStatus.EXECUTED
                action.execution_id = result.execution_id
                action.executed_at = now_dt
                action.execution_result = result.details
                action.failure_reason = None
                self.db.commit()
                self.db.refresh(action)
                logger.info(f"Action {action_id} successfully EXECUTED with ID {result.execution_id}")

                # Send WhatsApp Notification
                self._send_execution_notification(action, result.message, is_success=True)

                # Phase 13 Feedback Signal hook
                try:
                    from app.feedback.service import FeedbackService
                    from app.feedback.config import FeedbackType
                    from app.feedback.schemas import FeedbackSignalCreate
                    FeedbackService(self.db).record_signal(
                        FeedbackSignalCreate(
                            merchant_id=str(action.merchant_id),
                            recommendation_id=str(action.recommendation_id) if action.recommendation_id else None,
                            action_id=str(action.id),
                            execution_id=str(result.execution_id) if result.execution_id else None,
                            feedback_type=FeedbackType.ACTION_EXECUTED,
                            metadata_payload={"action_type": action.action_type.value, "is_mock": result.is_mock}
                        )
                    )
                except Exception as fb_err:
                    logger.warning(f"Feedback recording non-fatal error on action execution: {fb_err}")

                return ExecutionResponse(
                    action_id=action.id,
                    execution_id=result.execution_id,
                    merchant_id=action.merchant_id,
                    action_type=action.action_type.value,
                    status="EXECUTED",
                    executed_at=action.executed_at,
                    details=result.details,
                    message=result.message,
                    retry_count=int(action.retry_count or 0),
                    is_mock=result.is_mock
                )
            else:
                action.status = ActionStatus.FAILED
                current_retries = int(action.retry_count or 0)
                action.retry_count = str(current_retries + 1)
                action.failure_reason = result.message or result.error
                self.db.commit()
                self.db.refresh(action)
                logger.warning(f"Action {action_id} execution FAILED: {result.message}")

                # Send WhatsApp Failure Notification
                self._send_execution_notification(action, result.message, is_success=False)

                # Phase 13 Feedback Signal hook
                try:
                    from app.feedback.service import FeedbackService
                    from app.feedback.config import FeedbackType
                    from app.feedback.schemas import FeedbackSignalCreate
                    FeedbackService(self.db).record_signal(
                        FeedbackSignalCreate(
                            merchant_id=str(action.merchant_id),
                            recommendation_id=str(action.recommendation_id) if action.recommendation_id else None,
                            action_id=str(action.id),
                            execution_id=str(result.execution_id) if result.execution_id else None,
                            feedback_type=FeedbackType.ACTION_FAILED,
                            metadata_payload={"action_type": action.action_type.value, "failure_reason": action.failure_reason}
                        )
                    )
                except Exception as fb_err:
                    logger.warning(f"Feedback recording non-fatal error on action failure: {fb_err}")

                return ExecutionResponse(
                    action_id=action.id,
                    execution_id=result.execution_id,
                    merchant_id=action.merchant_id,
                    action_type=action.action_type.value,
                    status="FAILED",
                    executed_at=now_dt,
                    details=result.details,
                    message=result.message,
                    retry_count=int(action.retry_count or 0),
                    failure_reason=action.failure_reason,
                    is_mock=result.is_mock
                )

        finally:
            ExecutionIdempotencyManager.release_lock(action.id)

    def retry_action(self, action_id: str) -> ExecutionResponse:
        """
        Retries a failed action within the maximum retry limit.
        """
        action = self.db.query(Action).filter(Action.id == action_id).first()
        if not action:
            raise ActionValidationError(f"Action '{action_id}' not found.")

        current_retries = int(action.retry_count or 0)
        if current_retries >= MAX_EXECUTION_RETRIES:
            raise ActionRetryExhaustedError(
                f"Action '{action_id}' has reached the maximum retry limit ({MAX_EXECUTION_RETRIES})."
            )

        logger.info(f"Retrying action {action_id} (Attempt {current_retries + 1}/{MAX_EXECUTION_RETRIES})")
        action.status = ActionStatus.APPROVED
        self.db.commit()

        return self.execute_action(action_id=action.id, is_retry=True)

    def get_action_status(self, action_id: str) -> ActionExecutionStatusResponse:
        """
        Retrieves real-time status of an action.
        """
        action = self.db.query(Action).filter(Action.id == action_id).first()
        if not action:
            raise ActionValidationError(f"Action '{action_id}' not found.")

        return ActionExecutionStatusResponse(
            action_id=action.id,
            merchant_id=action.merchant_id,
            status=action.status.value,
            approved_at=action.approved_at,
            executed_at=action.executed_at,
            retry_count=int(action.retry_count or 0),
            failure_reason=action.failure_reason,
            execution_result=action.execution_result
        )

    def get_merchant_history(self, merchant_id: str, limit: int = 20) -> List[ExecutionHistoryItem]:
        """
        Retrieves recent execution history for a merchant.
        """
        actions = (
            self.db.query(Action)
            .filter(Action.merchant_id == merchant_id)
            .order_by(Action.created_at.desc())
            .limit(limit)
            .all()
        )

        history = []
        for act in actions:
            rec = self.db.query(Recommendation).filter(Recommendation.id == act.recommendation_id).first()
            title = rec.title if rec else act.action_type.value
            history.append(
                ExecutionHistoryItem(
                    action_id=act.id,
                    merchant_id=act.merchant_id,
                    action_type=act.action_type.value,
                    status=act.status.value,
                    title=title,
                    execution_id=act.execution_id,
                    approved_at=act.approved_at,
                    executed_at=act.executed_at,
                    details=act.execution_result
                )
            )
        return history

    def _send_execution_notification(self, action: Action, message_detail: str, is_success: bool = True) -> None:
        """
        Dispatches a clean WhatsApp execution confirmation to the merchant.
        """
        try:
            merchant = self.db.query(Merchant).filter(Merchant.id == action.merchant_id).first()
            if not merchant:
                return

            if is_success:
                text = (
                    f"✅ *Action Completed Successfully!*\n\n"
                    f"{message_detail}\n\n"
                    f"Reference: `{action.execution_id or action.id[:8]}`"
                )
            else:
                text = (
                    f"⚠️ *Action Execution Notice*\n\n"
                    f"We encountered an issue while processing your approved action: {message_detail}\n"
                    f"The action has been saved and can be retried."
                )

            whatsapp_client.send_text_message(recipient_phone=merchant.phone, text=text)
        except Exception as e:
            logger.warning(f"Failed to send execution notification: {str(e)}")
