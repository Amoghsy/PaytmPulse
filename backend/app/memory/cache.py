"""ML Intelligence Fast Cache for Paytm Pulse.

Caches expensive analytical computations (sales velocity, customer churn risk,
demand forecasts, financial product matches) in Redis with automatic TTL
and selective invalidation triggers.
"""
from typing import Dict, Any, Optional
import json
import logging

from app.core.redis import get_redis_client
from app.memory.config import REDIS_INTELLIGENCE_CACHE_TTL

logger = logging.getLogger(__name__)


class IntelligenceCache:
    """Fast cache for Phase 4 & Phase 10 ML Intelligence results."""

    @staticmethod
    def _key(merchant_id: str, analysis_type: str) -> str:
        return f"merchant:{merchant_id}:intelligence:{analysis_type}"

    @classmethod
    def get(cls, merchant_id: str, analysis_type: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached analysis result if valid."""
        redis = get_redis_client()
        if not redis:
            return None

        try:
            data = redis.get(cls._key(merchant_id, analysis_type))
            if data:
                return json.loads(data)
        except Exception as e:
            logger.warning(f"Failed to read intelligence cache for {merchant_id}:{analysis_type}: {e}")
        return None

    @classmethod
    def set(
        cls,
        merchant_id: str,
        analysis_type: str,
        data: Dict[str, Any],
        ttl: int = REDIS_INTELLIGENCE_CACHE_TTL
    ) -> bool:
        """Cache analysis result with TTL."""
        redis = get_redis_client()
        if not redis:
            return False

        try:
            redis.set(cls._key(merchant_id, analysis_type), json.dumps(data, default=str), ex=ttl)
            return True
        except Exception as e:
            logger.warning(f"Failed to set intelligence cache for {merchant_id}:{analysis_type}: {e}")
            return False

    @classmethod
    def invalidate(cls, merchant_id: str, analysis_type: str) -> bool:
        """Invalidate a specific cached analysis for a merchant."""
        redis = get_redis_client()
        if not redis:
            return False

        try:
            redis.delete(cls._key(merchant_id, analysis_type))
            return True
        except Exception as e:
            logger.warning(f"Failed to invalidate intelligence cache for {merchant_id}:{analysis_type}: {e}")
            return False

    @classmethod
    def invalidate_all(cls, merchant_id: str) -> bool:
        """Invalidate all intelligence caches for a merchant (e.g., when new transaction arrives)."""
        redis = get_redis_client()
        if not redis:
            return False

        try:
            pattern = f"merchant:{merchant_id}:intelligence:*"
            keys = redis.keys(pattern)
            if keys:
                redis.delete(*keys)
            return True
        except Exception as e:
            logger.warning(f"Failed to invalidate all intelligence caches for {merchant_id}: {e}")
            return False
