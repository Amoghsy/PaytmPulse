"""
Paytm Pulse - Phase 8 Execution Idempotency & Lock Manager
Guarantees at-most-once execution using Redis distributed locks.
"""

import logging
from typing import Optional
from app.services import redis_service
from app.execution.config import EXECUTION_LOCK_TTL_SECONDS
from app.execution.exceptions import ExecutionLockError

logger = logging.getLogger("paytm_pulse.execution.idempotency")


class ExecutionIdempotencyManager:
    """
    Manages short-lived execution locks to ensure strict idempotency and prevent double-execution.
    """

    @staticmethod
    def _lock_key(action_id: str) -> str:
        return f"lock:action_execution:{action_id}"

    @classmethod
    def acquire_lock(cls, action_id: str, ttl_seconds: int = EXECUTION_LOCK_TTL_SECONDS) -> bool:
        """
        Attempts to acquire an execution lock for the given action ID.
        """
        key = cls._lock_key(action_id)
        existing = redis_service.get_key(key)
        if existing:
            logger.warning(f"Concurrent execution blocked: Lock already exists for action {action_id}")
            return False

        return redis_service.set_key(key, "LOCKED", expire_seconds=ttl_seconds)

    @classmethod
    def release_lock(cls, action_id: str) -> bool:
        """
        Releases the execution lock.
        """
        key = cls._lock_key(action_id)
        return redis_service.delete_key(key)
