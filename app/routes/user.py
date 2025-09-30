from datetime import date, datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.middleware.jwt import JWTBearer, decodeJWT
from app.postgres.crud.card import (
    create_user_cards_from_list,
    delete_card_records_for_user,
    retrieve_cards,
    retrieve_completed_cards_with_score,
)
from app.postgres.crud.cognitive_fingerprint import (
    retrieve_cognitive_fingerprint,
    update_cognitive_fingerprint,
)
from app.postgres.crud.cognitive_score import (
    delete_cognitive_score_impacts_for_user,
    retrieve_cognitive_score,
    update_cognitive_score,
)
from app.postgres.crud.goal import retrieve_all_user_goals
from app.postgres.crud.user import (
    retrieve_user_by_id,
    update_morning_orientation_status,
)
from app.postgres.crud.user_preferences import (
    create_user_preference,
    retrieve_user_preferences,
)
from app.postgres.database import get_db
from app.postgres.models.card import CardData, CognitiveFingerprintUpdate
from app.postgres.models.user import (
    MorningOrientationAltTimeRequest,
    MorningOrientationRequest,
)
from app.postgres.schema.card import CardDetail, UserCard
from app.postgres.schema.user_preferences import CategoryEnum
from app.services.digital_mentor.cfp import CognitiveFingerprint
from app.services.digital_mentor.mentor import Mentor
from app.services.digital_mentor.user import User

router = APIRouter(prefix="/user", tags=["User"])


@router.get("/")
async def gets_user_details(
    db: Session = Depends(get_db),
    access_token: str = Depends(JWTBearer()),
):
    token = decodeJWT(access_token)
    user_id = token["user_id"]
    user = retrieve_user_by_id(db=db, user_id=user_id)

    # Check if user exists
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    if user.completed_morning_orientation is None:
        user.completed_morning_orientation = False
    cfp = await retrieve_cognitive_fingerprint(db, user_id)
    cfp = {
        "work_anxiety": cfp.work_anxiety,
        "social_anxiety": cfp.social_anxiety,
        "family_anxiety": cfp.family_anxiety,
        "eating_anxiety": cfp.eating_anxiety,
        "sleeping_anxiety": cfp.sleeping_anxiety,
    }
    return {"user": user, "cfp": cfp}


@router.get("/preferences")
def get_user_preferences(
    category: Optional[CategoryEnum] = Query(None, description="Filter by category (Optional)"),
    db: Session = Depends(get_db),
    access_token: str = Depends(JWTBearer()),
):
    token = decodeJWT(access_token)
    user_id = token["user_id"]
    user_preferences = retrieve_user_preferences(db=db, user_id=user_id, category=category)
    return user_preferences


@router.get("/preferences/category-filtered")
def get_user_preferences_filtered_by_category(
    category: CategoryEnum = Query(..., description="Filter by category"),
    db: Session = Depends(get_db),
    access_token: str = Depends(JWTBearer()),
):
    token = decodeJWT(access_token)
    user_id = token["user_id"]
    user_preferences = retrieve_user_preferences(db=db, user_id=user_id, category=category)
    return user_preferences


@router.post("/preferences/create")
def add_user_preference(
    preference_name: str = Query(..., example="Protein snack", description="Name of preference"),
    preference_metric: float = Query(..., example=0.8, description="How strong the user's preference is (between 0 and 1)", gt=0, le=1),
    category: CategoryEnum = Query(..., description="Filter by category"),
    db: Session = Depends(get_db),
    access_token: str = Depends(JWTBearer()),
):
    token = decodeJWT(access_token)
    user_id = token["user_id"]
    user_preference = create_user_preference(
        db=db, user_id=user_id, preference_name=preference_name, preference_metric=preference_metric, category=category
    )
    return user_preference


@router.post("/morning-orientation")
async def gives_morning_orientation_suggestions(
    request: MorningOrientationRequest,
    db: Session = Depends(get_db),
    access_token: str = Depends(JWTBearer()),
):
    time = request.time
    token = decodeJWT(access_token)
    user_id = token["user_id"]

    preferences = retrieve_user_preferences(db, user_id)
    goals = retrieve_all_user_goals(db, user_id)
    cfp = await retrieve_cognitive_fingerprint(db, user_id)
    cfp = CognitiveFingerprint(
        work_anxiety=cfp.work_anxiety,
        social_anxiety=cfp.social_anxiety,
        family_anxiety=cfp.family_anxiety,
        eating_anxiety=cfp.eating_anxiety,
        sleeping_anxiety=cfp.sleeping_anxiety,
    )
    cognitive_score = retrieve_cognitive_score(db, user_id)
    history = retrieve_completed_cards_with_score(db, user_id, time - timedelta(days=7), time)
    plan = retrieve_cards(
        db=db,
        user_id=user_id,
        start_date=datetime.combine(time.date(), datetime.min.time()),
        end_date=datetime.combine(time.date(), datetime.max.time()),
        load_card_details=True,
    )

    # Initialise User with preferences, goals, cfp, cog score, history, plan, calendar
    user = User(
        user_id=user_id,
        preferences=preferences,
        goals=goals,
        cognitive_fingerprint=cfp,
        cognitive_score=cognitive_score,  # How is cognitive score different from cognitive fingerprint
        history=history,
        plan=plan,
    )

    for card in user.plan:
        if hasattr(card.card_details, "tod"):
            card.card_details.tod = str(card.card_details.tod)

    suggested = Mentor().morning_orientation(db, user, fake_time=time)

    user.plan += suggested
    user.plan.sort(key=lambda x: x["time"] if isinstance(x, dict) else x.time)

    # Convert tod to string for each card in suggested
    for card in suggested:
        if isinstance(card["card_details"], dict) and "tod" in card["card_details"]:
            card["card_details"]["tod"] = str(card["card_details"]["tod"])
        elif hasattr(card["card_details"], "tod"):
            card["card_details"].tod = str(card["card_details"].tod)

    return suggested


@router.post("/add-morning-orientation-suggestions")
def adds_morning_orientation_suggestions_to_users_plan(
    cards: List[CardData],
    db: Session = Depends(get_db),
    access_token: str = Depends(JWTBearer()),
):
    token = decodeJWT(access_token)
    user_id = token["user_id"]
    create_user_cards_from_list(db, user_id, cards)
    update_morning_orientation_status(db, user_id, True)


def convert_card_data_to_user_card(card_data: CardData) -> UserCard:
    duration = card_data.card_details.duration
    if not isinstance(duration, timedelta):
        duration = timedelta(seconds=float(duration))
    card_details_sqlalchemy = CardDetail(
        id=card_data.card_details.id,
        card_type=card_data.card_details.card_type,
        title=card_data.card_details.title,
        category=card_data.card_details.category,
        details=card_data.card_details.details,
        description=card_data.card_details.description,
        duration=duration,
        special_card_action=card_data.card_details.special_card_action,
        affirmation_number=card_data.card_details.affirmation_number,
    )

    # Convert CardData to UserCard
    user_card = UserCard(
        card_id=card_data.card_id,
        time=card_data.time,
        created_at=card_data.created_at,
        user_id=card_data.user_id,
        location=card_data.location,
        recurrence=card_data.recurrence,
        calendar_event_id=card_data.calendar_event_id,
        card_details=card_details_sqlalchemy,  # Assuming card_details is the correct relationship
        # You can also omit fields not set by default, assuming they're optional in the database model
    )

    return user_card


@router.post("/morning-orientation-suggestion-alternative-times")
async def retrieves_allternative_times_to_change_a_MO_suggestion_to(
    body: MorningOrientationAltTimeRequest,
    db: Session = Depends(get_db),
    access_token: str = Depends(JWTBearer()),
):
    token = decodeJWT(access_token)
    user_id = token["user_id"]
    time = body.current_time

    # retrieve current user plan
    plan = retrieve_cards(db=db, user_id=user_id, start_date=time, end_date=datetime.combine(time, datetime.max.time()), load_card_details=True)

    converted_cards = [convert_card_data_to_user_card(card_data) for card_data in body.cards]

    combined_cards = plan + converted_cards

    # Sort the combined list by the time attribute
    combined_cards.sort(key=lambda x: x.time)
    cfp = await retrieve_cognitive_fingerprint(db, user_id)
    cfp = CognitiveFingerprint(
        work_anxiety=cfp.work_anxiety,
        social_anxiety=cfp.social_anxiety,
        family_anxiety=cfp.family_anxiety,
        eating_anxiety=cfp.eating_anxiety,
        sleeping_anxiety=cfp.sleeping_anxiety,
    )

    cognitive_score = retrieve_cognitive_score(db, user_id)

    user = User(
        user_id=user_id,
        preferences=[],
        goals=[],
        cognitive_fingerprint=cfp,
        cognitive_score=cognitive_score,  # How is cognitive score different from cognitive fingerprint
        history=[],
        plan=combined_cards,
    )

    start_time = time.replace(hour=8, minute=30, second=0, microsecond=0)
    start_of_day = max(time, start_time)

    available_times = user.get_available_times(start_of_day=start_of_day, end_of_day=time.replace(hour=23, minute=0, second=0, microsecond=0))
    print(available_times)

    return available_times


@router.post("/morning-orientation-suggestion-alternative-activities")
async def retrieves_allternative_times_to_change_a_MO_suggestion_to(
    card: CardData,
    db: Session = Depends(get_db),
    access_token: str = Depends(JWTBearer()),
):
    token = decodeJWT(access_token)
    user_id = token["user_id"]

    preferences = retrieve_user_preferences(db, user_id)
    goals = retrieve_all_user_goals(db, user_id)
    cfp = await retrieve_cognitive_fingerprint(db, user_id)
    cfp = CognitiveFingerprint(
        work_anxiety=cfp.work_anxiety,
        social_anxiety=cfp.social_anxiety,
        family_anxiety=cfp.family_anxiety,
        eating_anxiety=cfp.eating_anxiety,
        sleeping_anxiety=cfp.sleeping_anxiety,
    )
    cognitive_score = retrieve_cognitive_score(db, user_id)
    history = retrieve_completed_cards_with_score(db, user_id, datetime.now() - timedelta(days=7), datetime.now())
    plan = retrieve_cards(
        db=db,
        user_id=user_id,
        start_date=datetime.combine(date.today(), datetime.min.time()),
        end_date=datetime.combine(date.today(), datetime.max.time()),
        load_card_details=True,
    )

    # Initialise User with preferences, goals, cfp, cog score, history, plan, calendar
    user = User(
        user_id=user_id,
        preferences=preferences,
        goals=goals,
        cognitive_fingerprint=cfp,
        cognitive_score=cognitive_score,  # How is cognitive score different from cognitive fingerprint
        history=history,
        plan=plan,
    )

    for card in user.plan:
        if hasattr(card.card_details, "tod"):
            card.card_details.tod = str(card.card_details.tod)

    userCard = convert_card_data_to_user_card(card)
    suggestions = Mentor().suggest_alternatives(db, user, userCard)

    # Convert tod to string for each card in suggested
    for card in suggestions:
        if isinstance(card["card_details"], dict) and "tod" in card["card_details"]:
            card["card_details"]["tod"] = str(card["card_details"]["tod"])
        elif hasattr(card["card_details"], "tod"):
            card["card_details"].tod = str(card["card_details"].tod)

    return suggestions


@router.get("/reset-user-for-demo")
def resets_a_user_back_to_default_demo_settings(
    db: Session = Depends(get_db),
    access_token: str = Depends(JWTBearer()),
):
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


@router.get("/cognitive-fingerprint")
async def get_cognitive_fingerprint(
    db: Session = Depends(get_db),
    access_token: str = Depends(JWTBearer()),
):
    token = decodeJWT(access_token)
    user_id = token["user_id"]

    cfp = await retrieve_cognitive_fingerprint(db, user_id)
    res = {
        "work_anxiety": cfp.work_anxiety,
        "social_anxiety": cfp.social_anxiety,
        "family_anxiety": cfp.family_anxiety,
        "eating_anxiety": cfp.eating_anxiety,
        "sleeping_anxiety": cfp.sleeping_anxiety,
    }

    return res


@router.post("/cognitive-fingerprint/update")
async def update_cognitive_fingerprint_value(
    body: CognitiveFingerprintUpdate,
    db: Session = Depends(get_db),
    access_token: str = Depends(JWTBearer()),
):
    token = decodeJWT(access_token)
    user_id = token["user_id"]

    try:
        updated_cfp = await update_cognitive_fingerprint(db, user_id, **{body.type: body.value * 10})
        return {
            "work_anxiety": updated_cfp.work_anxiety,
            "social_anxiety": updated_cfp.social_anxiety,
            "family_anxiety": updated_cfp.family_anxiety,
            "eating_anxiety": updated_cfp.eating_anxiety,
            "sleeping_anxiety": updated_cfp.sleeping_anxiety,
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
