from sqlalchemy import Column, String, DateTime, Boolean, Enum, Integer, ForeignKey, JSON, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from .database import Base

# Imports required for resolving string-based relationships
from .agency import Agency, agency_members
from .podcast import Podcast, PodcastHost

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

    # ── Core Profile ──────────────────────────────────────────────────────────
    bio = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)
    location = Column(String, nullable=True)
    timezone = Column(String, nullable=True)          # e.g. "UTC+5:30 (IST)"
    onboarded = Column(Boolean, default=False)

    # ── Matching Signals (Content-Based AI) ───────────────────────────────────
    topics = Column(JSON, default=[])                 # List of niche tags
    target_audience = Column(String, nullable=True)   # Free-text audience description
    language = Column(String, default="English")
    engagement_style = Column(JSON, default=[])       # ["storytelling", "data_driven", ...]

    # ── Availability & Format Preferences ────────────────────────────────────
    interview_format = Column(String, default="both")         # remote | in_person | both
    episode_length_pref = Column(String, default="45-60")     # <30 | 30-45 | 45-60 | 60+
    content_rating = Column(String, default="clean")          # clean | explicit | both
    fee_expectation = Column(String, default="free")          # free | paid | negotiable

    # ── Platform Specifics ────────────────────────────────────────────────────
    social_links = Column(JSON, default={})           # {twitter, linkedin, youtube, website}
    host_details = Column(JSON, default={})           # podcast_name, podcast_desc, audience_size, episode_frequency, guest_wishlist, podcast_url
    guest_details = Column(JSON, default={})          # expertise_areas, topics_to_discuss, experience_years, past_appearances, media_kit_link

    # ── GDPR & State ──────────────────────────────────────────────────────────
    is_active = Column(Boolean, default=True)
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)
    is_public = Column(Boolean, default=True)

    # ── Subscription / Billing ────────────────────────────────────────────────
    subscription_status = Column(String, default="free")          # free | pro | agency
    subscription_ends_at = Column(DateTime(timezone=True), nullable=True)

    # ── Tracking ──────────────────────────────────────────────────────────────
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # ── Agency Links ──────────────────────────────────────────────────────────
    agency_id = Column(Integer, ForeignKey("agencies.id"), nullable=True)
    agencies = relationship("Agency", secondary="agency_members", back_populates="members")
    
    # ── Podcast Links ─────────────────────────────────────────────────────────
    podcasts = relationship("Podcast", secondary="podcast_hosts", back_populates="hosts")
