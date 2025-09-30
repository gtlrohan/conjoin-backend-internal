from datetime import datetime
from typing import Dict, List

from sqlalchemy.orm import Session, joinedload

from app.postgres.schema.fitbit_sleep import (
    FitbitSleepLevel,
    FitbitSleepLog,
    FitbitSleepSummary,
)


def create_sleep_log(sleep_logs: Dict[str, List[Dict]], user_id: str, db: Session):
    sleep_log_objects = []
    for sleep_log in sleep_logs["sleep"]:
        levels = []
        for level in sleep_log["levels"]["data"]:
            levels.append(FitbitSleepLevel(log_id=sleep_log["logId"], date_time=level["dateTime"], level=level["level"], seconds=level["seconds"]))

        sleep_summaries = []
        for sleep_type, sleep_data in sleep_log["levels"]["summary"].items():
            sleep_summaries.append(
                FitbitSleepSummary(log_id=sleep_log["logId"], level_type=sleep_type, count=sleep_data["count"], minutes=sleep_data["minutes"])
            )

        sleep_log_objects.append(
            FitbitSleepLog(
                log_id=sleep_log["logId"],
                user_id=user_id,
                date_of_sleep=sleep_log["dateOfSleep"],
                duration=sleep_log["duration"],
                efficiency=sleep_log["efficiency"],
                end_time=sleep_log["endTime"],
                info_code=sleep_log["infoCode"],
                is_main_sleep=sleep_log["isMainSleep"],
                minutes_after_wakeup=sleep_log["minutesAfterWakeup"],
                minutes_asleep=sleep_log["minutesAsleep"],
                minutes_awake=sleep_log["minutesAwake"],
                minutes_to_fall_asleep=sleep_log["minutesToFallAsleep"],
                start_time=sleep_log["startTime"],
                time_in_bed=sleep_log["timeInBed"],
                log_type=sleep_log["logType"],
                sleep_type=sleep_log["type"],
                sleep_levels=levels,
                sleep_summaries=sleep_summaries,
            )
        )

    # Add all the sleep log objects to the session at once
    db.add_all(sleep_log_objects)
    db.commit()


def retrieve_users_last_sleep(user_id: str, db: Session):
    # Query to find the most recent sleep log for the given user_id
    last_sleep_log = db.query(FitbitSleepLog).filter(FitbitSleepLog.user_id == user_id).order_by(FitbitSleepLog.date_of_sleep.desc()).first()
    return last_sleep_log


def retrieve_users_sleep_by_date(user_id: str, date: datetime, db: Session):
    # Query to find the sleep logs for the given user_id and date_of_sleep,
    # including the related sleep levels and summaries
    sleep_logs = (
        db.query(FitbitSleepLog)
        .filter(FitbitSleepLog.user_id == user_id, FitbitSleepLog.date_of_sleep == date)
        .options(joinedload(FitbitSleepLog.sleep_levels), joinedload(FitbitSleepLog.sleep_summaries))
        .all()
    )
    return sleep_logs


def retrieve_users_sleep_by_date_range(user_id: str, start_date: datetime, end_date: datetime, db: Session):
    # Query to find the sleep logs for the given user_id and within the date range,
    # including the related sleep levels and summaries
    sleep_logs = (
        db.query(FitbitSleepLog)
        .filter(FitbitSleepLog.user_id == user_id, FitbitSleepLog.date_of_sleep >= start_date, FitbitSleepLog.date_of_sleep <= end_date)
        .options(joinedload(FitbitSleepLog.sleep_levels), joinedload(FitbitSleepLog.sleep_summaries))
        .all()
    )
    return sleep_logs
