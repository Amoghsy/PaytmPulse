import json
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.core.redis import get_redis_client
from app.memory.config import REDIS_RECENT_TRANSACTION_TTL, REDIS_MAX_RECENT_TRANSACTIONS
from app.models.transaction import Transaction

logger = logging.getLogger("paytm_pulse.memory.transaction")


class TransactionMemory:
    """
    Maintains a rolling, short-term buffer of recent transactions in Redis
    with graceful fallback to PostgreSQL.
    """

    @staticmethod
    def _key(merchant_id: str) -> str:
        return f"merchant:{merchant_id}:recent_transactions"

    @classmethod
    def push_transaction(cls, merchant_id: str, tx_data: Dict[str, Any]) -> bool:
        """
        Pushes a transaction payload to the head of the Redis list, trims to max capacity, and refreshes TTL.
        """
        try:
            r = get_redis_client()
            if not r:
                return False
            key = cls._key(merchant_id)
            serialized = json.dumps(tx_data, default=str)
            r.lpush(key, serialized)
            r.ltrim(key, 0, REDIS_MAX_RECENT_TRANSACTIONS - 1)
            r.expire(key, REDIS_RECENT_TRANSACTION_TTL)
            logger.debug(f"[REDIS] Pushed recent transaction for merchant {merchant_id}")
            return True
        except Exception as e:
            logger.warning(f"Failed to push transaction memory for merchant {merchant_id}: {e}")
            return False

    @classmethod
    def get_recent_transactions(
        cls,
        merchant_id: str,
        limit: int = 50,
        db: Optional[Session] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetches recent transactions from Redis fast memory.
        If Redis returns empty and a db session is provided, gracefully falls back to PostgreSQL.
        """
        try:
            r = get_redis_client()
            if r:
                key = cls._key(merchant_id)
                raw_items = r.lrange(key, 0, limit - 1)
                if raw_items:
                    logger.debug(f"[REDIS] Cache HIT: {len(raw_items)} recent transactions for merchant {merchant_id}")
                    return [json.loads(item) for item in raw_items]
        except Exception as e:
            logger.warning(f"Failed to read transaction memory for merchant {merchant_id}: {e}")

        # PostgreSQL Fallback
        if db is not None:
            try:
                txs = db.query(Transaction).filter(
                    Transaction.merchant_id == merchant_id
                ).order_by(Transaction.created_at.desc()).limit(limit).all()

                logger.debug(f"[DB] Fallback: fetched {len(txs)} transactions from PostgreSQL for merchant {merchant_id}")
                return [
                    {
                        "id": str(t.id),
                        "transaction_id": str(t.id),
                        "merchant_id": str(t.merchant_id),
                        "product_id": str(t.product_id) if t.product_id else None,
                        "product_name": t.product.name if getattr(t, "product", None) else "Item",
                        "quantity": t.quantity,
                        "unit_price": float(t.unit_price) if t.unit_price else 0.0,
                        "amount": float(t.amount),
                        "payment_method": t.payment_method.value if hasattr(t.payment_method, "value") else str(t.payment_method),
                        "transaction_timestamp": t.transaction_timestamp.isoformat() if t.transaction_timestamp else t.created_at.isoformat()
                    }
                    for t in txs
                ]
            except Exception as e:
                logger.error(f"Database fallback query failed for merchant {merchant_id}: {e}")

        return []

    @classmethod
    def clear_recent_transactions(cls, merchant_id: str) -> bool:
        try:
            r = get_redis_client()
            if r:
                r.delete(cls._key(merchant_id))
                return True
        except Exception as e:
            logger.warning(f"Failed to clear transaction memory for {merchant_id}: {e}")
        return False
