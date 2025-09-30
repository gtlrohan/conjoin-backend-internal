import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.middleware.jwt import JWTBearer, decodeJWT
from app.postgres.crud.fitbit_sleep import (
    retrieve_users_sleep_by_date,
    retrieve_users_sleep_by_date_range,
)
from app.postgres.database import get_db

router = APIRouter(prefix="/biometrics/fitbit/internal", tags=["Internal Fitbit APIs"])

# initiates logger
log = logging.getLogger(__name__)


@router.get("/sleep/date")
async def get_sleep_log_by_date(
    date: datetime = Query(..., description="Date of the sleep log in the format yyyy-MM-dd"),
    access_token: str = Depends(JWTBearer()),
    db: Session = Depends(get_db),
):
    """
    Retrieves user's fitbit sleep log for a specific date that is stored in our DB
    """
    try:
        token = decodeJWT(access_token)
        user_id = token["user_id"]
        return retrieve_users_sleep_by_date(user_id=user_id, date=date, db=db)

    except Exception as e:
        raise HTTPException(status_code=404, detail=f"{e}") from None


@router.get("/sleep/date-range")
async def get_sleep_log_by_date_range(
    start_date: datetime = Query(..., description="Start date (inclusive) of the sleep log in the format yyyy-MM-dd"),
    end_date: datetime = Query(..., description="End date (inclusive) of the sleep log in the format yyyy-MM-dd"),
    access_token: str = Depends(JWTBearer()),
    db: Session = Depends(get_db),
):
    """
    Retrieves user's fitbit sleep log for a specific date that is stored in our DB
    """
    try:
        token = decodeJWT(access_token)
        user_id = token["user_id"]
        return retrieve_users_sleep_by_date_range(user_id=user_id, start_date=start_date, end_date=end_date, db=db)

    except Exception as e:
        raise HTTPException(status_code=404, detail=f"{e}") from None
