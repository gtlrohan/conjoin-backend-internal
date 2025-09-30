import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    String,
)
from sqlalchemy.orm import relationship

from app.postgres.database import Base

# class CognitiveFingerprint(Base):
#     __tablename__ = "CognitiveFingerprint"

#     fingerprint_id = Column(Integer, primary_key=True, index=True)
#     user_id = Column(Integer, ForeignKey("User.user_id"), nullable=False)
#     work_anxiety = Column(Float, nullable=False)
#     social_anxiety = Column(Float, nullable=False)
#     family_anxiety = Column(Float, nullable=False)
#     eating_anxiety = Column(Float, nullable=False)
#     sleeping_anxiety = Column(Float, nullable=False)
#     created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

#     # Define the relationship with User
#     user = relationship("User", back_populates="cognitive_fingerprints")


class User(Base):
    __tablename__ = "User"
    user_id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=False)
    firstname = Column(String(255), nullable=False)
    surname = Column(String(255), nullable=False, default="")
    password = Column(String(255), nullable=False, default="")
    home = Column(String(255), nullable=True)
    office = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    completed_morning_orientation = Column(Boolean, default=False, nullable=True)
    completed_morning_orientation_date = Column(DateTime, default=None, nullable=True)

    # Define the relationship with Card
    cards = relationship("UserCard", back_populates="user")

    # Define the relationship with UserPreferences
    preferences = relationship("UserPreferences", back_populates="user")

    # Define the relationship with ExternalToken
    external_tokens = relationship("ExternalToken", back_populates="user")

    # Define the relationship with FitbitSleepLog
    fitbit_sleep_logs = relationship("FitbitSleepLog", back_populates="user")

    # Define the relationship with FitbitHeartLog
    fitbit_heart_logs = relationship("FitbitHeartLog", back_populates="user")

    # Define the relationship with Google CalendarEvent
    google_calendar_event = relationship("CalendarEvent", back_populates="user")

    # Define the relationship with cognitive score
    cognitive_scores = relationship("CognitiveScore", back_populates="user")

    # Define the relationship with cognitive fingerprint
    cognitive_fingerprints = relationship("CognitiveFingerprint", back_populates="user")

    # Define the relationship with voice therapy sessions
    voice_therapy_sessions = relationship("VoiceTherapySession", back_populates="user")

    # Define the relationship with mentor messages
    mentor_messages = relationship("MentorMessage", back_populates="user")

    # Define the relationship with wellness metrics
    wellness_metrics = relationship("DailyWellnessMetrics", back_populates="user")
