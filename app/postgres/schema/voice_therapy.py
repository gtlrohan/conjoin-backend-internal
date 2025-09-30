from datetime import datetime

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.postgres.database import Base


class VoiceTherapySession(Base):
    __tablename__ = "voice_therapy_sessions"

    session_id = Column(String, primary_key=True, index=True)  # This is now OpenAI's session ID
    user_id = Column(Integer, ForeignKey("User.user_id"), nullable=False)
    therapy_type = Column(String, nullable=False)  # general, anxiety, stress, depression, sleep
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    session_summary = Column(Text, nullable=True)
    mood_before = Column(String, nullable=True)
    mood_after = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Transcript storage for chat integration
    transcript = Column(JSON, nullable=True)  # Store full conversation as array of messages

    # OpenAI Realtime API fields
    openai_session_id = Column(String, nullable=False)  # Store OpenAI's internal session ID
    ephemeral_token_expires = Column(DateTime, nullable=True)  # Track token expiration
    # Optional link to a specific user card that initiated session
    linked_user_card_id = Column(Integer, ForeignKey("UserCard.card_id"), nullable=True)

    # Relationship to User
    user = relationship("User", back_populates="voice_therapy_sessions")

    def __repr__(self):
        return (
            f"<VoiceTherapySession(session_id={self.session_id}, user_id={self.user_id}, "
            f"therapy_type={self.therapy_type}, start_time={self.start_time}, "
            f"duration_minutes={self.duration_minutes})>"
        )
