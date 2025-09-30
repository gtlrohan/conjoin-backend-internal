from sqlalchemy import Column, Integer, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
import datetime

from app.postgres.database import Base


class CognitiveFingerprint(Base):
    __tablename__ = "CognitiveFingerprint"

    fingerprint_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("User.user_id"), nullable=False)
    work_anxiety = Column(Float, nullable=False)
    social_anxiety = Column(Float, nullable=False)
    family_anxiety = Column(Float, nullable=False)
    eating_anxiety = Column(Float, nullable=False)
    sleeping_anxiety = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    # Define the relationship with User
    user = relationship("User", back_populates="cognitive_fingerprints")
