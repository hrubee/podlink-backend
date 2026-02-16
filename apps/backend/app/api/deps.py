from typing import Generator
import redis
from app.models.database import SessionLocal
from app.core.config import settings

def get_db() -> Generator:
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()

def get_redis() -> redis.Redis:
    return redis.from_url(settings.REDIS_URL)
