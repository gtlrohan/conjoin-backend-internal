from datetime import datetime
from typing import Dict, List

from sqlalchemy.orm import Session

from app.postgres.schema.fitbit_heart import (
    FitbitCustomHeartRateZone,
    FitbitHeartLog,
    FitbitHeartRateZone,
)


def create_heart_log(heart_logs: Dict[str, List[Dict]], user_id: str, db: Session):
    heart_log_objects = []
    for heart_log in heart_logs["activities-heart"]:
        date_time = datetime.strptime(heart_log["dateTime"], "%Y-%m-%d")

        heart_rate_zones = []
        for zone in heart_log["value"]["heartRateZones"]:
            heart_rate_zones.append(
                FitbitHeartRateZone(name=zone["name"], min=zone["min"], max=zone["max"], minutes=zone["minutes"], calories_out=zone["caloriesOut"])
            )

        custom_heart_rate_zones = []
        for custom_zone in heart_log["value"]["customHeartRateZones"]:
            custom_heart_rate_zones.append(
                FitbitCustomHeartRateZone(
                    name=custom_zone["name"],
                    min=custom_zone["min"],
                    max=custom_zone["max"],
                    minutes=custom_zone["minutes"],
                    calories_out=custom_zone["caloriesOut"],
                )
            )

        heart_log_objects.append(
            FitbitHeartLog(
                user_id=user_id,
                date_time=date_time,
                resting_heart_rate=heart_log["value"].get("restingHeartRate"),
                heart_rate_zones=heart_rate_zones,
                custom_heart_rate_zones=custom_heart_rate_zones,
            )
        )

    # Add all the heart log objects to the session at once
    db.add_all(heart_log_objects)
    db.commit()
