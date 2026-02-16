from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Enum, Integer
import enum
from app.models.database import Base
from datetime import datetime
import uuid

class ReportStatus(str, enum.Enum):
    PENDING = "pending"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"

class UserReport(Base):
    __tablename__ = "user_reports"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    reporter_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    target_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    reason = Column(String, nullable=False)
    details = Column(Text)
    status = Column(Enum(ReportStatus), default=ReportStatus.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    admin_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String, nullable=False) # e.g., "BAN_USER", "RESOLVE_REPORT"
    target_id = Column(Integer, nullable=True) # Usually a user ID
    metadata_json = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
