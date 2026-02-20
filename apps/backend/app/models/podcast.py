from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Boolean, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

class PodcastType(str):
    PODCAST = "podcast"
    SHOW = "show"

class Podcast(Base):
    __tablename__ = "podcasts"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    slug = Column(String, unique=True, index=True)
    description = Column(String)
    cover_image = Column(String)
    website_url = Column(String)
    rss_feed_url = Column(String)
    
    # Metadata
    topics = Column(JSON, default=[]) # e.g. ["Tech", "Business"]
    category = Column(String)
    language = Column(String, default="English")
    
    # Stats
    monthly_listeners = Column(String) # e.g. "10k-50k"
    episode_count = Column(Integer, default=0)
    
    # Association
    # A podcast can have many hosts (users)
    # This requires adding 'podcasts' relationship to User model
    hosts = relationship("User", secondary="podcast_hosts", back_populates="podcasts")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class PodcastHost(Base):
    __tablename__ = "podcast_hosts"
    
    podcast_id = Column(Integer, ForeignKey("podcasts.id"), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    
    role = Column(String, default="host") # "host", "producer", "guest_host"
    is_primary = Column(Boolean, default=False) # Main host shown on profile cards
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
