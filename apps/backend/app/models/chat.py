from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Integer, Text
from sqlalchemy.sql import func
from .database import Base

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(String, index=True) # Usually a combination of user IDs
    sender_id = Column(String, index=True)
    content = Column(Text)
    is_flagged = Column(Boolean, default=False)
    flagged_reason = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ChatRoom(Base):
    __tablename__ = "chat_rooms"
    
    id = Column(String, primary_key=True)
    user_one_id = Column(String, index=True)
    user_two_id = Column(String, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)
