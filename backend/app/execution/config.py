"""
Paytm Pulse - Phase 8 Execution Configuration
"""

import os
from dotenv import load_dotenv

load_dotenv()

EXECUTION_MODE = os.getenv("EXECUTION_MODE", "mock").lower()
MAX_EXECUTION_RETRIES = int(os.getenv("MAX_EXECUTION_RETRIES", "3"))
MOCK_EXECUTION_DELAY_MS = int(os.getenv("MOCK_EXECUTION_DELAY_MS", "0"))
MOCK_FAILURE_RATE = float(os.getenv("MOCK_FAILURE_RATE", "0.0"))
PAYTM_ENABLED = os.getenv("PAYTM_ENABLED", "false").lower() in ("true", "1", "yes")
EXECUTION_LOCK_TTL_SECONDS = 60
