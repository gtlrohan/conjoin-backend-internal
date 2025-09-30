
from sqlalchemy import CheckConstraint, Column, ForeignKey, Integer, Numeric, String
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy.orm import relationship

from app.postgres.database import Base
from app.postgres.models.card import CategoryEnum


class UserPreferences(Base):
    __tablename__ = "UserPreferences"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("User.user_id"), nullable=False)
    preferenceName = Column(String, nullable=False)
    preferenceMetric = Column(Numeric, CheckConstraint('"preferenceMetric" >= 0 AND "preferenceMetric" <= 1'), nullable=True)
    category = Column(SQLAlchemyEnum(CategoryEnum), nullable=False)

    user = relationship("User", back_populates="preferences")
