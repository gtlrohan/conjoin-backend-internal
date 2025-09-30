import json
from datetime import date, datetime, time, timedelta
from enum import Enum
from typing import List, Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Query
from sqlalchemy.orm import Session

from app.middleware.jwt import JWTBearer, decodeJWT
from app.postgres.crud.card import (
    create_card_details,
    create_completion_details,
    create_user_card,
    delete_card_records_for_user,
    retrieve_affirmation_card,
    retrieve_all_card_details,
    retrieve_card_by_id,
    retrieve_card_details,
    retrieve_cards,
    retrieve_completed_cards,
    retrieve_next_available_slot,
    update_card_time,
)
from app.postgres.crud.cognitive_score import (
    delete_cognitive_score_impacts_for_user,
    update_cognitive_score,
)
from app.postgres.crud.user import update_morning_orientation_status
from app.postgres.database import get_db
from app.postgres.models.card import (
    CategoryEnum,
    CompletionDetails,
    ConfirmReschedule,
    HowWasIt,
    Reschedule,
    SpecialActions,
    ToD,
)
from app.postgres.schema.card import CardType
from app.utils.decision_tree import CardActionsDecisionTree

router = APIRouter(prefix="/cards", tags=["Cards"])


@router.get("/")
def get_cards_between_date_range(
    startDate: datetime = Query(..., example="2024-06-01T00:00:00"),
    endDate: datetime = Query(..., example="2024-06-30T23:59:59"),
    db: Session = Depends(get_db),
    access_token: str = Depends(JWTBearer()),
):
    token = decodeJWT(access_token)
    user_id = token["user_id"]
    cards = retrieve_cards(db, user_id, startDate, endDate)

    for card in cards:
        if hasattr(card.card_details, "tod"):
            card.card_details.tod = str(card.card_details.tod)

    return cards


@router.get("/card-details")
def get_all_card_details(
    db: Session = Depends(get_db),
    access_token: str = Depends(JWTBearer()),
):
    card_details = retrieve_all_card_details(db)

    for card_detail in card_details:
        if hasattr(card_detail, "tod"):
            card_detail.tod = str(card_detail.tod)

    return card_details


@router.get("/affirmation-card")
def get_affirmation_card(
    affirmation_number: int = Query(..., example=1),
    db: Session = Depends(get_db),
    access_token: str = Depends(JWTBearer()),
):
    token = decodeJWT(access_token)
    token["user_id"]
    affirmation_card_details = retrieve_affirmation_card(db, affirmation_number)

    if hasattr(affirmation_card_details, "tod"):
        affirmation_card_details.tod = str(affirmation_card_details.tod)

    if hasattr(affirmation_card_details, "duration"):
        affirmation_card_details.duration = str(affirmation_card_details.duration)

    return affirmation_card_details


@router.post("/create-user-card")
def creates_a_user_card(
    card_details_id: int = Form(...),
    time: datetime = Form(..., example="2024-06-14T00:00:00"),
    recurrence: Optional[List[str]] = Form(None, example="RRULE:FREQ=WEEKLY;BYDAY=TU"),
    location: Optional[str] = Form(None, example="1234 Street, London, SW6 3XJ"),
    find_time: Optional[bool] = Form(..., example=True),
    db: Session = Depends(get_db),
    access_token: str = Depends(JWTBearer()),
):
    token = decodeJWT(access_token)
    user_id = token["user_id"]

    if find_time:
        card_details = retrieve_card_details(db, card_details_id)
        # Add 10 minutes to the local time
        local_time = time + timedelta(minutes=10)

        time = retrieve_next_available_slot(db=db, user_id=user_id, card_details=card_details, start_time=local_time)

    card = create_user_card(
        db=db,
        user_id=user_id,
        card_details_id=card_details_id,
        card={
            "time": time,
            "recurrence": recurrence,
            "location": location,
        },
    )

    if find_time:
        if hasattr(card_details, "tod"):
            card_details.tod = str(card_details.tod)
        if isinstance(card_details.duration, str):
            hours, minutes, seconds = map(int, card_details.duration.split(":"))
            duration_in_minutes = hours * 60 + minutes + seconds / 60
            card_details.duration = duration_in_minutes
        card.card_details = card_details

    print(card.card_details)

    return card


@router.post("/create-card-details")
def creates_card_details(
    card_type: CardType = Form(...),
    title: str = Form(..., example="Have a nutritional breakfast"),
    category: CategoryEnum = Form(..., example="Nutrition"),
    details: str = Form(
        ...,
        example='{"ingredients": "Cooked quinoa, almond milk, fresh berries, sliced almonds, and a sprinkle of cinnamon.", "preparation": "High in protein and fiber, gluten-free, and a good source of essential amino acids."}',
    ),
    # objective_id: int = Form(..., example=1),
    description: Optional[str] = Form(None, example="Have a bowl of Muesli with some fruit for breakfast"),
    duration: timedelta = Form(..., example="00:30:00"),
    tod: ToD = Form(..., example="ANY"),
    special_card_action: SpecialActions = Form(..., example="AFFIRMATION"),
    db: Session = Depends(get_db),
    access_token: str = Depends(JWTBearer()),
):
    details_dict = json.loads(details)
    token = decodeJWT(access_token)
    token["user_id"]
    card = create_card_details(
        db=db,
        card_type=card_type,
        title=title,
        category=category,
        details=details_dict,
        # objective_id=objective_id,
        description=description,
        duration=duration,
        tod=tod,
        special_card_action=special_card_action,
    )
    return repr(card)


@router.post("/completion-details")
def updates_the_cards_completion_details(
    details: CompletionDetails,
    db: Session = Depends(get_db),
    access_token: str = Depends(JWTBearer()),
):
    token = decodeJWT(access_token)
    user_id = token["user_id"]
    create_completion_details(db=db, user_id=user_id, completion_details=details)
    card = retrieve_card_by_id(db, user_id, details.card_id)
    if card.card_details_id == 77 and (details.how_was_it == HowWasIt.terrible or details.how_was_it == HowWasIt.bad):
        card_data = {
            "card_details_id": 49,
            "time": datetime.combine(details.time, time(17, 00)),
            "recurrence": None,
            "location": None,
        }
        create_user_card(db=db, user_id=user_id, card=card_data, card_details_id=49)
        return {"message": "add_message", "card_details_id": 77}

    # if card.card_details.category == CategoryEnum.Nutrition and details.completion_level == CompletionLevel.incomplete:


@router.get("/retrieve-completion-details")
def retrieves_card_completion_details_in_range(
    startDate: datetime = Query(..., example="2024-06-01T00:00:00"),
    endDate: datetime = Query(..., example="2024-06-30T23:59:59"),
    db: Session = Depends(get_db),
    access_token: str = Depends(JWTBearer()),
):
    token = decodeJWT(access_token)
    user_id = token["user_id"]
    completed_cards = retrieve_completed_cards(db, user_id, startDate, endDate)
    return completed_cards


@router.post("/reschedule")
def reschedule_card(request: Reschedule, db: Session = Depends(get_db), access_token: str = Depends(JWTBearer())):
    token = decodeJWT(access_token)
    user_id = token["user_id"]

    card = retrieve_card_by_id(
        db=db,
        user_id=user_id,
        card_id=request.card_id,
    )

    local_time = request.current_time

    # Add 10 minutes to the local time
    local_time = local_time + timedelta(minutes=10)

    new_time = retrieve_next_available_slot(db=db, user_id=user_id, card_details=card.card_details, start_time=local_time)

    if new_time is None:
        return {"message": "I couldn't find an available slot for rescheduling"}

    return {"message": "success", "new_time": new_time}


@router.post("/confirm-reschedule")
def reschedule_card(request: ConfirmReschedule, db: Session = Depends(get_db), access_token: str = Depends(JWTBearer())):
    token = decodeJWT(access_token)
    user_id = token["user_id"]

    card = retrieve_card_by_id(
        db=db,
        user_id=user_id,
        card_id=request.card_id,
    )

    new_time = datetime.strptime(request.new_time, "%Y-%m-%d %H:%M:%S")

    # Update and commit the card's new time
    update_card_time(db=db, card=card, new_time=new_time)

    return {"message": "success"}


class TriggerEnum(str, Enum):
    completed = "completed"
    missed = "missed"
    user_cancelled = "user_cancelled"
    participant_cancelled = "participant_cancelled"


@router.post("/trigger")
def trigger_card(
    trigger: TriggerEnum = Query([]),
    db: Session = Depends(get_db),
    access_token: str = Depends(JWTBearer()),
):
    # Example usage
    user_probabilities = {
        "free_time_yes": 0.7,
        "free_time_no": 0.3,
        "reschedule_immediately_yes": 0.6,
        "reschedule_immediately_no": 0.4,
        "reschedule_by_mentor_yes": 0.5,
        "reschedule_by_mentor_no": 0.5,
        "reschedule_by_user_yes": 0.8,
        "reschedule_by_user_no": 0.2,
    }

    decision_tree = CardActionsDecisionTree(user_probabilities)
    decision_tree.process(trigger.value)


@router.get("/create/test-data")
def add_companion_card_test_data_for_today(db: Session = Depends(get_db), access_token: str = Depends(JWTBearer())):
    token = decodeJWT(access_token)
    user_id = token["user_id"]

    # call crud function that deletes all CognitiveScoreImpact records for a specific user
    delete_cognitive_score_impacts_for_user(db, user_id)

    # call crud function that deletes all CardCompletionDetail records for a specific user
    # call crud function that deletes all UserCard records for a specific user
    delete_card_records_for_user(db, user_id)

    # reset cognitive score back to 5 (or default)
    update_cognitive_score(db, user_id, 5)

    # set user morning orientiation to uncompleted
    update_morning_orientation_status(db, user_id, False)

    # Get today's date
    # todays_date = datetime.now().date()
    todays_date = date(2025, 1, 17)
    test_data = [
        {
            "card_details_id": 1,
            "time": datetime.combine(todays_date, time(8, 00)),
            "recurrence": None,
            "location": None,
        },
        {
            "card_details_id": 75,
            "time": datetime.combine(todays_date, time(11, 00)),
            "recurrence": None,
            "location": None,
        },
        {
            "card_details_id": 76,
            "time": datetime.combine(todays_date, time(13, 00)),
            "recurrence": None,
            "location": None,
        },
        {
            "card_details_id": 77,
            "time": datetime.combine(todays_date, time(16, 00)),
            "recurrence": None,
            "location": None,
        },
        {
            "card_details_id": 80,
            "time": datetime.combine(todays_date, time(18, 00)),
            "recurrence": None,
            "location": None,
        },
        {
            "card_details_id": 79,
            "time": datetime.combine(todays_date, time(20, 00)),
            "recurrence": None,
            "location": "Bluebird Restaurant, Chelsea, London",
        },
    ]

    for card_data in test_data:
        try:
            create_user_card(db=db, user_id=user_id, card=card_data, card_details_id=card_data["card_details_id"])
        except Exception as e:
            # Handle any exceptions that may occur during the creation of cards
            raise HTTPException(status_code=500, detail=f"Failed to create card: {str(e)}") from None

    return "Successfully created companion card test data"
