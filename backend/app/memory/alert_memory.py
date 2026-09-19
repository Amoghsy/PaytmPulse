import json
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.core.redis import get_redis_client
from app.memory.config import REDIS_ALERT_TTL
from app.models.business_event import BusinessEvent

logger = logging.getLogger("paytm_pulse.memory.alert")


class AlertMemory:
    """
    Manages fast-access active business alerts for each merchant in Redis
    with PostgreSQL fallback.
    """

    @staticmethod
    def _key(merchant_id: str) -> str:
        return f"merchant:{merchant_id}:active_alerts"

    @classmethod
    def set_alert(cls, merchant_id: str, event_id: str, alert_data: Dict[str, Any]) -> bool:
        """Adds or updates an active alert in Redis hash."""
        try:
            r = get_redis_client()
            if not r:
                return False
            key = cls._key(merchant_id)
            payload = dict(alert_data)
            if "id" not in payload:
                payload["id"] = str(event_id)
            if "event_id" not in payload:
                payload["event_id"] = str(event_id)
            r.hset(key, str(event_id), json.dumps(payload, default=str))
            r.expire(key, REDIS_ALERT_TTL)
            logger.debug(f"[REDIS] Set active alert {event_id} for merchant {merchant_id}")
            return True
        except Exception as e:
            logger.warning(f"Failed to set active alert for merchant {merchant_id}: {e}")
            return False

    @classmethod
    def add_active_alert(cls, merchant_id: str, alert_data: Dict[str, Any]) -> bool:
        """Alias for set_alert extracting event_id from payload."""
        ev_id = str(alert_data.get("event_id") or alert_data.get("id") or "active")
        return cls.set_alert(merchant_id, ev_id, alert_data)

    @classmethod
    def get_active_alerts(
        cls,
        merchant_id: str,
        db: Optional[Session] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieves all currently active alerts for a merchant.
        Falls back to PostgreSQL unprocessed BusinessEvents if Redis is empty/offline.
        """
        try:
            r = get_redis_client()
            if r:
                key = cls._key(merchant_id)
                raw_dict = r.hgetall(key)
                if raw_dict:
                    logger.debug(f"[REDIS] Cache HIT: {len(raw_dict)} active alerts for merchant {merchant_id}")
                    return [json.loads(v) for v in raw_dict.values()]
        except Exception as e:
            logger.warning(f"Failed to read alert memory for merchant {merchant_id}: {e}")

        # PostgreSQL Fallback
        if db is not None:
            try:
                events = db.query(BusinessEvent).filter(
                    BusinessEvent.merchant_id == merchant_id,
                    BusinessEvent.processed == False
                ).order_by(BusinessEvent.created_at.desc()).limit(10).all()

                logger.debug(f"[DB] Fallback: fetched {len(events)} active events from PostgreSQL for merchant {merchant_id}")
                return [
                    {
                        "id": str(e.id),
                        "event_id": str(e.id),
                        "merchant_id": str(e.merchant_id),
                        "event_type": e.event_type.value if hasattr(e.event_type, "value") else str(e.event_type),
                        "severity": e.severity.value if hasattr(e.severity, "value") else str(e.severity),
                        "summary": e.payload.get("summary") if e.payload else f"{e.event_type} detected",
                        "payload": e.payload,
                        "created_at": e.created_at.isoformat()
                    }
                    for e in events
                ]
            except Exception as e:
                logger.error(f"Database alert fallback query failed for merchant {merchant_id}: {e}")

        return []

    @classmethod
    def clear_alert(cls, merchant_id: str, event_id: str) -> bool:
        """Removes an active alert when resolved or processed."""
        try:
            r = get_redis_client()
            if r:
                r.hdel(cls._key(merchant_id), str(event_id))
                return True
        except Exception as e:
            logger.warning(f"Failed to remove active alert for merchant {merchant_id}: {e}")
        return False

    @classmethod
    def remove_active_alert(cls, merchant_id: str, event_id: str) -> bool:
        return cls.clear_alert(merchant_id, event_id)

    @classmethod
    def clear_active_alerts(cls, merchant_id: str) -> bool:
        try:
            r = get_redis_client()
            if r:
                r.delete(cls._key(merchant_id))
                return True
        except Exception as e:
            logger.warning(f"Failed to clear alerts for {merchant_id}: {e}")
        return False
