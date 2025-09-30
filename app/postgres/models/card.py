from typing import Any, List, Optional
from pydantic import BaseModel
from enum import Enum
from datetime import datetime


class CompletionLevel(str, Enum):
    partly = "partly"
    fully = "fully"
    incomplete = "incomplete"


class HowWasIt(str, Enum):
    terrible = "terrible"
    bad = "bad"
    ok = "ok"
    good = "good"
    awesome = "awesome"


class CardType(str, Enum):
    suggestion = "suggestion"
    calendar = "calendar"
    option = "option"


class ToD(str, Enum):
    MORNING = "MORNING"
    AFTERNOON = "AFTERNOON"
    EVENING = "EVENING"
    NIGHT = "NIGHT"
    ANY = "ANY"


class SpecialActions(str, Enum):
    NONE = "NONE"
    BREATHING = "BREATHING"
    AFFIRMATION = "AFFIRMATION"


class CategoryEnum(Enum):
    NUTRITION = "Nutrition"
    INNER_GOALS = "Inner goals"
    RELATIONSHIPS = "Relationships"
    HOBBIES = "Hobbies"
    SLEEP = "Sleep"
    EXERCISE = "Exercise"
    SELF_DEVELOPMENT = "Self development"
    MOOD = "Mood"


class CardStatus(str, Enum):
    ongoing = "ongoing"
    missed = "missed"
    completed = "completed"
    deleted = "deleted"


class CompletionDetails(BaseModel):
    card_id: int
    completion_level: CompletionLevel
    how_was_it: HowWasIt
    reason: str
    status: CardStatus
    time: datetime
    is_positive: bool


class Reschedule(BaseModel):
    card_id: int
    current_time: datetime


class ConfirmReschedule(BaseModel):
    card_id: int
    new_time: str


class CardDetails(BaseModel):
    card_type: str
    id: int
    category: str
    description: Optional[str] = None
    title: str
    details: dict[str, Any]
    duration: float
    special_card_action: Optional[str] = None
    affirmation_number: Optional[int] = None


class CardData(BaseModel):
    card_id: int
    time: datetime
    created_at: datetime
    user_id: int
    location: Optional[str] = None
    recurrence: Optional[List[Any]] = None
    calendar_event_id: Optional[str] = None
    card_details: CardDetails
    status: str


class CognitiveFingerprintUpdate(BaseModel):
    type: str
    value: float
