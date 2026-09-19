import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.core.redis import get_redis_client
from app.memory.config import REDIS_CONVERSATION_TTL, REDIS_MAX_CONVERSATION_MESSAGES
from app.models.merchant_message import MerchantMessage, MessageDirection

logger = logging.getLogger("paytm_pulse.memory.conversation")


class ConversationMemory:
    """
    Maintains a short-term multi-turn conversation buffer in Redis
    with fallback to PostgreSQL MerchantMessage history.
    """

    @staticmethod
    def _key(merchant_id: str) -> str:
        return f"merchant:{merchant_id}:conversation"

    @classmethod
    def add_message(
        cls,
        merchant_id: str,
        role: str,
        message: str,
        ttl: int = REDIS_CONVERSATION_TTL
    ) -> bool:
        """
        Appends a conversation message to the list (RPUSH), trims old messages, and refreshes TTL.
        """
        turn = {
            "role": role,
            "text": message,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        try:
            r = get_redis_client()
            if not r:
                return False
            key = cls._key(merchant_id)
            r.rpush(key, json.dumps(turn, default=str))
            # Keep latest N messages
            r.ltrim(key, -REDIS_MAX_CONVERSATION_MESSAGES, -1)
            r.expire(key, ttl)
            logger.debug(f"[REDIS] Conversation updated for merchant {merchant_id} ({role})")
            return True
        except Exception as e:
            logger.warning(f"Failed to record conversation message in Redis for {merchant_id}: {e}")
            return False

    @classmethod
    def get_recent_conversation(
        cls,
        merchant_id: str,
        limit: int = 20,
        db: Optional[Session] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieves recent conversation turns in chronological order.
        Falls back to PostgreSQL if Redis is empty/offline.
        """
        try:
            r = get_redis_client()
            if r:
                key = cls._key(merchant_id)
                raw_items = r.lrange(key, -limit, -1)
                if raw_items:
                    logger.debug(f"[REDIS] Cache HIT: {len(raw_items)} conversation messages for merchant {merchant_id}")
                    return [json.loads(item) for item in raw_items]
        except Exception as e:
            logger.warning(f"Failed to read conversation from Redis for {merchant_id}: {e}")

        # PostgreSQL Fallback
        if db is not None:
            try:
                msgs = db.query(MerchantMessage).filter(
                    MerchantMessage.merchant_id == merchant_id
                ).order_by(MerchantMessage.created_at.desc()).limit(limit).all()

                # Reverse to return in chronological order
                msgs.reverse()
                logger.debug(f"[DB] Fallback: fetched {len(msgs)} messages from PostgreSQL for merchant {merchant_id}")
                return [
                    {
                        "role": "user" if m.direction == MessageDirection.INBOUND else "assistant",
                        "text": m.content,
                        "message": m.content,
                        "timestamp": m.created_at.isoformat()
                    }
                    for m in msgs
                ]
            except Exception as e:
                logger.error(f"Database conversation fallback failed for {merchant_id}: {e}")

        return []

    @classmethod
    def clear_conversation(cls, merchant_id: str) -> bool:
        """
        Clears short-term conversation memory in Redis.
        """
        try:
            r = get_redis_client()
            if r:
                r.delete(cls._key(merchant_id))
                logger.debug(f"[REDIS] Cleared conversation memory for merchant {merchant_id}")
                return True
        except Exception as e:
            logger.warning(f"Failed to clear conversation memory for {merchant_id}: {e}")
        return False
