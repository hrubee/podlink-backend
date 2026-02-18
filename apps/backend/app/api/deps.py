from typing import Generator, Optional
import redis
from app.models.database import SessionLocal
from app.core.config import settings


def get_db() -> Generator:
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()


class NoOpRedis:
    """
    A no-op Redis stub used when REDIS_URL is not configured.
    All operations silently succeed/return safe defaults so the app
    doesn't crash. Features that depend on Redis (quota, matching limits,
    real-time chat pub/sub) will degrade gracefully.
    """
    def get(self, *a, **kw): return None
    def set(self, *a, **kw): return True
    def setex(self, *a, **kw): return True
    def exists(self, *a, **kw): return 0
    def incr(self, *a, **kw): return 1
    def expire(self, *a, **kw): return True
    def delete(self, *a, **kw): return 0
    def sadd(self, *a, **kw): return 0
    def srem(self, *a, **kw): return 0
    def smembers(self, *a, **kw): return set()
    def sismember(self, *a, **kw): return False
    def zadd(self, *a, **kw): return 0
    def zcard(self, *a, **kw): return 0
    def zremrangebyscore(self, *a, **kw): return 0
    def hincrby(self, *a, **kw): return 0
    def publish(self, *a, **kw): return 0
    def from_url(self, *a, **kw): return self


_redis_client: Optional[redis.Redis] = None

def get_redis() -> redis.Redis:
    """Returns a Redis client, or a no-op stub if REDIS_URL is not configured."""
    global _redis_client
    if not settings.REDIS_URL:
        return NoOpRedis()
    if _redis_client is None:
        _redis_client = redis.from_url(settings.REDIS_URL, decode_responses=False)
    return _redis_client

