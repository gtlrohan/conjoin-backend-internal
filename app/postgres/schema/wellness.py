from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
)
from sqlalchemy.orm import relationship

from app.postgres.database import Base


class DailyWellnessMetrics(Base):
    __tablename__ = "daily_wellness_metrics"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("User.user_id"), nullable=False)
    energy_level = Column(Float, nullable=False)
    stress_level = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    date = Column(Date, default=date.today, nullable=False)

    # Add check constraints to ensure values are between 1.0-10.0 (allowing decimals)
    __table_args__ = (
        CheckConstraint("energy_level >= 0.0 AND energy_level <= 10.0", name="check_energy_level_range"),
        CheckConstraint("stress_level >= 0.0 AND stress_level <= 10.0", name="check_stress_level_range"),
    )

    # Define the relationship with User
    user = relationship("User", back_populates="wellness_metrics")

    def __repr__(self):
        return (
            f"<DailyWellnessMetrics(id={self.id}, user_id={self.user_id}, "
            f"energy_level={self.energy_level}, stress_level={self.stress_level}, "
            f"date={self.date})>"
        )
