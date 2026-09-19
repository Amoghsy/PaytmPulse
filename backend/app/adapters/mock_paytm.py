"""
Paytm Pulse - Phase 8 Mock Paytm Adapter
Simulates Paytm merchant platform API responses with realistic latency and configurable failure injection.
"""

import os
import time
import random
import logging
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from app.models.action import Action
from app.adapters.base import BaseActionAdapter, AdapterExecutionResult
from app.adapters.inventory import InventoryActionAdapter
from app.adapters.promotion import PromotionActionAdapter
from app.adapters.customer import CustomerActionAdapter

load_dotenv()
logger = logging.getLogger("paytm_pulse.adapters.mock_paytm")


class MockPaytmAdapter(BaseActionAdapter):
    """
    Simulates Paytm merchant backend services for hackathon demonstration.
    Provides realistic state updates for inventory, promotions, and customer campaigns.
    """

    def __init__(self):
        self.inventory_adapter = InventoryActionAdapter()
        self.promotion_adapter = PromotionActionAdapter()
        self.customer_adapter = CustomerActionAdapter()
        self.mock_delay_ms = int(os.getenv("MOCK_EXECUTION_DELAY_MS", "0"))
        self.mock_failure_rate = float(os.getenv("MOCK_FAILURE_RATE", "0.0"))

    def execute(self, action: Action, db: Session) -> AdapterExecutionResult:
        logger.info(f"[PAYTM MOCK] Executing action {action.id} (Type: {action.action_type.value})")

        # 1. Simulate network latency if configured
        if self.mock_delay_ms > 0:
            time.sleep(self.mock_delay_ms / 1000.0)

        # 2. Simulate failure if configured (for error resiliency testing)
        if self.mock_failure_rate > 0.0 and random.random() < self.mock_failure_rate:
            logger.warning(f"[PAYTM MOCK] Injected simulated failure for action {action.id}")
            return AdapterExecutionResult(
                success=False,
                execution_id=f"exec_sim_err_{action.id[:8]}",
                action_type=action.action_type.value,
                status="FAILED",
                message="Simulated Paytm gateway transient timeout.",
                error="PAYTM_GATEWAY_TIMEOUT",
                is_mock=True
            )

        # 3. Route to specialized domain adapter for state mutation
        action_type_val = action.action_type.value
        if action_type_val in ("REORDER", "RESTOCK_PRODUCT"):
            return self.inventory_adapter.execute(action, db)

        elif action_type_val in ("PROMOTION", "RUN_PROMOTION"):
            return self.promotion_adapter.execute(action, db)

        else:
            return self.customer_adapter.execute(action, db)
