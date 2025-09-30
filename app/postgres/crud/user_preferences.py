from typing import List, Optional

from sqlalchemy.orm import Session

from app.postgres.schema.user_preferences import CategoryEnum, UserPreferences


def create_user_preference(db: Session, user_id: int, preference_name: str, preference_metric: float, category: CategoryEnum):
    try:
        # Create a new UserPreferences instance
        user_preference = UserPreferences(user_id=user_id, preferenceName=preference_name, preferenceMetric=preference_metric, category=category)

        db.add(user_preference)
        db.commit()
        db.refresh(user_preference)

        return user_preference

    except Exception as e:
        db.rollback()  # Rollback the transaction in case of an error
        raise e  # Re-raise the exception for further handling


def retrieve_user_preferences(db: Session, user_id: int, category: Optional[CategoryEnum] = None) -> List[UserPreferences]:
    try:
        # Base query to filter by user_id
        query = db.query(UserPreferences).filter(UserPreferences.user_id == user_id)

        # If category is provided, add it to the query filters
        if category:
            query = query.filter(UserPreferences.category == category)

        return query.all()

    except Exception as e:
        raise e
