"""
Paytm Pulse - Phase 8 Customer & Campaign Action Adapter
Executes customer winback campaigns, bundle offerings, and cross-sell campaigns.
"""

import uuid
import logging
from typing import Dict, Any
from sqlalchemy.orm import Session

from app.models.base import utc_now
from app.models.action import Action
from app.models.customer import Customer
from app.adapters.base import BaseActionAdapter, AdapterExecutionResult

logger = logging.getLogger("paytm_pulse.adapters.customer")


class CustomerActionAdapter(BaseActionAdapter):
    """
    Executes customer re-engagement campaigns and bundled merchandising offers.
    """

    def execute(self, action: Action, db: Session) -> AdapterExecutionResult:
        params: Dict[str, Any] = action.parameters or {}
        action_type_val = action.action_type.value
        exec_id = f"exec_campaign_{uuid.uuid4().hex[:12]}"

        if action_type_val in ("CUSTOMER_WINBACK", "WINBACK", "CUSTOMER_RETENTION"):
            target_segment = params.get("target_segment", "AT_RISK")
            offer_pct = float(params.get("discount_percentage", 10.0))
            
            # Count target customers
            cust_count = db.query(Customer).filter(Customer.merchant_id == action.merchant_id).count()
            target_count = max(1, min(cust_count // 3, 25))

            details = {
                "campaign_id": f"CAMP-WINBACK-{uuid.uuid4().hex[:6].upper()}",
                "campaign_type": "CUSTOMER_WINBACK",
                "target_segment": target_segment,
                "offer_discount_percentage": offer_pct,
                "audience_size": target_count,
                "status": "READY",
                "scheduled_at": utc_now().isoformat()
            }
            message = f"Win-back campaign queued for {target_count} {target_segment} customers with a {offer_pct:.0f}% special offer."

        elif action_type_val in ("CREATE_BUNDLE", "CROSS_SELL"):
            primary_p = params.get("product_id") or "Catalog Item 1"
            bundle_name = params.get("bundle_name") or "Special Value Combo"
            discount = float(params.get("discount_percentage", 12.0))

            details = {
                "bundle_id": f"BUNDLE-{uuid.uuid4().hex[:6].upper()}",
                "bundle_name": bundle_name,
                "primary_product_id": primary_p,
                "bundle_discount_percentage": discount,
                "status": "ACTIVE",
                "created_at": utc_now().isoformat()
            }
            message = f"Product bundle '{bundle_name}' configured with {discount:.0f}% bundle discount."

        else:
            # Informational / monitoring actions
            details = {
                "tracking_id": f"TRACK-{uuid.uuid4().hex[:6].upper()}",
                "monitoring_started_at": utc_now().isoformat(),
                "status": "MONITORING_ACTIVE"
            }
            message = f"Live telemetry monitoring active for '{action_type_val}'."

        logger.info(f"Customer adapter executed for merchant {action.merchant_id}: '{message}'")

        return AdapterExecutionResult(
            success=True,
            execution_id=exec_id,
            action_type=action_type_val,
            status="EXECUTED",
            details=details,
            message=message,
            is_mock=True
        )
