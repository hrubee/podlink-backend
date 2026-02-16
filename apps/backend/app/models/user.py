from sqlalchemy import Column, String, DateTime, Boolean, Enum, Integer, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from .database import Base

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    AGENCY = "agency"
    HOST = "host"
    GUEST = "guest"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    role = Column(Enum(UserRole), default=UserRole.GUEST)
    
    # Profile Data
    bio = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)
    location = Column(String, nullable=True)
    onboarded = Column(Boolean, default=False)
    
    # Structured Data for Matching (Collaborative Filtering)
    topics = Column(JSON, default=[]) # List of interest tags
    target_audience = Column(String, nullable=True)
    language = Column(String, default="English")
    
    # Platform Specifics
    social_links = Column(JSON, default={})
    host_details = Column(JSON, default={}) # podcast_name, podcast_desc, etc.
    guest_details = Column(JSON, default={}) # expertise, media_kit, etc.
    
    # GDPR & State
    is_active = Column(Boolean, default=True)
    is_deleted = Column(Boolean, default=False) # Soft delete
    deleted_at = Column(DateTime, nullable=True)
    
    # Profile Visibility
    is_public = Column(Boolean, default=True)
    
    # Tracking
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Agency Links
    agency_id = Column(Integer, ForeignKey("agencies.id"), nullable=True) # If this user is a 'client' of an agency
    agencies = relationship("Agency", secondary="agency_members", back_populates="members")
