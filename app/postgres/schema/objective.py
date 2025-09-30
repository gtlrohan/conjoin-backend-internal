
from sqlalchemy import Column, Integer, String

from app.postgres.database import Base


class Objective(Base):
    __tablename__ = "Objective"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)

    # Relationship with CardDetail
    # card_detail = relationship("CardDetail", back_populates="objective")
