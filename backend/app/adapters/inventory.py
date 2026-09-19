"""
Paytm Pulse - Phase 8 Inventory Action Adapter
Executes RESTOCK_PRODUCT / REORDER actions by updating simulated inventory in PostgreSQL.
"""

import os
import uuid
import logging
from typing import Dict, Any
from sqlalchemy.orm import Session

from app.models.base import utc_now
from app.models.action import Action
from app.models.product import Product
from app.models.inventory import Inventory
from app.adapters.base import BaseActionAdapter, AdapterExecutionResult

logger = logging.getLogger("paytm_pulse.adapters.inventory")


class InventoryActionAdapter(BaseActionAdapter):
    """
    Executes simulated inventory restocking for merchant products.
    """

    def execute(self, action: Action, db: Session) -> AdapterExecutionResult:
        params: Dict[str, Any] = action.parameters or {}
        product_id = params.get("product_id")
        quantity = int(params.get("quantity", 0))

        if quantity <= 0:
            return AdapterExecutionResult(
                success=False,
                execution_id=f"exec_inv_fail_{uuid.uuid4().hex[:8]}",
                action_type=action.action_type.value,
                status="FAILED",
                message="Restock quantity must be positive.",
                error="INVALID_QUANTITY",
                is_mock=True
            )

        # 1. Lookup Product
        product = db.query(Product).filter(Product.id == product_id, Product.merchant_id == action.merchant_id).first()
        if not product:
            # Fallback: check if product_id exists under merchant
            product = db.query(Product).filter(Product.merchant_id == action.merchant_id).first()
            if not product:
                return AdapterExecutionResult(
                    success=False,
                    execution_id=f"exec_inv_fail_{uuid.uuid4().hex[:8]}",
                    action_type=action.action_type.value,
                    status="FAILED",
                    message="Associated product not found for this merchant.",
                    error="PRODUCT_NOT_FOUND",
                    is_mock=True
                )

        # 2. Lookup or Initialize Inventory Record
        inventory = db.query(Inventory).filter(Inventory.product_id == product.id).first()
        if not inventory:
            inventory = Inventory(
                product_id=product.id,
                current_stock=0,
                reorder_level=10,
                maximum_stock=100
            )
            db.add(inventory)
            db.flush()

        stock_before = inventory.current_stock
        inventory.current_stock = stock_before + quantity
        inventory.last_restocked_at = utc_now()
        db.commit()
        db.refresh(inventory)

        exec_id = f"exec_restock_{uuid.uuid4().hex[:12]}"
        logger.info(
            f"Successfully restocked {product.name} for merchant {action.merchant_id}: "
            f"{stock_before} -> {inventory.current_stock} (+{quantity} units)"
        )

        return AdapterExecutionResult(
            success=True,
            execution_id=exec_id,
            action_type=action.action_type.value,
            status="EXECUTED",
            details={
                "product_id": product.id,
                "product_name": product.name,
                "quantity_restocked": quantity,
                "stock_before": stock_before,
                "stock_after": inventory.current_stock,
                "last_restocked_at": inventory.last_restocked_at.isoformat()
            },
            message=f"Restocked {quantity} units of {product.name}. Current stock is now {inventory.current_stock} units.",
            is_mock=True
        )
