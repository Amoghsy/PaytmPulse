import os
import json
import logging
import redis
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("paytm_pulse.redis")

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None) or None
RECENT_TX_LIMIT = int(os.getenv("REDIS_RECENT_TRANSACTION_LIMIT", 50))

actual_redis_host = REDIS_HOST
if actual_redis_host == "redis" and not os.path.exists("/.dockerenv"):
    actual_redis_host = "localhost"


def get_redis_client(host: str = actual_redis_host):
    return redis.Redis(
        host=host,
        port=REDIS_PORT,
        password=REDIS_PASSWORD,
        socket_timeout=1,
        socket_connect_timeout=1,
        decode_responses=True
    )


def check_redis_connection() -> bool:
    """
    Actually performs a Redis PING operation to verify connectivity.
    Returns True if healthy, False if unhealthy.
    """
    try:
        client = get_redis_client(actual_redis_host)
        return client.ping() is True
    except Exception as e:
        logger.warning(f"Redis connection health check failed: {str(e)}")
        return False


def push_recent_transaction(merchant_id: str, tx_data: dict):
    """
    Pushes a transaction JSON to merchant's recent transaction list in Redis.
    Safely falls back if Redis is offline.
    """
    try:
        client = get_redis_client()
        key = f"merchant:{merchant_id}:recent_tx"
        client.lpush(key, json.dumps(tx_data, default=str))
        client.ltrim(key, 0, RECENT_TX_LIMIT - 1)
    except Exception as e:
        logger.warning(f"Failed to push transaction to Redis for merchant {merchant_id}: {str(e)}")


def get_recent_transactions(merchant_id: str, limit: int = 50) -> list:
    """
    Retrieves recent transactions for a merchant from Redis list.
    """
    try:
        client = get_redis_client()
        key = f"merchant:{merchant_id}:recent_tx"
        raw_items = client.lrange(key, 0, limit - 1)
        return [json.loads(item) for item in raw_items]
    except Exception as e:
        logger.warning(f"Failed to fetch recent transactions from Redis for merchant {merchant_id}: {str(e)}")
        return []


def increment_merchant_counter(merchant_id: str, metric: str, amount: float = 1.0):
    """
    Increments a real-time counter metric (e.g., daily_sales, order_count) in Redis.
    """
    try:
        client = get_redis_client()
        key = f"merchant:{merchant_id}:{metric}"
        client.incrbyfloat(key, amount)
    except Exception as e:
        logger.warning(f"Failed to increment Redis counter {metric} for merchant {merchant_id}: {str(e)}")


def get_merchant_counter(merchant_id: str, metric: str) -> float:
    """
    Reads a real-time counter metric from Redis.
    """
    try:
        client = get_redis_client()
        key = f"merchant:{merchant_id}:{metric}"
        val = client.get(key)
        return float(val) if val else 0.0
    except Exception as e:
        logger.warning(f"Failed to read Redis counter {metric} for merchant {merchant_id}: {str(e)}")
        return 0.0


def get_key(key: str) -> str | None:
    """Gets a raw string value from Redis by key."""
    try:
        client = get_redis_client()
        return client.get(key)
    except Exception as e:
        logger.warning(f"Failed to get key {key} from Redis: {str(e)}")
        return None


def set_key(key: str, value: str, expire_seconds: int | None = None) -> bool:
    """Sets a string value in Redis with optional TTL."""
    try:
        client = get_redis_client()
        if expire_seconds:
            return bool(client.setex(key, expire_seconds, value))
        return bool(client.set(key, value))
    except Exception as e:
        logger.warning(f"Failed to set key {key} in Redis: {str(e)}")
        return False


def delete_key(key: str) -> bool:
    """Deletes a key from Redis."""
    try:
        client = get_redis_client()
        return bool(client.delete(key))
    except Exception as e:
        logger.warning(f"Failed to delete key {key} from Redis: {str(e)}")
        return False
