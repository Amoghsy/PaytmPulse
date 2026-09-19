"""Recommendation Fast Memory for Paytm Pulse.

Manages short-term caching of active and recently evaluated recommendations
in Redis with PostgreSQL fallback.
"""
from typing import Dict, Any, List, Optional
import json
import logging
from sqlalchemy.orm import Session

from app.core.redis import get_redis_client
from app.memory.config import REDIS_RECOMMENDATION_TTL

logger = logging.getLogger(__name__)


class RecommendationMemory:
    """Manages active recommendation caching in Redis with PostgreSQL fallback."""

    @staticmethod
    def _key_active(merchant_id: str) -> str:
        return f"merchant:{merchant_id}:active_recommendations"

    @staticmethod
    def _key_rec(merchant_id: str, rec_id: str) -> str:
        return f"merchant:{merchant_id}:recommendation:{rec_id}"

    @classmethod
    def cache_recommendation(
        cls,
        merchant_id: str,
        rec_data: Dict[str, Any],
        ttl: int = REDIS_RECOMMENDATION_TTL
    ) -> bool:
        """Cache a single recommendation and add it to active recommendations map."""
        redis = get_redis_client()
        if not redis:
            return False

        rec_id = str(rec_data.get("id") or rec_data.get("recommendation_id") or "active")
        rec_key = cls._key_rec(merchant_id, rec_id)
        active_key = cls._key_active(merchant_id)

        try:
            payload = json.dumps(rec_data, default=str)
            # Store recommendation payload
            redis.set(rec_key, payload, ex=ttl)
            # Store in active recommendations hash
            redis.hset(active_key, rec_id, payload)
            redis.expire(active_key, ttl)
            return True
        except Exception as e:
            logger.warning(f"Failed to cache recommendation in Redis for {merchant_id}: {e}")
            return False

    @classmethod
    def get_active_recommendation(
        cls,
        merchant_id: str,
        rec_id: Optional[str] = None,
        db: Optional[Session] = None
    ) -> Optional[Dict[str, Any]]:
        """Get active recommendation from Redis, fallback to DB if not found."""
        redis = get_redis_client()
        if redis:
            try:
                if rec_id:
                    rec_key = cls._key_rec(merchant_id, rec_id)
                    data = redis.get(rec_key)
                    if data:
                        return json.loads(data)
                
                # Check active recommendations hash
                active_key = cls._key_active(merchant_id)
                if rec_id:
                    val = redis.hget(active_key, rec_id)
                    if val:
                        return json.loads(val)
                else:
                    # Return latest/first active recommendation
                    all_recs = redis.hgetall(active_key)
                    if all_recs:
                        # Return the most recent one
                        first_val = list(all_recs.values())[-1]
                        return json.loads(first_val)
            except Exception as e:
                logger.warning(f"Error reading recommendation from Redis for {merchant_id}: {e}")

        # Fallback to PostgreSQL
        if db:
            try:
                from app.models.recommendation import Recommendation, RecommendationStatus
                query = db.query(Recommendation).filter(
                    Recommendation.merchant_id == merchant_id,
                    Recommendation.status == RecommendationStatus.PENDING
                )
                if rec_id:
                    query = query.filter(Recommendation.id == rec_id)
                rec = query.order_by(Recommendation.created_at.desc()).first()
                if rec:
                    return {
                        "id": str(rec.id),
                        "merchant_id": str(rec.merchant_id),
                        "recommendation_text": rec.recommendation_text,
                        "title": getattr(rec, "title", None) or rec.recommendation_text[:40],
                        "urgency": rec.urgency.value if hasattr(rec.urgency, "value") else str(rec.urgency),
                        "status": rec.status.value if hasattr(rec.status, "value") else str(rec.status),
                        "suggested_actions": rec.suggested_actions,
                        "created_at": str(rec.created_at)
                    }
            except Exception as e:
                logger.warning(f"Error fetching recommendation fallback from DB for {merchant_id}: {e}")

        return None

    @classmethod
    def list_active_recommendations(
        cls,
        merchant_id: str,
        db: Optional[Session] = None
    ) -> List[Dict[str, Any]]:
        """List all active recommendations from Redis, fallback to DB."""
        redis = get_redis_client()
        if redis:
            try:
                active_key = cls._key_active(merchant_id)
                raw_dict = redis.hgetall(active_key)
                if raw_dict:
                    return [json.loads(v) for v in raw_dict.values()]
            except Exception as e:
                logger.warning(f"Error reading active recommendations from Redis for {merchant_id}: {e}")

        if db:
            try:
                from app.models.recommendation import Recommendation, RecommendationStatus
                recs = db.query(Recommendation).filter(
                    Recommendation.merchant_id == merchant_id,
                    Recommendation.status == RecommendationStatus.PENDING
                ).order_by(Recommendation.created_at.desc()).limit(10).all()
                return [
                    {
                        "id": str(r.id),
                        "merchant_id": str(r.merchant_id),
                        "recommendation_text": r.recommendation_text,
                        "title": getattr(r, "title", None) or r.recommendation_text[:40],
                        "urgency": r.urgency.value if hasattr(r.urgency, "value") else str(r.urgency),
                        "status": r.status.value if hasattr(r.status, "value") else str(r.status),
                        "suggested_actions": r.suggested_actions,
                        "created_at": str(r.created_at)
                    }
                    for r in recs
                ]
            except Exception as e:
                logger.warning(f"Error listing recommendations fallback from DB for {merchant_id}: {e}")

        return []

    @classmethod
    def invalidate_recommendation(
        cls,
        merchant_id: str,
        rec_id: Optional[str] = None
    ) -> bool:
        """Remove a recommendation (e.g. after approval, rejection, or expiry)."""
        redis = get_redis_client()
        if not redis:
            return False

        try:
            active_key = cls._key_active(merchant_id)
            if rec_id:
                redis.hdel(active_key, rec_id)
                redis.delete(cls._key_rec(merchant_id, rec_id))
            else:
                redis.delete(active_key)
            return True
        except Exception as e:
            logger.warning(f"Failed to invalidate recommendation in Redis for {merchant_id}: {e}")
            return False
