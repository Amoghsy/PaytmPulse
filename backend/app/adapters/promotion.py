"""
Paytm Pulse - Phase 8 Promotion Action Adapter
Executes RUN_PROMOTION / PROMOTION actions by creating active promotion campaigns in PostgreSQL.
"""

import uuid
import logging
from datetime import timedelta
from typing import Dict, Any
from sqlalchemy.orm import Session

from app.models.base import utc_now
from app.models.action import Action
from app.models.product import Product
from app.models.promotion import Promotion, PromotionStatus
from app.adapters.base import BaseActionAdapter, AdapterExecutionResult

logger = logging.getLogger("paytm_pulse.adapters.promotion")


class PromotionActionAdapter(BaseActionAdapter):
    """
    Executes simulated merchant sales promotions and flash offers.
    """

    def execute(self, action: Action, db: Session) -> AdapterExecutionResult:
        params: Dict[str, Any] = action.parameters or {}
        product_id = params.get("product_id")
        discount_pct = float(params.get("discount_percentage", 10.0))
        duration_hours = int(params.get("duration_hours", 24))
        target_segment = params.get("target_segment", "ALL")

        # 1. Bounding safety check (Cap discounts at 50%)
        if discount_pct <= 0 or discount_pct > 50.0:
            discount_pct = min(max(discount_pct, 5.0), 50.0)

        # 2. Lookup Product
        product = db.query(Product).filter(Product.id == product_id, Product.merchant_id == action.merchant_id).first()
        if not product:
            product = db.query(Product).filter(Product.merchant_id == action.merchant_id).first()
            if not product:
                return AdapterExecutionResult(
                    success=False,
                    execution_id=f"exec_promo_fail_{uuid.uuid4().hex[:8]}",
                    action_type=action.action_type.value,
                    status="FAILED",
                    message="Target product not found for promotion.",
                    error="PRODUCT_NOT_FOUND",
                    is_mock=True
                )

        now_dt = utc_now()
        end_dt = now_dt + timedelta(hours=duration_hours)
        title = f"{discount_pct:.0f}% Off on {product.name}"

        # 3. Create Promotion Record
        promo = Promotion(
            merchant_id=action.merchant_id,
            action_id=action.id,
            product_id=product.id,
            title=title,
            discount_percentage=discount_pct,
            target_segment=target_segment,
            start_time=now_dt,
            end_time=end_dt,
            status=PromotionStatus.ACTIVE
        )
        db.add(promo)
        db.commit()
        db.refresh(promo)

        exec_id = f"exec_promo_{uuid.uuid4().hex[:12]}"
        logger.info(f"Created active promotion {promo.id} for merchant {action.merchant_id}: '{title}'")

        return AdapterExecutionResult(
            success=True,
            execution_id=exec_id,
            action_type=action.action_type.value,
            status="EXECUTED",
            details={
                "promotion_id": promo.id,
                "product_id": product.id,
                "product_name": product.name,
                "discount_percentage": discount_pct,
                "duration_hours": duration_hours,
                "start_time": now_dt.isoformat(),
                "end_time": end_dt.isoformat(),
                "status": "ACTIVE"
            },
            message=f"Promotion '{title}' is now ACTIVE for {duration_hours} hours.",
            is_mock=True
        )
