from typing import List

from fastapi import APIRouter, Depends, Form
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.middleware.jwt import JWTBearer, decodeJWT
from app.postgres.crud.goal import (
    create_goal,
    create_goals2card_from_list,
    create_user_goal,
    retrieve_all_goals,
)
from app.postgres.database import get_db

router = APIRouter(prefix="/goals", tags=["Goals"])


@router.get("/")
def get_goals(
    db: Session = Depends(get_db),
    access_token: str = Depends(JWTBearer()),
):
    return retrieve_all_goals(db=db)


@router.post("/create")
def creates_a_new_goal(
    name: str = Form(..., description="Name of goal"),
    db: Session = Depends(get_db),
    access_token: str = Depends(JWTBearer()),
):
    return create_goal(db=db, name=name)


@router.post("/create-user-goal")
def creates_a_new_user_goal(
    goal_id: int = Form(..., description="Goal id"),
    target: int = Form(..., description="Target"),
    db: Session = Depends(get_db),
    access_token: str = Depends(JWTBearer()),
):
    token = decodeJWT(access_token)
    user_id = token["user_id"]
    return create_user_goal(db=db, user_id=user_id, goal_id=goal_id, target=target)


# First, create a Pydantic model for your individual goal2card item
class Goal2CardCreate(BaseModel):
    card_id: int
    goal_id: int
    goal_name: str
    card_detail_title: str

    class Config:
        # This allows the model to be used with ORMs
        orm_mode = True


@router.post("/add-goals2card")
async def add_goals2card_endpoint(
    body: List[Goal2CardCreate],
    db: Session = Depends(get_db),
    access_token: str = Depends(JWTBearer()),
):
    created_entries = create_goals2card_from_list(db, body)
    return created_entries
