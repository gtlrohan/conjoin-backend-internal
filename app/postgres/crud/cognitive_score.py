import datetime

from sqlalchemy.orm import Session

from app.postgres.schema.card import CardCompletionDetail, UserCard
from app.postgres.schema.cognitive_score import CognitiveScore, CognitiveScoreImpact


def create_cognitive_score(db: Session, user_id: int, score: int):
    # Create an instance of CognitiveScore
    cognitive_score = CognitiveScore(user_id=user_id, score=score)
    db.add(cognitive_score)
    db.commit()
    db.refresh(cognitive_score)
    return cognitive_score


def retrieve_cognitive_score(db: Session, user_id: int) -> CognitiveScore:
    # Query to retrieve CognitiveScores based on user_id
    cognitive_score = db.query(CognitiveScore).filter(CognitiveScore.user_id == user_id).first()
    return cognitive_score


def retrieve_user_cognitive_score_impacts(session: Session, user_id: int, start_time: datetime, end_time: datetime):
    # Query to retrieve CognitiveScoreImpacts for a specific user and time range
    impacts = (
        session.query(
            CognitiveScoreImpact.id,
            CognitiveScoreImpact.card_completion_id,
            CognitiveScoreImpact.new_cognitive_score,
            CognitiveScoreImpact.value,
            UserCard.time.label("completed_at"),
        )
        .join(CardCompletionDetail, CognitiveScoreImpact.card_completion_id == CardCompletionDetail.id)
        .join(UserCard, CardCompletionDetail.card_id == UserCard.card_id)
        .filter(UserCard.user_id == user_id, UserCard.time >= start_time, UserCard.time <= end_time)
        .all()
    )
    return [
        {
            "id": impact.id,
            "card_completion_id": impact.card_completion_id,
            "new_cognitive_score": impact.new_cognitive_score,
            "value": impact.value,
            "completed_at": impact.completed_at,
        }
        for impact in impacts
    ]


def update_cognitive_score(db: Session, user_id: int, new_score: float):
    try:
        # Query the existing cognitive score record for the user
        cognitive_score = db.query(CognitiveScore).filter(CognitiveScore.user_id == user_id).first()

        if cognitive_score is None:
            raise Exception(f"No cognitive score record found for user {user_id}")

        # Update the score
        cognitive_score.score = new_score
        db.commit()
        db.refresh(cognitive_score)

        return cognitive_score

    except Exception as e:
        db.rollback()
        raise Exception(f"Error updating cognitive score: {str(e)}")


def delete_cognitive_score_impacts_for_user(db: Session, user_id: int):
    try:
        # Find all cognitive scores for the user
        cognitive_scores = db.query(CognitiveScore).filter(CognitiveScore.user_id == user_id).all()

        # Get all cognitive score IDs
        cognitive_score_ids = [score.id for score in cognitive_scores]

        if cognitive_score_ids:
            # Delete all impacts associated with these cognitive scores
            deleted_count = (
                db.query(CognitiveScoreImpact)
                .filter(CognitiveScoreImpact.cognitive_score_id.in_(cognitive_score_ids))
                .delete(synchronize_session=False)
            )

            db.commit()
            return deleted_count

        return 0

    except Exception as e:
        db.rollback()
        raise Exception(f"Error deleting cognitive score impacts: {str(e)}")
