"""
Paytm Pulse - Phase 7 Conversation Manager
Maintains short-lived conversation context in Redis with automatic TTL expiry.
"""

import json
import logging
from typing import Dict, Any, Optional, List
from app.services import redis_service

logger = logging.getLogger("paytm_pulse.communication.conversation")

CONVERSATION_TTL_SECONDS = 1800  # 30 minutes
MAX_HISTORY_TURNS = 6  # Last 6 interaction turns (3 user + 3 assistant)


class ConversationManager:
    """
    Manages merchant conversation sessions, contextual references, and active topics.
    Backed by Redis for rapid lookup and stateless backend horizontal scaling.
    """

    @staticmethod
    def _get_key(merchant_id: str) -> str:
        return f"merchant:{merchant_id}:conversation"

    @classmethod
    def get_context(cls, merchant_id: str) -> Dict[str, Any]:
        """
        Retrieves the current conversation context for a merchant.
        """
        key = cls._get_key(merchant_id)
        raw = redis_service.get_key(key)
        if raw:
            try:
                return json.loads(raw)
            except Exception as e:
                logger.warning(f"Failed to decode conversation context for merchant {merchant_id}: {str(e)}")
        
        return {
            "merchant_id": merchant_id,
            "turns": [],
            "last_topic": None,
            "last_product_id": None,
            "last_product_name": None,
            "last_recommendation_id": None,
            "last_event_id": None
        }

    @classmethod
    def save_context(cls, merchant_id: str, context: Dict[str, Any], ttl_seconds: int = CONVERSATION_TTL_SECONDS) -> bool:
        """
        Saves updated conversation context to Redis with TTL.
        """
        key = cls._get_key(merchant_id)
        try:
            # Enforce max history length
            if "turns" in context and len(context["turns"]) > MAX_HISTORY_TURNS:
                context["turns"] = context["turns"][-MAX_HISTORY_TURNS:]
                
            serialized = json.dumps(context, default=str)
            return redis_service.set_key(key, serialized, expire_seconds=ttl_seconds)
        except Exception as e:
            logger.error(f"Failed to persist conversation context for {merchant_id}: {str(e)}")
            return False

    @classmethod
    def add_interaction(
        cls,
        merchant_id: str,
        user_message: str,
        agent_response: str,
        topic: Optional[str] = None,
        product_id: Optional[str] = None,
        product_name: Optional[str] = None,
        recommendation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Appends an interaction turn to merchant's session and updates topic focus.
        """
        ctx = cls.get_context(merchant_id)
        turns = ctx.get("turns", [])
        turns.append({"role": "merchant", "content": user_message})
        turns.append({"role": "agent", "content": agent_response})
        ctx["turns"] = turns

        if topic:
            ctx["last_topic"] = topic
        if product_id:
            ctx["last_product_id"] = product_id
        if product_name:
            ctx["last_product_name"] = product_name
        if recommendation_id:
            ctx["last_recommendation_id"] = recommendation_id

        cls.save_context(merchant_id, ctx)
        return ctx

    @classmethod
    def clear_context(cls, merchant_id: str) -> bool:
        """Clears the merchant's conversation history."""
        key = cls._get_key(merchant_id)
        return redis_service.delete_key(key)
