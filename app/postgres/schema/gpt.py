from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.postgres.database import Base


class MentorMessage(Base):
    __tablename__ = "mentor_messages"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("User.user_id"), nullable=False)
    role = Column(String(20), nullable=False)  # 'user', 'assistant', 'system'
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    message_type = Column(String(20), default="text")  # 'text', 'voice_session', 'system'
    session_id = Column(String(100), nullable=True)  # For voice therapy sessions
    message_count = Column(Integer, nullable=True)  # Number of messages in voice session

    # Relationship to User - use string reference to avoid circular imports
    user = relationship("User", back_populates="mentor_messages")

    def __repr__(self):
        return f"<MentorMessage(id={self.id}, user_id={self.user_id}, role={self.role})>"
