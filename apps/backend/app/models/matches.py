from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Integer, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from .database import Base

class InteractionType(enum.Enum):
    LIKE = "like"
    DISLIKE = "dislike"

class Interaction(Base):
    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True, index=True)
    actor_id = Column(String, index=True)  # User performing the action
    target_id = Column(String, index=True) # User receiving the action
    interaction_type = Column(Enum(InteractionType))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Match(Base):
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True, index=True)
    user_one_id = Column(String, index=True)
    user_two_id = Column(String, index=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    matched_at = Column(DateTime(timezone=True), server_default=func.now())
