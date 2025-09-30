from datetime import date, datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.postgres.schema.wellness import DailyWellnessMetrics
from app.postgres.models.wellness import DailyWellnessRequest


def create_daily_wellness_metrics(
    db: Session, user_id: int, wellness_data: DailyWellnessRequest
) -> DailyWellnessMetrics:
    """
    Create or update daily wellness metrics for a user.
    If entry already exists for today, update it; otherwise create new entry.
    """
    today = date.today()
    
    # Check if entry already exists for today
    existing_entry = db.query(DailyWellnessMetrics).filter(
        DailyWellnessMetrics.user_id == user_id,
        DailyWellnessMetrics.date == today
    ).first()
    
    if existing_entry:
        # Update existing entry
        existing_entry.energy_level = wellness_data.energy_level
        existing_entry.stress_level = wellness_data.stress_level
        existing_entry.created_at = datetime.utcnow()  # Update timestamp
        db.commit()
        db.refresh(existing_entry)
        return existing_entry
    else:
        # Create new entry
        db_wellness = DailyWellnessMetrics(
            user_id=user_id,
            energy_level=wellness_data.energy_level,
            stress_level=wellness_data.stress_level,
            date=today
        )
        db.add(db_wellness)
        db.commit()
        db.refresh(db_wellness)
        return db_wellness


def get_user_wellness_metrics(
    db: Session, 
    user_id: int, 
    limit: int = 30, 
    offset: int = 0
) -> List[DailyWellnessMetrics]:
    """
    Retrieve wellness metrics for a user, ordered by date (most recent first).
    """
    return db.query(DailyWellnessMetrics).filter(
        DailyWellnessMetrics.user_id == user_id
    ).order_by(desc(DailyWellnessMetrics.date)).offset(offset).limit(limit).all()


def get_wellness_metrics_by_date_range(
    db: Session, 
    user_id: int, 
    start_date: date, 
    end_date: date
) -> List[DailyWellnessMetrics]:
    """
    Retrieve wellness metrics for a user within a specific date range.
    """
    return db.query(DailyWellnessMetrics).filter(
        DailyWellnessMetrics.user_id == user_id,
        DailyWellnessMetrics.date >= start_date,
        DailyWellnessMetrics.date <= end_date
    ).order_by(desc(DailyWellnessMetrics.date)).all()


def get_latest_wellness_metrics(db: Session, user_id: int) -> Optional[DailyWellnessMetrics]:
    """
    Get the most recent wellness metrics entry for a user.
    """
    return db.query(DailyWellnessMetrics).filter(
        DailyWellnessMetrics.user_id == user_id
    ).order_by(desc(DailyWellnessMetrics.date)).first()


def get_wellness_stats(db: Session, user_id: int, days: int = 30) -> dict:
    """
    Calculate average energy and stress levels for the last N days.
    """
    start_date = date.today() - timedelta(days=days)
    
    metrics = db.query(DailyWellnessMetrics).filter(
        DailyWellnessMetrics.user_id == user_id,
        DailyWellnessMetrics.date >= start_date
    ).all()
    
    if not metrics:
        return {
            "avg_energy_level": 0.0,
            "avg_stress_level": 0.0,
            "total_entries": 0,
            "date_range": f"{start_date} to {date.today()}",
            "latest_entry": None
        }
    
    avg_energy = sum(m.energy_level for m in metrics) / len(metrics)
    avg_stress = sum(m.stress_level for m in metrics) / len(metrics)
    latest_entry = max(metrics, key=lambda x: x.date)
    
    return {
        "avg_energy_level": round(avg_energy, 2),
        "avg_stress_level": round(avg_stress, 2),
        "total_entries": len(metrics),
        "date_range": f"{start_date} to {date.today()}",
        "latest_entry": latest_entry
    }


def delete_wellness_metrics(db: Session, user_id: int, metrics_id: int) -> bool:
    """
    Delete a specific wellness metrics entry.
    """
    wellness_entry = db.query(DailyWellnessMetrics).filter(
        DailyWellnessMetrics.id == metrics_id,
        DailyWellnessMetrics.user_id == user_id
    ).first()
    
    if wellness_entry:
        db.delete(wellness_entry)
        db.commit()
        return True
    return False
