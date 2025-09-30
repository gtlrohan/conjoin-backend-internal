from datetime import datetime, time
from enum import Enum

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Interval,
    String,
    Boolean,
)
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import backref, relationship

from app.postgres.database import Base
from app.postgres.models.card import CategoryEnum, HowWasIt, CompletionLevel, CardType, CardStatus, SpecialActions

# from app.postgres.schema.objective import Objective
# from app.postgres.schema.mh_categories import MHCategory


class TimeOfDay(Enum):
    MORNING = (time(6, 0), time(12, 0))  # 6:00 AM to 12:00 PM
    AFTERNOON = (time(12, 0), time(17, 0))  # 12:00 PM to 5:00 PM
    EVENING = (time(17, 0), time(21, 0))  # 5:00 PM to 9:00 PM
    NIGHT = (time(21, 0), time(6, 0))  # 9:00 PM to 6:00 AM
    ANY = (time(0, 0), time(23, 59, 59))  # All day

    def __init__(self, start, end):
        self.start = start
        self.end = end

    def is_time_in_range(self, t):
        if self == TimeOfDay.ANY:
            return True
        elif self == TimeOfDay.NIGHT:
            return t >= self.start or t < self.end
        else:
            return self.start <= t < self.end

    def __str__(self):
        return self.name


class CardCompletionDetail(Base):
    __tablename__ = "CardCompletionDetail"

    id = Column(Integer, primary_key=True, index=True)
    card_id = Column(Integer, ForeignKey("UserCard.card_id"), nullable=False)
    status = Column(SQLAlchemyEnum(CardStatus), nullable=False, default=CardStatus.ongoing)
    completion_level = Column(SQLAlchemyEnum(CompletionLevel), nullable=False)
    how_was_it = Column(SQLAlchemyEnum(HowWasIt), nullable=False)
    reason = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_positive = Column(Boolean, nullable=True)

    # Relationships
    card_completion = relationship("UserCard", back_populates="completion_details")
    score_impacts = relationship("CognitiveScoreImpact", back_populates="card_completion")

    def __repr__(self):
        return (
            f"<CardCompletionDetail(id={self.id}, card_id={self.card_id}, status={self.status}, "
            f"completion_level={self.completion_level}, how_was_it={self.how_was_it}, "
            f"reason={self.reason}, created_at={self.created_at})>"
        )


class CardDetail(Base):
    __tablename__ = "CardDetail"

    id = Column(Integer, primary_key=True, index=True)
    card_type = Column(SQLAlchemyEnum(CardType), nullable=False)
    title = Column(String(255), nullable=False)
    category = Column(SQLAlchemyEnum(CategoryEnum), nullable=True)
    details = Column(JSONB)
    # objective_id = Column(Integer, ForeignKey("Objective.id"), nullable=False)
    description = Column(String(255), nullable=True)
    duration = Column(Interval, nullable=False)  # Length of time card is expected to take
    tod = Column(SQLAlchemyEnum(TimeOfDay), nullable=True)  # time of day the card can be set
    special_card_action = Column(SQLAlchemyEnum(SpecialActions), nullable=True)
    affirmation_number = Column(Integer, nullable=True)

    # One-to-one relationship with UserCard
    user_card = relationship("UserCard", back_populates="card_details", uselist=False)

    card_mh_categories = relationship("CardMHCategory", back_populates="card_detail")

    # Relationship with Objective
    # objective = relationship("Objective", back_populates="card_detail")

    def __repr__(self):
        tod_str = self.tod.name if hasattr(self.tod, "name") else "None"
        return (
            f"<CardDetail(id={self.id}, card_type={self.card_type}, title={self.title}, "
            f"category={self.category}, details={self.details}, description={self.description}, "
            f"duration={self.duration}, tod={str(tod_str)}, special_card_action={self.special_card_action})> , "
            f"affirmation_number={self.affirmation_number}"
        )


class UserCard(Base):
    __tablename__ = "UserCard"

    card_id = Column(Integer, primary_key=True, index=True)
    card_details_id = Column(Integer, ForeignKey("CardDetail.id"), nullable=False)
    time = Column(DateTime, nullable=False)  # Start time
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    user_id = Column(Integer, ForeignKey("User.user_id"))
    recurrence = Column(JSONB)
    calendar_event_id = Column(String, ForeignKey("GoogleCalendarEvents.id"), nullable=True)
    location = Column(String(255), nullable=True)

    # Relationship with User
    user = relationship("User", back_populates="cards")

    # Relationship with CalendarEvent
    calendar_event = relationship("CalendarEvent", backref=backref("cards", cascade="all, delete-orphan"))

    # Relationship with CardCompletionDetails
    completion_details = relationship("CardCompletionDetail", back_populates="card_completion")

    # Relationship with CardDetail
    card_details = relationship("CardDetail", back_populates="user_card")

    def __repr__(self):
        return (
            f"<UserCard(card_id={self.card_id}, card_details_id={self.card_details_id}, time={self.time}, "
            f"created_at={self.created_at}, user_id={self.user_id}, recurrence={self.recurrence}, "
            f"calendar_event_id={self.calendar_event_id}, location={self.location})>"
        )


class CardMHCategory(Base):
    __tablename__ = "card_mh_categories"

    id = Column(Integer, primary_key=True, index=True)
    card_detail_id = Column(Integer, ForeignKey("CardDetail.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("mh_categories.id"), nullable=False)
    severity = Column(Integer, nullable=True)

    # Relationships
    card_detail = relationship("CardDetail", back_populates="card_mh_categories")
    category = relationship("MHCategory", back_populates="card_categories")

    def __repr__(self):
        return f"<CardMHCategory(id={self.id}, card_detail_id={self.card_detail_id}, category_id={self.category_id})>"


class MHCategory(Base):
    __tablename__ = "mh_categories"

    id = Column(Integer, primary_key=True, index=True)
    category_name = Column(String(100), unique=True, nullable=False)

    # Relationship with CardMHCategory
    card_categories = relationship("CardMHCategory", back_populates="category")

    def __repr__(self):
        return f"<MHCategory(id={self.id}, category_name={self.category_name})>"
