from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field, validator


class DailyWellnessRequest(BaseModel):
    energy_level: float = Field(..., ge=0.0, le=10.0, description="Energy level from 0.0 (very low) to 10.0 (very high)")
    stress_level: float = Field(..., ge=0.0, le=10.0, description="Stress level from 0.0 (very low) to 10.0 (very high)")

    @validator("energy_level", "stress_level")
    def validate_levels(cls, v):
        if not isinstance(v, (int, float)):
            raise ValueError("Level must be a number")
        if v < 0.0 or v > 10.0:
            raise ValueError("Level must be between 0.0 and 10.0")
        return float(v)


class DailyWellnessResponse(BaseModel):
    id: int
    user_id: int
    energy_level: float
    stress_level: float
    date: date
    created_at: datetime

    class Config:
        from_attributes = True


class DailyWellnessListResponse(BaseModel):
    metrics: list[DailyWellnessResponse]
    total_count: int


class WellnessStatsResponse(BaseModel):
    avg_energy_level: float
    avg_stress_level: float
    total_entries: int
    date_range: str
    latest_entry: Optional[DailyWellnessResponse] = None
