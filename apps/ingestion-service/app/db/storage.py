from sqlalchemy import create_engine, Column, String, Float, JSON, DateTime, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
import redis
import json
from datetime import datetime
from contextlib import contextmanager

Base = declarative_base()

# Only set up DB if DATABASE_URL is configured
if settings.DATABASE_URL:
    engine = create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=300,
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
else:
    engine = None
    SessionLocal = None


class PodcastEntity(Base):
    __tablename__ = "podcasts_metadata"

    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String, unique=True, index=True)
    title = Column(String)
    description = Column(String, nullable=True)
    rating = Column(Float, default=0.0)
    categories = Column(JSON)  # List[str]
    metadata_json = Column(JSON)  # Full normalized metadata
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class RedisCache:
    def __init__(self):
        self.r = None
        self.ttl = 86400  # 24 hours
        if settings.REDIS_URL:
            try:
                self.r = redis.from_url(settings.REDIS_URL, decode_responses=True)
            except Exception as e:
                print(f"[RedisCache] Redis init failed: {e}")

    def get_podcast(self, external_id: str):
        if not self.r:
            return None
        data = self.r.get(f"ingestion:podcast:{external_id}")
        return json.loads(data) if data else None

    def set_podcast(self, external_id: str, data: dict):
        if not self.r:
            return
        self.r.setex(f"ingestion:podcast:{external_id}", self.ttl, json.dumps(data))


# Create tables only if DB is configured
if engine is not None:
    Base.metadata.create_all(bind=engine)

