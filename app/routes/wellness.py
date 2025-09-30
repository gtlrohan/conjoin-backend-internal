from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.middleware.jwt import JWTBearer, decodeJWT
from app.postgres.crud.wellness import (
    create_daily_wellness_metrics,
    delete_wellness_metrics,
    get_latest_wellness_metrics,
    get_user_wellness_metrics,
    get_wellness_metrics_by_date_range,
    get_wellness_stats,
)
from app.postgres.database import get_db
from app.postgres.models.wellness import (
    DailyWellnessListResponse,
    DailyWellnessRequest,
    DailyWellnessResponse,
    WellnessStatsResponse,
)

router = APIRouter(prefix="/wellness", tags=["Wellness Metrics"])


@router.post("/daily-metrics", response_model=DailyWellnessResponse)
def create_or_update_daily_wellness(
    wellness_data: DailyWellnessRequest,
    db: Session = Depends(get_db),
    access_token: str = Depends(JWTBearer()),
):
    """
    Create or update daily wellness metrics (energy level and stress level).

    - **energy_level**: Integer from 1 (very low) to 10 (very high)
    - **stress_level**: Integer from 1 (very low) to 10 (very high)

    If an entry already exists for today, it will be updated.
    Otherwise, a new entry will be created.
    """
    try:
        token = decodeJWT(access_token)
        user_id = token["user_id"]

        wellness_metrics = create_daily_wellness_metrics(db=db, user_id=user_id, wellness_data=wellness_data)

        return DailyWellnessResponse.from_orm(wellness_metrics)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create wellness metrics: {str(e)}")


@router.get("/daily-metrics", response_model=DailyWellnessListResponse)
def get_wellness_history(
    limit: int = Query(30, ge=1, le=100, description="Number of entries to retrieve"),
    offset: int = Query(0, ge=0, description="Number of entries to skip"),
    db: Session = Depends(get_db),
    access_token: str = Depends(JWTBearer()),
):
    """
    Get wellness metrics history for the authenticated user.
    Returns entries ordered by date (most recent first).
    """
    try:
        token = decodeJWT(access_token)
        user_id = token["user_id"]

        metrics = get_user_wellness_metrics(db=db, user_id=user_id, limit=limit, offset=offset)

        metrics_response = [DailyWellnessResponse.from_orm(m) for m in metrics]

        return DailyWellnessListResponse(metrics=metrics_response, total_count=len(metrics_response))

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve wellness metrics: {str(e)}")


@router.get("/daily-metrics/date-range", response_model=DailyWellnessListResponse)
def get_wellness_by_date_range(
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    access_token: str = Depends(JWTBearer()),
):
    """
    Get wellness metrics for a specific date range.
    """
    try:
        if start_date > end_date:
            raise HTTPException(status_code=400, detail="Start date must be before or equal to end date")

        token = decodeJWT(access_token)
        user_id = token["user_id"]

        metrics = get_wellness_metrics_by_date_range(db=db, user_id=user_id, start_date=start_date, end_date=end_date)

        metrics_response = [DailyWellnessResponse.from_orm(m) for m in metrics]

        return DailyWellnessListResponse(metrics=metrics_response, total_count=len(metrics_response))

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve wellness metrics: {str(e)}")


@router.get("/daily-metrics/latest", response_model=Optional[DailyWellnessResponse])
def get_latest_wellness(
    db: Session = Depends(get_db),
    access_token: str = Depends(JWTBearer()),
):
    """
    Get the most recent wellness metrics entry for the authenticated user.
    """
    try:
        token = decodeJWT(access_token)
        user_id = token["user_id"]

        latest_metrics = get_latest_wellness_metrics(db=db, user_id=user_id)

        if latest_metrics:
            return DailyWellnessResponse.from_orm(latest_metrics)
        return None

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve latest wellness metrics: {str(e)}")


@router.get("/stats", response_model=WellnessStatsResponse)
def get_wellness_statistics(
    days: int = Query(30, ge=1, le=365, description="Number of days to include in statistics"),
    db: Session = Depends(get_db),
    access_token: str = Depends(JWTBearer()),
):
    """
    Get wellness statistics (averages, trends) for the last N days.
    """
    try:
        token = decodeJWT(access_token)
        user_id = token["user_id"]

        stats = get_wellness_stats(db=db, user_id=user_id, days=days)

        latest_response = None
        if stats["latest_entry"]:
            latest_response = DailyWellnessResponse.from_orm(stats["latest_entry"])

        return WellnessStatsResponse(
            avg_energy_level=stats["avg_energy_level"],
            avg_stress_level=stats["avg_stress_level"],
            total_entries=stats["total_entries"],
            date_range=stats["date_range"],
            latest_entry=latest_response,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve wellness statistics: {str(e)}")


@router.delete("/daily-metrics/{metrics_id}")
def delete_wellness_entry(
    metrics_id: int,
    db: Session = Depends(get_db),
    access_token: str = Depends(JWTBearer()),
):
    """
    Delete a specific wellness metrics entry.
    """
    try:
        token = decodeJWT(access_token)
        user_id = token["user_id"]

        success = delete_wellness_metrics(db=db, user_id=user_id, metrics_id=metrics_id)

        if success:
            return {"message": "Wellness metrics entry deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="Wellness metrics entry not found")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete wellness metrics: {str(e)}")
