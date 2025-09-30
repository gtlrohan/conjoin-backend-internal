from sqlalchemy import BigInteger, Column, Date, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.postgres.database import Base


# Table to store general heart data information
class FitbitHeartLog(Base):
    __tablename__ = "FitbitHeartLog"

    log_id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("User.user_id"), nullable=False)
    date_time = Column(Date, nullable=False)
    resting_heart_rate = Column(Integer)

    # Relationship to User
    user = relationship("User", back_populates="fitbit_heart_logs")
    # Relationship to HeartRateZone
    heart_rate_zones = relationship("FitbitHeartRateZone", back_populates="heart_log")
    # Relationship to CustomHeartRateZone
    custom_heart_rate_zones = relationship("FitbitCustomHeartRateZone", back_populates="heart_log")


# Table to store detailed heart rate zone data for each heart log
class FitbitHeartRateZone(Base):
    __tablename__ = "FitbitHeartRateZone"

    id = Column(Integer, primary_key=True, index=True)
    log_id = Column(BigInteger, ForeignKey("FitbitHeartLog.log_id"), nullable=False)
    name = Column(String(50), nullable=False)
    min = Column(Integer, nullable=False)
    max = Column(Integer, nullable=False)
    minutes = Column(Integer, nullable=False)
    calories_out = Column(Float, nullable=False)

    # Relationship to HeartLog
    heart_log = relationship("FitbitHeartLog", back_populates="heart_rate_zones")


# Table to store custom heart rate zone data for each heart log
class FitbitCustomHeartRateZone(Base):
    __tablename__ = "FitbitCustomHeartRateZone"

    id = Column(Integer, primary_key=True, index=True)
    log_id = Column(BigInteger, ForeignKey("FitbitHeartLog.log_id"), nullable=False)
    name = Column(String(50), nullable=False)
    min = Column(Integer, nullable=False)
    max = Column(Integer, nullable=False)
    minutes = Column(Integer, nullable=False)
    calories_out = Column(Float, nullable=False)

    # Relationship to HeartLog
    heart_log = relationship("FitbitHeartLog", back_populates="custom_heart_rate_zones")
