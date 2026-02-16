from sqlalchemy import create_engine, Column, String, Float, JSON, DateTime, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
import redis
import json
from datetime import datetime

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class PodcastEntity(Base):
    __tablename__ = "podcasts_metadata"
    
    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String, unique=True, index=True)
    title = Column(String)
    description = Column(String, nullable=True)
    rating = Column(Float, default=0.0)
    categories = Column(JSON) # List[str]
    metadata_json = Column(JSON) # Full normalized metadata
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class RedisCache:
    def __init__(self):
        self.r = redis.from_url(settings.REDIS_URL, decode_responses=True)
        self.ttl = 86400  # 24 hours

    def get_podcast(self, external_id: str):
        data = self.r.get(f"ingestion:podcast:{external_id}")
        return json.loads(data) if data else None

    def set_podcast(self, external_id: str, data: dict):
        self.r.setex(f"ingestion:podcast:{external_id}", self.ttl, json.dumps(data))

# Create tables
Base.metadata.create_all(bind=engine)
