import logging
from datetime import datetime, timezone
from typing import Tuple, Optional
from app.models.action import Action, ActionStatus
from app.outcomes.config import get_observation_window_hours
from app.services.redis_service import get_redis_client

logger = logging.getLogger("paytm_pulse.outcomes.scheduler")


def ensure_utc(dt: Optional[datetime]) -> datetime:
    if dt is None:
        return datetime.now(timezone.utc)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class OutcomeScheduler:
    """
    Evaluates observation window readiness and manages distributed measurement locks.
    """

    @staticmethod
    def is_action_ready_for_measurement(
        action: Action,
        min_window_hours: Optional[float] = None,
        allow_immediate_demo: bool = True
    ) -> Tuple[bool, float, str]:
        """
        Determines whether sufficient observation time has elapsed for an executed action.
        """
        status_val = str(action.status.value if hasattr(action.status, "value") else action.status).upper()
        if status_val != "EXECUTED":
            return False, 0.0, f"Action status is '{status_val}', must be 'EXECUTED' for outcome measurement."

        if not action.executed_at:
            executed_at = action.updated_at or action.created_at or datetime.now(timezone.utc)
        else:
            executed_at = action.executed_at

        now = datetime.now(timezone.utc)
        hours_elapsed = (ensure_utc(now) - ensure_utc(executed_at)).total_seconds() / 3600.0


        action_type = str(action.action_type.value if hasattr(action.action_type, "value") else action.action_type)
        required_window = min_window_hours if min_window_hours is not None else get_observation_window_hours(action_type)

        # In testing/demo mode or when allow_immediate_demo is true, we allow measurement even if window is young,
        # but the impact calculator will accurately flag INSUFFICIENT_DATA if no transactions exist.
        if allow_immediate_demo:
            return True, round(hours_elapsed, 2), "Ready for progressive/immediate measurement."

        if hours_elapsed < required_window:
            return False, round(hours_elapsed, 2), f"Observation window in progress ({hours_elapsed:.1f}h / {required_window}h required)."

        return True, round(hours_elapsed, 2), "Observation window elapsed."

    @staticmethod
    def acquire_measurement_lock(action_id: str, ttl_seconds: int = 60) -> bool:
        """
        Acquire Redis lock to prevent concurrent duplicate measurements.
        """
        try:
            r = get_redis_client()
            if not r:
                return True
            lock_key = f"lock:outcome_measurement:{action_id}"
            acquired = r.set(lock_key, "1", nx=True, ex=ttl_seconds)
            return bool(acquired)
        except Exception as e:
            logger.warning(f"Failed to acquire redis lock for {action_id}: {e}")
            return True

    @staticmethod
    def release_measurement_lock(action_id: str):
        """
        Release Redis measurement lock.
        """
        try:
            r = get_redis_client()
            if r:
                r.delete(f"lock:outcome_measurement:{action_id}")
        except Exception as e:
            logger.warning(f"Failed to release redis lock for {action_id}: {e}")
