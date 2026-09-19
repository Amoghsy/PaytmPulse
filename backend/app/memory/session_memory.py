import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.core.redis import get_redis_client
from app.memory.config import REDIS_SESSION_TTL
from app.models.merchant import Merchant

logger = logging.getLogger("paytm_pulse.memory.session")


class SessionMemory:
    """
    Manages short-lived merchant interaction session state in Redis.
    """

    @staticmethod
    def _key(merchant_id: str) -> str:
        return f"merchant:{merchant_id}:session"

    @classmethod
    def update_session(
        cls,
        merchant_id: str,
        patch_data: Optional[Dict[str, Any]] = None,
        last_action: Optional[str] = None,
        **kwargs
    ) -> bool:
        """
        Updates session attributes and resets session TTL.
        Accepts dict patch_data or kwargs (e.g. last_action="viewed_dashboard").
        """
        try:
            r = get_redis_client()
            if not r:
                return False

            current = cls.get_session(merchant_id) or {
                "merchant_id": merchant_id,
                "interface": "whatsapp",
                "language": "en"
            }
            if patch_data and isinstance(patch_data, dict):
                current.update(patch_data)
            elif isinstance(patch_data, str) and not last_action:
                last_action = patch_data

            if last_action:
                current["last_action"] = last_action
            if kwargs:
                current.update(kwargs)

            current["merchant_id"] = merchant_id
            current["last_active_at"] = datetime.now(timezone.utc).isoformat()
            current["last_interaction"] = current["last_active_at"]

            key = cls._key(merchant_id)
            r.set(key, json.dumps(current, default=str), ex=REDIS_SESSION_TTL)
            logger.debug(f"[REDIS] Updated session for merchant {merchant_id}")
            return True
        except Exception as e:
            logger.warning(f"Failed to update session for merchant {merchant_id}: {e}")
            return False

    @classmethod
    def get_session(
        cls,
        merchant_id: str,
        db: Optional[Session] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieves active session state from Redis. Falls back to base merchant profile from PostgreSQL.
        """
        try:
            r = get_redis_client()
            if r:
                key = cls._key(merchant_id)
                raw = r.get(key)
                if raw:
                    logger.debug(f"[REDIS] Cache HIT: active session for merchant {merchant_id}")
                    return json.loads(raw)
        except Exception as e:
            logger.warning(f"Failed to read session for merchant {merchant_id}: {e}")

        # Fallback to base merchant info
        if db is not None:
            try:
                m = db.query(Merchant).filter(Merchant.id == merchant_id).first()
                if m:
                    return {
                        "merchant_id": str(m.id),
                        "shop_name": m.shop_name,
                        "language": getattr(m, "language", "Hindi") or "Hindi",
                        "interface": "whatsapp",
                        "last_active_at": None,
                        "fallback": True
                    }
            except Exception as e:
                logger.error(f"Database session fallback failed for merchant {merchant_id}: {e}")

        return None

    @classmethod
    def touch_session(cls, merchant_id: str) -> bool:
        """Extends the TTL of an active session."""
        try:
            r = get_redis_client()
            if r:
                r.expire(cls._key(merchant_id), REDIS_SESSION_TTL)
                return True
        except Exception as e:
            logger.warning(f"Failed to touch session for merchant {merchant_id}: {e}")
        return False

    @classmethod
    def clear_session(cls, merchant_id: str) -> bool:
        try:
            r = get_redis_client()
            if r:
                r.delete(cls._key(merchant_id))
                return True
        except Exception as e:
            logger.warning(f"Failed to clear session for merchant {merchant_id}: {e}")
        return False
