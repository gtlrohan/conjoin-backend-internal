"""
AI Morning Orientation Suggestions API
Provides 5 personalized daily suggestions for Kevin using GPT-4o
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.middleware.jwt import JWTBearer, decodeJWT
from app.postgres.database import get_db
from app.postgres.crud.cognitive_fingerprint import get_cognitive_fingerprint_by_user_id
from app.postgres.crud.wellness import get_latest_wellness_metrics
from app.services.ai_morning_suggestions import get_kevin_ai_suggestions

router = APIRouter(prefix="/user/morning-orientation", tags=["AI Morning Orientation"])


@router.post("/ai-suggestions")
def get_ai_morning_suggestions(
    db: Session = Depends(get_db),
    access_token: str = Depends(JWTBearer()),
):
    """
    Get 2 primary AI suggestions for Kevin's morning orientation.
    
    This endpoint automatically:
    1. Fetches user's cognitive fingerprint from database
    2. Gets latest wellness metrics (energy & stress levels)
    3. Sends data to GPT-4o for personalized suggestions
    4. Returns first 2 suggestions in same format as /user/morning-orientation
    
    **No input required** - everything is fetched from database using JWT token.
    
    **Returns:**
    - Array of 2 suggestion cards in existing API format
    - Compatible with existing frontend integration
    """
    try:
        # Extract user ID from JWT token
        token = decodeJWT(access_token)
        user_id = token["user_id"]
        
        # Get user's cognitive fingerprint
        cognitive_fingerprint_record = get_cognitive_fingerprint_by_user_id(db, user_id)
        if not cognitive_fingerprint_record:
            raise HTTPException(
                status_code=404, 
                detail="Cognitive fingerprint not found. Please complete your profile first."
            )
        
        # Get user's latest wellness metrics
        latest_wellness = get_latest_wellness_metrics(db, user_id)
        if not latest_wellness:
            raise HTTPException(
                status_code=404,
                detail="Wellness data not found. Please log your daily energy and stress levels first."
            )
        
        # Prepare data for AI service
        cognitive_fingerprint = {
            'work_anxiety': float(cognitive_fingerprint_record.work_anxiety),
            'social_anxiety': float(cognitive_fingerprint_record.social_anxiety),
            'family_anxiety': float(cognitive_fingerprint_record.family_anxiety),
            'eating_anxiety': float(cognitive_fingerprint_record.eating_anxiety),
            'sleeping_anxiety': float(cognitive_fingerprint_record.sleeping_anxiety)
        }
        
        daily_state = {
            'energy_level': float(latest_wellness.energy_level),
            'stress_level': float(latest_wellness.stress_level)
        }
        
        # Get AI suggestions
        suggestions, error = get_kevin_ai_suggestions(
            db, user_id, cognitive_fingerprint, daily_state
        )
        
        if error:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate AI suggestions: {error}"
            )
        
        # Return only first 2 suggestions in same format as existing morning-orientation API
        if not suggestions or len(suggestions) < 2:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate enough AI suggestions"
            )
        
        # Convert tod to string for each card (same as existing API)
        first_two = suggestions[:2]
        for card in first_two:
            # Convert tod to string for each card
            if hasattr(card["card_details"], "tod"):
                card["card_details"].tod = str(card["card_details"].tod)
        
        return first_two
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/ai-alternatives")
def get_ai_alternative_suggestions(
    db: Session = Depends(get_db),
    access_token: str = Depends(JWTBearer()),
):
    """
    Get 3 alternative AI suggestions for Kevin's morning orientation.
    
    Returns the remaining 3 suggestions from the AI model in same format as 
    /user/morning-orientation-suggestion-alternative-activities
    
    **No input required** - everything is fetched from database using JWT token.
    
    **Returns:**
    - Array of 3 alternative suggestion cards in existing API format
    - Compatible with existing frontend integration
    """
    try:
        # Extract user ID from JWT token
        token = decodeJWT(access_token)
        user_id = token["user_id"]
        
        # Get user's cognitive fingerprint
        cognitive_fingerprint_record = get_cognitive_fingerprint_by_user_id(db, user_id)
        if not cognitive_fingerprint_record:
            raise HTTPException(
                status_code=404, 
                detail="Cognitive fingerprint not found. Please complete your profile first."
            )
        
        # Get user's latest wellness metrics
        latest_wellness = get_latest_wellness_metrics(db, user_id)
        if not latest_wellness:
            raise HTTPException(
                status_code=404,
                detail="Wellness data not found. Please log your daily energy and stress levels first."
            )
        
        # Prepare data for AI service
        cognitive_fingerprint = {
            'work_anxiety': float(cognitive_fingerprint_record.work_anxiety),
            'social_anxiety': float(cognitive_fingerprint_record.social_anxiety),
            'family_anxiety': float(cognitive_fingerprint_record.family_anxiety),
            'eating_anxiety': float(cognitive_fingerprint_record.eating_anxiety),
            'sleeping_anxiety': float(cognitive_fingerprint_record.sleeping_anxiety)
        }
        
        daily_state = {
            'energy_level': float(latest_wellness.energy_level),
            'stress_level': float(latest_wellness.stress_level)
        }
        
        # Get AI suggestions
        suggestions, error = get_kevin_ai_suggestions(
            db, user_id, cognitive_fingerprint, daily_state
        )
        
        if error:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate AI suggestions: {error}"
            )
        
        # Return remaining 3 suggestions (skipping first 2)
        if not suggestions or len(suggestions) < 5:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate enough AI suggestions for alternatives"
            )
        
        # Convert tod to string for each card (same as existing API)
        last_three = suggestions[2:5]
        for card in last_three:
            # Convert tod to string for each card
            if hasattr(card["card_details"], "tod"):
                card["card_details"].tod = str(card["card_details"].tod)
        
        return last_three
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/user-state")
def get_user_current_state(
    db: Session = Depends(get_db),
    access_token: str = Depends(JWTBearer()),
):
    """
    Get user's current cognitive fingerprint and wellness state.
    
    Useful for debugging or checking if user has required data before calling AI suggestions.
    """
    try:
        # Extract user ID from JWT token
        token = decodeJWT(access_token)
        user_id = token["user_id"]
        
        # Get user's cognitive fingerprint
        cognitive_fingerprint_record = get_cognitive_fingerprint_by_user_id(db, user_id)
        
        # Get user's latest wellness metrics
        latest_wellness = get_latest_wellness_metrics(db, user_id)
        
        return {
            "user_id": user_id,
            "has_cognitive_fingerprint": cognitive_fingerprint_record is not None,
            "has_wellness_data": latest_wellness is not None,
            "cognitive_fingerprint": {
                "work_anxiety": float(cognitive_fingerprint_record.work_anxiety) if cognitive_fingerprint_record else None,
                "social_anxiety": float(cognitive_fingerprint_record.social_anxiety) if cognitive_fingerprint_record else None,
                "family_anxiety": float(cognitive_fingerprint_record.family_anxiety) if cognitive_fingerprint_record else None,
                "eating_anxiety": float(cognitive_fingerprint_record.eating_anxiety) if cognitive_fingerprint_record else None,
                "sleeping_anxiety": float(cognitive_fingerprint_record.sleeping_anxiety) if cognitive_fingerprint_record else None
            } if cognitive_fingerprint_record else None,
            "latest_wellness": {
                "energy_level": float(latest_wellness.energy_level),
                "stress_level": float(latest_wellness.stress_level),
                "date": latest_wellness.date.isoformat(),
                "created_at": latest_wellness.created_at.isoformat()
            } if latest_wellness else None,
            "ready_for_ai_suggestions": cognitive_fingerprint_record is not None and latest_wellness is not None
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get user state: {str(e)}"
        )
