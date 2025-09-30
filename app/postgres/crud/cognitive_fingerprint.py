from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from typing import Optional
from datetime import datetime
from fastapi import HTTPException

from app.postgres.schema.cognitive_fingerprint import CognitiveFingerprint

# from app.services.digital_mentor.cfp import CognitiveFingerprint


# Create
async def create_cognitive_fingerprint(
    db: Session, user_id: int, work_anxiety: float, social_anxiety: float, family_anxiety: float, eating_anxiety: float, sleeping_anxiety: float
) -> CognitiveFingerprint:
    try:
        fingerprint = CognitiveFingerprint(
            user_id=user_id,
            work_anxiety=work_anxiety,
            social_anxiety=social_anxiety,
            family_anxiety=family_anxiety,
            eating_anxiety=eating_anxiety,
            sleeping_anxiety=sleeping_anxiety,
            created_at=datetime.utcnow(),
        )
        db.add(fingerprint)
        db.commit()
        db.refresh(fingerprint)
        return fingerprint
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create cognitive fingerprint: {str(e)}")


# Retrieve single fingerprint (sync version for AI suggestions)
def get_cognitive_fingerprint_by_user_id(db: Session, user_id: int) -> Optional[CognitiveFingerprint]:
    """Get cognitive fingerprint by user ID (synchronous version)"""
    return db.query(CognitiveFingerprint).filter(CognitiveFingerprint.user_id == user_id).first()


# Retrieve single fingerprint
async def retrieve_cognitive_fingerprint(db: Session, user_id: int) -> CognitiveFingerprint:
    try:
        # First try to retrieve the existing fingerprint
        fingerprint = db.query(CognitiveFingerprint).filter(CognitiveFingerprint.user_id == user_id).first()

        # If fingerprint is not found, create a new one using existing create function
        if not fingerprint:
            fingerprint = await create_cognitive_fingerprint(
                db=db, user_id=user_id, work_anxiety=5.0, social_anxiety=5.0, family_anxiety=5.0, eating_anxiety=5.0, sleeping_anxiety=5.0
            )

        return fingerprint

    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


# Update
async def update_cognitive_fingerprint(
    db: Session,
    user_id: int,
    work_anxiety: Optional[float] = None,
    social_anxiety: Optional[float] = None,
    family_anxiety: Optional[float] = None,
    eating_anxiety: Optional[float] = None,
    sleeping_anxiety: Optional[float] = None,
) -> CognitiveFingerprint:
    try:
        fingerprint = db.query(CognitiveFingerprint).filter(CognitiveFingerprint.user_id == user_id).first()

        if not fingerprint:
            raise HTTPException(status_code=404, detail="Cognitive fingerprint not found")

        if work_anxiety is not None:
            fingerprint.work_anxiety = work_anxiety
        if social_anxiety is not None:
            fingerprint.social_anxiety = social_anxiety
        if family_anxiety is not None:
            fingerprint.family_anxiety = family_anxiety
        if eating_anxiety is not None:
            fingerprint.eating_anxiety = eating_anxiety
        if sleeping_anxiety is not None:
            fingerprint.sleeping_anxiety = sleeping_anxiety

        db.commit()
        db.refresh(fingerprint)
        return fingerprint
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update cognitive fingerprint: {str(e)}")


# Delete
async def delete_cognitive_fingerprint(db: Session, user_id: int) -> bool:
    try:
        fingerprint = db.query(CognitiveFingerprint).filter(CognitiveFingerprint.user_id == user_id).first()

        if not fingerprint:
            raise HTTPException(status_code=404, detail="Cognitive fingerprint not found")

        db.delete(fingerprint)
        db.commit()
        return True
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete cognitive fingerprint: {str(e)}")
