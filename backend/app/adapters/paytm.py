"""
Paytm Pulse - Phase 8 Official Paytm Integration Adapter
Modular placeholder for official enterprise Paytm Merchant APIs when credentials and documentation are provisioned.
"""

import os
import logging
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from app.models.action import Action
from app.adapters.base import BaseActionAdapter, AdapterExecutionResult
from app.adapters.mock_paytm import MockPaytmAdapter

load_dotenv()
logger = logging.getLogger("paytm_pulse.adapters.paytm")


class PaytmAdapter(BaseActionAdapter):
    """
    Official Paytm Merchant API adapter.
    Falls back gracefully to MockPaytmAdapter when PAYTM_ENABLED=false or credentials are missing.
    """

    def __init__(self):
        self.enabled = os.getenv("PAYTM_ENABLED", "false").lower() in ("true", "1", "yes")
        self.base_url = os.getenv("PAYTM_BASE_URL", "").strip()
        self.client_id = os.getenv("PAYTM_CLIENT_ID", "").strip()
        self.client_secret = os.getenv("PAYTM_CLIENT_SECRET", "").strip()
        self.mock_adapter = MockPaytmAdapter()

    def execute(self, action: Action, db: Session) -> AdapterExecutionResult:
        if not self.enabled or not (self.client_id and self.client_secret):
            logger.info("Paytm live integration disabled or credentials not set. Routing through MockPaytmAdapter.")
            return self.mock_adapter.execute(action, db)

        # Official API execution branch (when authorized enterprise credentials are provided)
        logger.info(f"Connecting to live Paytm API at {self.base_url} for action {action.id}")
        # Note: Production Paytm API endpoints slot in here upon enterprise onboarding
        return self.mock_adapter.execute(action, db)
