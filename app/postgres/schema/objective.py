from datetime import datetime
from enum import Enum

from sqlalchemy import ARRAY, Column, DateTime, Float, ForeignKey, Integer, Interval, String, Table
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy.orm import backref, relationship

from app.postgres.database import Base


class Objective(Base):
    __tablename__ = "Objective"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)

    # Relationship with CardDetail
    # card_detail = relationship("CardDetail", back_populates="objective")
