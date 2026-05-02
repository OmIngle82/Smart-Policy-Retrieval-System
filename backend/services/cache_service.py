import os
import json
import logging
import redis
from typing import Optional, Any

logger = logging.getLogger(__name__)

class CacheService:
    def __init__(self):
        self.redis_client = None
        self.enabled = os.getenv("ENABLE_CACHE", "true").lower() == "true"
        
        if self.enabled:
            try:
                self.redis_client = redis.Redis(
                    host=os.getenv("REDIS_HOST", "localhost"),
                    port=int(os.getenv("REDIS_PORT", 6379)),
                    db=int(os.getenv("REDIS_DB", 0)),
                    decode_responses=True,
                    socket_timeout=1
                )
                # Only ping if not in a test environment (dummy check)
                if os.getenv("PYTEST_CURRENT_TEST") is None:
                    self.redis_client.ping()
                    logger.info("Connected to Redis for caching.")
                else:
                    logger.info("Test environment detected. Skipping Redis ping.")
            except (redis.ConnectionError, redis.TimeoutError):
                logger.warning("Redis not found or connection timed out. Caching will be disabled for this session.")
                self.redis_client = None

    def get(self, key: str) -> Optional[Any]:
        if not self.redis_client:
            return None
        try:
            data = self.redis_client.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None

    def set(self, key: str, value: Any, expire: int = 3600):
        if not self.redis_client:
            return
        try:
            self.redis_client.set(key, json.dumps(value), ex=expire)
        except Exception as e:
            logger.error(f"Cache set error: {e}")

    def generate_key(self, question: str, mode: str, sources: Optional[list] = None) -> str:
        # Simple key generation based on question and context
        import hashlib
        context_str = f"{question}:{mode}:{str(sources)}"
        return "query:" + hashlib.md5(context_str.encode()).hexdigest()

# Singleton instance
cache_service = CacheService()
