import copy
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any
from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from dateutil.rrule import rrulestr
from sqlalchemy.orm import Session, joinedload, aliased, contains_eager
from sqlalchemy import and_, or_, select
from sqlalchemy.sql import func

from app.postgres.crud.user import retrieve_user_by_id
from app.postgres.models.card import CardData, CompletionDetails, CardStatus, SpecialActions, ToD
from app.postgres.schema.card import CardMHCategory, MHCategory, UserCard, CardCompletionDetail, CardDetail
from app.postgres.schema.cognitive_score import CognitiveScore, CognitiveScoreImpact
from app.postgres.schema.objective import Objective
from app.postgres.schema.google_calendar import CalendarEvent
from app.utils.cognitive_score_utils import calculate_score_impact


def create_user_card(db: Session, user_id: int, card_details_id: int, card: Dict[str, Any]):
    # Check a user exists before assigning a card to them
    user = retrieve_user_by_id(db, user_id)
    if not user:
        return None

    card_details = db.query(CardDetail).filter(CardDetail.id == card_details_id).first()
    if not card_details:
        return None

    new_card = UserCard(
        card_details_id=card_details_id,
        time=card["time"],
        user_id=user_id,  # Associate the card with the user
        recurrence=card["recurrence"],
        location=card["location"],
    )

    db.add(new_card)
    db.commit()
    db.refresh(new_card)

    return new_card


def create_user_cards_from_list(db: Session, user_id: int, cards: List[CardData]):
    # Check if user exists
    user = retrieve_user_by_id(db, user_id)
    if not user:
        return None

    new_cards = []

    # Process each card
    for card in cards:
        # Lookup card details in db
        card_details = db.query(CardDetail).filter(CardDetail.id == card.card_details.id).first()

        # Skip this card if card details don't exist
        if not card_details:
            print(f"Card details with id {card.card_details.id} not found")
            continue

        # Create new UserCard instance
        new_card = UserCard(
            card_details_id=card.card_details.id,
            time=card.time,
            user_id=user_id,
            recurrence=card.recurrence,
            location=card.location,
        )
        new_cards.append(new_card)

    # If we have valid cards to add
    if new_cards:
        # Add all new cards at once
        db.add_all(new_cards)
        db.commit()

        # Refresh all new cards to get their generated IDs
        for card in new_cards:
            db.refresh(card)

    return new_cards


def create_card_details(
    db: Session,
    card_type: str,
    title: str,
    category: str,
    details: Dict[str, Any],
    # objective_id: int,
    description: str,
    duration: timedelta,
    tod: ToD,
    special_card_action: SpecialActions,
):
    new_card_detail = CardDetail(
        card_type=card_type,
        title=title,
        category=category,
        details=details,
        # objective_id=objective_id,
        description=description,
        duration=duration,
        tod=tod,
        special_card_action=special_card_action,
    )

    db.add(new_card_detail)
    db.commit()
    db.refresh(new_card_detail)

    return new_card_detail


def create_user_cards_from_events(events: List[CalendarEvent], user_id: int, db: Session):
    for event in events:
        # Create Card object for each calendar event
        card = UserCard(
            user_id=user_id,
            card_type="calendar",
            title=event.summary,
            time=event.start.dateTime if event.start else None,
            category=[],
            created_at=datetime.utcnow(),
            recurrence=event.recurrence,
            calendar_event_id=event.id,
        )
        # Add UserCard object to session
        db.add(card)

    # Commit the transaction
    db.commit()


def create_completion_details(db: Session, user_id: int, completion_details: CompletionDetails):
    try:
        # Start of a new transaction
        # Create new CardCompletionDetail
        new_completion_details = CardCompletionDetail(
            card_id=completion_details.card_id,
            status=completion_details.status,
            completion_level=completion_details.completion_level,
            how_was_it=completion_details.how_was_it,
            reason=completion_details.reason,
            created_at=completion_details.time,
            is_positive=completion_details.is_positive,
        )
        db.add(new_completion_details)
        db.commit()
        db.refresh(new_completion_details)

        # Calculate initial score impact
        initial_impact_value = Decimal(calculate_score_impact(completion_details.how_was_it, completion_details.completion_level))

        # Find the user's cognitive score
        cognitive_score = db.query(CognitiveScore).filter(CognitiveScore.user_id == user_id).first()
        if not cognitive_score:
            # If no cognitive score exists, create a new one
            new_score = min(max(initial_impact_value, Decimal(0)), Decimal(10))
            cognitive_score = CognitiveScore(user_id=user_id, score=new_score)
            db.add(cognitive_score)
            actual_impact_value = new_score
        else:
            # Calculate the actual impact value
            old_score = cognitive_score.score
            new_score = min(max(old_score + initial_impact_value, Decimal(0)), Decimal(10))
            actual_impact_value = new_score - old_score
            cognitive_score.score = new_score

        db.commit()

        # Create CognitiveScoreImpact
        score_impact = CognitiveScoreImpact(
            cognitive_score_id=cognitive_score.id,
            card_completion_id=new_completion_details.id,
            value=actual_impact_value,
            new_cognitive_score=cognitive_score.score,
        )
        db.add(score_impact)
        db.commit()

        return new_completion_details

    except Exception as e:
        db.rollback()
        raise e


def retrieve_card_by_id(db: Session, user_id: int, card_id: int):
    card = db.query(UserCard).options(joinedload(UserCard.card_details)).filter(UserCard.card_id == card_id, UserCard.user_id == user_id).first()

    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    return card


def retrieve_cards(db: Session, user_id: int, start_date: datetime, end_date: datetime, load_card_details: bool = True) -> List[UserCard]:
    today_start = datetime.combine(start_date.date(), datetime.min.time())
    today_end = datetime.combine(end_date.date(), datetime.min.time()) + timedelta(days=1)

    # Subquery to find cards with completion details for today
    subquery = (
        select(CardCompletionDetail.card_id)
        .filter(and_(CardCompletionDetail.created_at >= today_start, CardCompletionDetail.created_at < today_end))
        .scalar_subquery()
    )

    query_options = []
    if load_card_details:
        query_options.append(joinedload(UserCard.card_details))

    # Retrieve cards within the date range for the given user that do not have a completion entry for today
    cards = (
        db.query(UserCard)
        .options(*query_options)
        .filter(
            UserCard.user_id == user_id,
            or_(UserCard.time.between(start_date, end_date), UserCard.recurrence.isnot(None)),
            UserCard.card_id.notin_(subquery),
        )
        .all()
    )

    result = []

    for card in cards:
        if card.recurrence:
            rule = rrulestr(card.recurrence[0], dtstart=card.time)
            recurring_dates = list(rule.between(start_date, end_date, inc=True))
            for rec_date in recurring_dates:
                rec_card = UserCard(
                    card_id=card.card_id,
                    card_details_id=card.card_details_id,
                    time=rec_date,
                    created_at=card.created_at,
                    user_id=card.user_id,
                    recurrence=card.recurrence,
                    calendar_event_id=card.calendar_event_id,
                    location=card.location,
                )
                rec_card.card_details = copy.deepcopy(card.card_details)  # Or a suitable copy method if deepcopy is too heavy
                result.append(rec_card)
        elif start_date <= card.time <= end_date:
            result.append(card)

    # Sort the result by time
    result.sort(key=lambda x: x.time)

    return result


def retrieve_all_card_details(db: Session) -> List[CardDetail]:
    card_details = db.query(CardDetail).all()
    return card_details


def retrieve_card_details(db: Session, card_details_id: int):
    card_details = db.query(CardDetail).filter(CardDetail.id == card_details_id).first()
    return card_details


def retrieve_affirmation_card(db: Session, affirmation_number: int):
    affirmation_card = (
        db.query(CardDetail)
        .filter(and_(CardDetail.special_card_action == SpecialActions.AFFIRMATION, CardDetail.affirmation_number == affirmation_number))
        .first()
    )

    if affirmation_card is None:
        return None

    return affirmation_card


def retrieve_random_card_detail_sample(db: Session, n_samples: int = 4):
    return db.query(CardDetail).order_by(func.random()).limit(n_samples).all()


def retrieve_next_available_slot(db: Session, user_id: int, card_details: CardDetail, start_time: datetime) -> Optional[datetime]:
    tod = card_details.tod
    duration = card_details.duration

    # Ensure the initial search time is within the allowable time of day
    if not tod.is_time_in_range(start_time.time()):
        adjusted_start_time = (
            datetime.combine(start_time.date(), tod.start).replace(tzinfo=start_time.tzinfo)
            if tod.end > start_time.time()
            else datetime.combine(start_time.date() + timedelta(days=1), tod.start).replace(tzinfo=start_time.tzinfo)
        )
        search_time = adjusted_start_time
    else:
        search_time = start_time

    max_days = 1 if card_details.category == "Nutrition" else 7  # For 'Nutrition', limit the search to the same day

    for _ in range(max_days * 24 * 4):  # Search for up to `max_days` days, each day has 24 hours and each hour has 4 slots of 15 minutes
        if search_time < start_time:
            search_time += timedelta(minutes=15)
            continue

        if tod.is_time_in_range(search_time.time()) and (card_details.category != "Nutrition" or search_time.date() == start_time.date()):
            card_detail_alias = aliased(CardDetail)

            # Check for conflicts with other cards
            conflicting_cards = (
                db.query(UserCard)
                .join(card_detail_alias, UserCard.card_details_id == card_detail_alias.id)
                .filter(UserCard.user_id == user_id, UserCard.time < search_time + duration, UserCard.time + card_detail_alias.duration > search_time)
                .all()
            )

            if not conflicting_cards:
                # Found an available time slot
                return search_time

        # Move to the next 15-minute interval
        search_time += timedelta(minutes=15)

        # For 'Nutrition' cards, stop searching if we surpass the same day's time range
        if card_details.category == "Nutrition" and search_time.date() > start_time.date():
            break

        # If we've passed the end of the day's available time range, go to the next day's start time
        if search_time.time() >= tod.end:
            if card_details.category == "Nutrition":
                break  # Stop for 'Nutrition' cards to prevent crossing into the next day
            else:
                search_time = search_time.replace(hour=tod.start.hour, minute=tod.start.minute, second=0, microsecond=0) + timedelta(days=1)

    # If no slot is found, return None
    return None


def retrieve_completed_cards_with_score(session: Session, user_id: int, start_date: datetime, end_date: datetime):
    # Define the query to retrieve completed cards within the specified date range
    query = (
        select(CardDetail.title, CardDetail.category, CognitiveScoreImpact.value, CognitiveScoreImpact.new_cognitive_score, UserCard.time)
        .select_from(CardCompletionDetail)
        .join(UserCard, UserCard.card_id == CardCompletionDetail.card_id)
        .join(CardDetail, CardDetail.id == UserCard.card_details_id)
        .join(CognitiveScoreImpact, CognitiveScoreImpact.card_completion_id == CardCompletionDetail.id)
        .filter(
            UserCard.user_id == user_id, CardCompletionDetail.status != CardStatus.ongoing, UserCard.time >= start_date, UserCard.time <= end_date
        )
    )

    # Execute the query
    completed_cards = session.execute(query).all()

    # Return the results as a list of dictionaries
    return [
        {"title": title, "category": category, "value": value, "new_cognitive_score": new_cognitive_score, "time": time}
        for title, category, value, new_cognitive_score, time in completed_cards
    ]


def retrieve_completed_cards(session: Session, user_id: int, start_date: datetime, end_date: datetime):
    # Define the query to retrieve completed cards within the specified date range
    query = (
        select(CardDetail.title, CardCompletionDetail.status, CardCompletionDetail.how_was_it, CardCompletionDetail.reason, UserCard.time)
        .select_from(CardCompletionDetail)
        .join(UserCard, UserCard.card_id == CardCompletionDetail.card_id)
        .join(CardDetail, CardDetail.id == UserCard.card_details_id)
        .join(CognitiveScoreImpact, CognitiveScoreImpact.card_completion_id == CardCompletionDetail.id)
        .filter(
            UserCard.user_id == user_id, CardCompletionDetail.status != CardStatus.ongoing, UserCard.time >= start_date, UserCard.time <= end_date
        )
    )

    # Execute the query
    completed_cards = session.execute(query).all()

    # Return the results as a list of dictionaries
    return [
        {"title": title, "status": status, "how_was_it": how_was_it, "reason": reason, "time": time}
        for title, status, how_was_it, reason, time in completed_cards
    ]


def retrieve_filtered_card_details(
    session: Session, mh_category_name: str, max_duration: timedelta, exclude_ids: Optional[List[int]] = None
) -> List[CardDetail]:
    query = (
        session.query(CardDetail)
        .join(CardMHCategory)
        .join(MHCategory)
        .filter(and_(MHCategory.category_name == mh_category_name, CardDetail.duration < max_duration))
    )

    # exclusion filter if exclude_ids is provided
    if exclude_ids:
        query = query.filter(CardDetail.id.notin_(exclude_ids))

    return query.all()


def update_card_time(db: Session, card: UserCard, new_time: datetime):
    """
    Update the card's time and commit changes.
    """
    card.time = new_time
    db.commit()
    db.refresh(card)
    return card


def delete_card_records_for_user(db: Session, user_id: int):
    try:
        # First find all UserCard records for this user
        user_cards = db.query(UserCard).filter(UserCard.user_id == user_id).all()

        # Get all card IDs belonging to this user
        card_ids = [card.card_id for card in user_cards]

        deleted_counts = {"completion_details": 0, "user_cards": 0}

        if card_ids:
            # First delete all completion details associated with these cards
            # (due to foreign key constraints)
            deleted_counts["completion_details"] = (
                db.query(CardCompletionDetail).filter(CardCompletionDetail.card_id.in_(card_ids)).delete(synchronize_session=False)
            )

            # Then delete the UserCard records
            deleted_counts["user_cards"] = db.query(UserCard).filter(UserCard.user_id == user_id).delete(synchronize_session=False)

            db.commit()
            return deleted_counts

        return deleted_counts

    except Exception as e:
        db.rollback()
        raise Exception(f"Error deleting card records: {str(e)}")
