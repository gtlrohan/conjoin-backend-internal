from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import relationship

from app.postgres.database import Base


# Table to store general sleep log information
class FitbitSleepLog(Base):
    __tablename__ = "FitbitSleepLog"
    log_id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("User.user_id"), nullable=False)
    date_of_sleep = Column(Date, nullable=False)
    duration = Column(Integer, nullable=False)
    efficiency = Column(Integer)
    end_time = Column(DateTime)
    info_code = Column(Integer)
    is_main_sleep = Column(Boolean)
    minutes_after_wakeup = Column(Integer)
    minutes_asleep = Column(Integer)
    minutes_awake = Column(Integer)
    minutes_to_fall_asleep = Column(Integer)
    start_time = Column(DateTime)
    time_in_bed = Column(Integer)
    log_type = Column(String(50))
    sleep_type = Column(String(50))

    # Relationship to User
    user = relationship("User", back_populates="fitbit_sleep_logs")
    # Relationship to SleepLevel
    sleep_levels = relationship("FitbitSleepLevel", back_populates="sleep_log")
    # Relationship to SleepSummary
    sleep_summaries = relationship("FitbitSleepSummary", back_populates="sleep_log")


# Table to store detailed levels data for each sleep log
class FitbitSleepLevel(Base):
    __tablename__ = "FitbitSleepLevel"
    id = Column(Integer, primary_key=True, index=True)
    log_id = Column(BigInteger, ForeignKey("FitbitSleepLog.log_id"), nullable=False)
    date_time = Column(DateTime, nullable=False)
    level = Column(String(50), nullable=False)
    seconds = Column(Integer, nullable=False)

    # Relationship to SleepLog
    sleep_log = relationship("FitbitSleepLog", back_populates="sleep_levels")


# Table to store summary data for each sleep log
class FitbitSleepSummary(Base):
    __tablename__ = "FitbitSleepSummary"
    id = Column(Integer, primary_key=True, index=True)
    log_id = Column(BigInteger, ForeignKey("FitbitSleepLog.log_id"), nullable=False)
    level_type = Column(String(50), nullable=False)
    count = Column(Integer, nullable=False)
    minutes = Column(Integer, nullable=False)
    thirty_day_avg_minutes = Column(Integer, nullable=True)

    # Relationship to SleepLog
    sleep_log = relationship("FitbitSleepLog", back_populates="sleep_summaries")
