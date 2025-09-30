from datetime import datetime
from sqlalchemy import (
    ARRAY,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
)
from sqlalchemy.orm import relationship
from app.postgres.database import Base


class CognitiveScore(Base):
    __tablename__ = "CognitiveScore"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("User.user_id"), nullable=False)
    score = Column(Numeric(precision=10, scale=2))

    # Relationships
    user = relationship("User", back_populates="cognitive_scores")
    impacts = relationship("CognitiveScoreImpact", back_populates="cognitive_score")


class CognitiveScoreImpact(Base):
    __tablename__ = "CognitiveScoreImpact"

    id = Column(Integer, primary_key=True, index=True)
    cognitive_score_id = Column(Integer, ForeignKey("CognitiveScore.id"), nullable=False)
    card_completion_id = Column(Integer, ForeignKey("CardCompletionDetail.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    value = Column(Numeric(precision=10, scale=2))
    new_cognitive_score = Column(Numeric(precision=10, scale=2))

    # Relationships
    cognitive_score = relationship("CognitiveScore", back_populates="impacts")
    card_completion = relationship("CardCompletionDetail", back_populates="score_impacts")
