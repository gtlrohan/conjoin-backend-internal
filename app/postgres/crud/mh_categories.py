from datetime import timedelta
from typing import Any, Dict, List

from requests import Session
from sqlalchemy.exc import NoResultFound

from app.postgres.models.card import CardType, CategoryEnum
from app.postgres.schema.card import CardDetail, CardMHCategory, MHCategory

# from app.postgres.schema.mh_categories import MHCategory


def create_mh_category(
    db: Session,
    category_name: str,
):
    new_category = MHCategory(
        category_name=category_name,
    )

    db.add(new_category)
    db.commit()
    db.refresh(new_category)

    return new_category


def create_card_detail_from_json(db: Session, data: List[Dict[str, Any]]):
    for item in data:
        # Create a CardDetail object with mapped fields
        card_detail = CardDetail(
            card_type=CardType.suggestion,  # Assuming CardType.REGULAR is a valid card type in your setup
            title=item["activity"],
            category=CategoryEnum[item["category"]],  # Assuming CategoryEnum is properly defined
            details={},  # Store the whole item as JSON if necessary
            description=None,  # Add a description if you have it
            duration=timedelta(minutes=min((item["duration"]))),
            tod=None,  # Set appropriate TimeOfDay if necessary
            special_card_action=None,  # Define if applicable
            affirmation_number=None,  # Set if applicable
        )

        # Add the card detail to the session
        db.add(card_detail)

    db.commit()


def create_card_mh_categories(db: Session, data: List[Dict[str, Any]]):
    for item in data:
        try:
            # Fetch the CardDetail based on activity (title in CardDetail)
            card_detail = db.query(CardDetail).filter(CardDetail.title == item["activity"]).one()

            # Fetch the MHCategory based on cat
            mh_category = db.query(MHCategory).filter(MHCategory.category_name == item["cat"]).one()

            # Convert severity to an integer, handling "4+" as 5
            severity_str = str(item.get("severity", "0"))  # Convert severity to string
            severity = int(severity_str.replace("+", "")) if severity_str.isdigit() else 5

            # Create a new CardMHCategory
            card_mh_category = CardMHCategory(card_detail_id=card_detail.id, category_id=mh_category.id, severity=severity)

            # Add the new CardMHCategory to the session
            db.add(card_mh_category)
        except NoResultFound as e:
            # Handle cases where no matching CardDetail or MHCategory is found
            print(f"No matching CardDetail or MHCategory found for activity '{item['activity']}' or category '{item['cat']}'. Error: {e}")
            continue

    # Commit all additions to the database
    db.commit()
