"""
Paytm Pulse - Phase 8 Action Validator
Pre-execution safety, permission, state, and parameter bounds checking.
"""

import logging
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.models.action import Action, ActionStatus
from app.models.merchant import Merchant
from app.models.product import Product
from app.execution.exceptions import (
    ActionValidationError,
    ActionNotApprovedError,
    ActionAlreadyExecutedError
)

logger = logging.getLogger("paytm_pulse.execution.validator")


class ActionValidator:
    """
    Ensures an action is safe, authorized, approved, and fully configured before execution.
    """

    @classmethod
    def validate_for_execution(
        cls,
        action: Action,
        db: Session,
        is_retry: bool = False
    ) -> None:
        """
        Validates action state, ownership, and parameter boundaries.
        Raises ActionValidationError or ActionNotApprovedError if invalid.
        """
        if not action:
            raise ActionValidationError("Action does not exist.")

        # 1. Merchant Check
        merchant = db.query(Merchant).filter(Merchant.id == action.merchant_id).first()
        if not merchant:
            raise ActionValidationError(f"Merchant '{action.merchant_id}' does not exist.")

        # 2. State Transition Check
        if action.status == ActionStatus.EXECUTED:
            raise ActionAlreadyExecutedError(f"Action '{action.id}' has already been executed.")

        if is_retry:
            if action.status not in (ActionStatus.FAILED, ActionStatus.APPROVED):
                raise ActionNotApprovedError(f"Action '{action.id}' in status '{action.status.value}' cannot be retried.")
        else:
            if action.status != ActionStatus.APPROVED:
                raise ActionNotApprovedError(
                    f"Action '{action.id}' is in status '{action.status.value}'. Only 'APPROVED' actions can be executed."
                )

        # 3. Action Parameter Bounds Validation
        params: Dict[str, Any] = action.parameters or {}
        action_type_val = action.action_type.value

        if action_type_val in ("REORDER", "RESTOCK_PRODUCT"):
            qty = params.get("quantity")
            if qty is None or int(qty) <= 0:
                raise ActionValidationError("Restock action requires a positive 'quantity' parameter.")

            prod_id = params.get("product_id")
            if prod_id:
                product = db.query(Product).filter(Product.id == prod_id, Product.merchant_id == action.merchant_id).first()
                if not product:
                    # Check if merchant has any product
                    p_count = db.query(Product).filter(Product.merchant_id == action.merchant_id).count()
                    if p_count == 0:
                        raise ActionValidationError(f"Product '{prod_id}' not found for merchant '{action.merchant_id}'.")

        elif action_type_val in ("PROMOTION", "RUN_PROMOTION"):
            discount = params.get("discount_percentage", 10.0)
            try:
                discount_f = float(discount)
                if discount_f <= 0 or discount_f > 50.0:
                    raise ActionValidationError("Promotional discount percentage must be between 1% and 50%.")
            except (ValueError, TypeError):
                raise ActionValidationError("Invalid discount percentage format.")

        logger.info(f"Action {action.id} passed pre-execution validation successfully.")
