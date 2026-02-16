from sqlalchemy import Column, String, DateTime, Integer
from sqlalchemy.sql import func
from .database import Base

class WaitlistEntry(Base):
    __tablename__ = "waitlist"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    role_interest = Column(String, nullable=True) # host, guest, or both
    fullName = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
