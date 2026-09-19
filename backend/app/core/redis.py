import os
import logging
import redis
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("paytm_pulse.core.redis")

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None) or None
REDIS_URL = os.getenv("REDIS_URL", None)

actual_redis_host = REDIS_HOST
if actual_redis_host == "redis" and not os.path.exists("/.dockerenv"):
    actual_redis_host = "localhost"


def get_redis_client(host: str = actual_redis_host) -> Optional[redis.Redis]:
    """
    Returns a connected, decoded Redis client or None if connection fails.
    """
    try:
        if REDIS_URL and os.path.exists("/.dockerenv"):
            client = redis.from_url(
                REDIS_URL,
                socket_timeout=1,
                socket_connect_timeout=1,
                decode_responses=True
            )
        else:
            client = redis.Redis(
                host=host,
                port=REDIS_PORT,
                password=REDIS_PASSWORD,
                socket_timeout=1,
                socket_connect_timeout=1,
                decode_responses=True
            )
        return client
    except Exception as e:
        logger.warning(f"Could not initialize Redis client: {e}")
        return None


def check_redis_connection() -> bool:
    """
    Performs a Redis PING check. Returns True if responsive, False otherwise.
    """
    try:
        client = get_redis_client()
        if client:
            return client.ping() is True
        return False
    except Exception as e:
        logger.warning(f"Redis connection check failed: {e}")
        return False


check_redis_health = check_redis_connection
