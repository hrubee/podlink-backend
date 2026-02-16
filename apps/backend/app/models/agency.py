from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Integer, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

# Association table for Agency Members (Agents/Managers)
agency_members = Table(
    "agency_members",
    Base.metadata,
    Column("agency_id", Integer, ForeignKey("agencies.id"), primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("role", String, default="member") # manager, admin, member
)

class Agency(Base):
    __tablename__ = "agencies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, index=True) # For white-label URLs
    website = Column(String, nullable=True)
    logo_url = Column(String, nullable=True)
    
    # Ownership
    owner_id = Column(Integer, ForeignKey("users.id"))
    
    # Relationships
    owner = relationship("User", foreign_keys=[owner_id])
    members = relationship("User", secondary=agency_members, back_populates="agencies")
    clients = relationship("User", backref="managed_by_agency", foreign_keys="User.agency_id") # Clients handled by this agency

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
