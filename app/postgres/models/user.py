from datetime import datetime
from typing import List

from pydantic import BaseModel

from app.postgres.models.card import CardData


class UserLogin(BaseModel):
    email: str
    password: str


class UserCreate(BaseModel):
    email: str
    password: str
    firstname: str
    surname: str


class User(BaseModel):
    user_id: int
    email: str
    time_created: datetime

    class Config:
        from_attributes = True


class MorningOrientationRequest(BaseModel):
    time: datetime


class MorningOrientationAltTimeRequest(BaseModel):
    cards: List[CardData]
    current_time: datetime
