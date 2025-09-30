from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.postgres.database import Base


class ExternalToken(Base):
    __tablename__ = "ExternalTokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("User.user_id"), nullable=False)
    service_name = Column(String(100), nullable=False)
    token_type = Column(String(50), nullable=False)
    token_value = Column(String(1024), nullable=False)
    expires_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="external_tokens")
