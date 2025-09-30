from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.middleware.jwt import JWTBearer, decodeJWT
from app.postgres.crud.card import retrieve_completed_cards_with_score
from app.postgres.crud.cognitive_score import retrieve_cognitive_score, retrieve_user_cognitive_score_impacts
from app.postgres.database import get_db

router = APIRouter(prefix="/scores", tags=["Scores"])


@router.get("/cognitive-score-impacts")
def get_cognitive_score_impacts_between_date_range(
    startDate: datetime = Query(..., example="2024-06-01T00:00:00"),
    endDate: datetime = Query(..., example="2024-06-30T23:59:59"),
    db: Session = Depends(get_db),
    access_token: str = Depends(JWTBearer()),
):
    token = decodeJWT(access_token)
    user_id = token["user_id"]
    current_score = retrieve_cognitive_score(db, user_id)

    # Filter scores to only include those exactly on the original startDate
    start_date_scores = retrieve_user_cognitive_score_impacts(db, user_id, startDate, endDate)

    return {
        "current_score": current_score.score,
        "scores": start_date_scores,
    }


@router.get("/cognitive-score-breakdown")
def get_cognitive_score_impacts_between_date_range(
    startDate: datetime = Query(..., example="2024-06-01T00:00:00"),
    endDate: datetime = Query(..., example="2024-06-30T23:59:59"),
    db: Session = Depends(get_db),
    access_token: str = Depends(JWTBearer()),
):
    token = decodeJWT(access_token)
    user_id = token["user_id"]
    scores_breakdown = retrieve_completed_cards_with_score(db, user_id, startDate, endDate)
    current_score = retrieve_cognitive_score(db, user_id)

    return {"current_score": current_score.score, "scores": scores_breakdown}
