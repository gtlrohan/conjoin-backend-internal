import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Optional

from app.middleware.jwt import JWTBearer, decodeJWT
from app.postgres.database import get_db
from app.postgres.crud.card import retrieve_card_by_id
from app.postgres.crud.voice_therapy import get_voice_therapy_session

router = APIRouter(prefix="/father-analysis", tags=["Father Analysis Cards"])
logger = logging.getLogger(__name__)


@router.get("/card/{card_id}/analysis")
async def get_card_analysis_data(
    card_id: int,
    db: Session = Depends(get_db),
    access_token: str = Depends(JWTBearer()),
):
    """
    Get the A-G matrix analysis data for a father call reflection card.
    This shows the detailed analysis when the card is clicked.
    """
    try:
        token = decodeJWT(access_token)
        user_id = token["user_id"]
        
        # Get the card
        card = retrieve_card_by_id(db, user_id, card_id)
        if not card:
            raise HTTPException(status_code=404, detail="Card not found")
        
        # Check if this is a reflection card with analysis data
        if not card.card_details.details or 'matrix_analysis' not in card.card_details.details:
            raise HTTPException(status_code=400, detail="This card doesn't contain analysis data")
        
        # Extract analysis data from card details
        details = card.card_details.details
        session_id = details.get('session_id')
        
        # Get the voice session for additional context
        voice_session = None
        if session_id:
            voice_session = get_voice_therapy_session(db, session_id)
        
        # Format the A-G matrix results for display
        matrix_analysis = details.get('matrix_analysis', {})
        conversation_summary = details.get('conversation_summary', '')
        suggestions = details.get('suggestions', [])
        rationales = details.get('rationales', {})
        
        # Create formatted response
        response = {
            'card_id': card_id,
            'card_title': card.card_details.title,
            'session_id': session_id,
            'analysis_data': {
                'matrix_selections': matrix_analysis,
                'conversation_summary': conversation_summary,
                'suggestions': suggestions,
                'rationales': rationales,
            },
            'session_data': {
                'duration_minutes': voice_session.duration_minutes if voice_session else None,
                'therapy_type': voice_session.therapy_type if voice_session else None,
                'start_time': voice_session.start_time.isoformat() if voice_session else None,
                'transcript_available': bool(voice_session and voice_session.transcript),
            } if voice_session else None
        }
        
        logger.info(f"Retrieved analysis data for card {card_id}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving analysis data for card {card_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve analysis data")


@router.get("/matrix-labels")
async def get_matrix_labels():
    """
    Get the human-readable labels for A-G matrix categories.
    Used by frontend to display matrix results properly.
    """
    matrix_labels = {
        'A': {
            1: "90-100% Kevin talking",
            2: "70-90% Kevin talking", 
            3: "50-70% Kevin talking",
            4: "Equal participation",
            5: "50-70% Father talking",
            6: "70-90% Father talking",
            7: "90-100% Father talking",
            99: "Dynamic/Custom assessment"
        },
        'B': {
            10: "Aggressive/Hostile",
            11: "Patronizing/Condescending", 
            12: "Distant/Cold",
            13: "Critical/Judgmental",
            14: "Intrusive/Nosy",
            15: "Lying/Deceptive",
            16: "Irrational/Unreasonable",
            17: "Self-obsessed/Narcissistic",
            18: "Dismissive/Invalidating",
            19: "Manipulative/Guilt-tripping",
            20: "Supportive/Understanding",
            21: "Neutral/Matter-of-fact",
            99: "Custom behavior"
        },
        'C': {
            21: "Very rare",
            22: "Somewhat rare", 
            23: "Frequent",
            24: "Very frequent/constant",
            25: "Not specific to Kevin",
            99: "Custom frequency"
        },
        'D': {
            31: "Politics/Current events",
            32: "Sports/Hobbies",
            33: "Kevin's friendships",
            34: "Kevin's family relationships",
            35: "Kevin's romantic life", 
            36: "Work/Career issues",
            37: "Health issues",
            38: "Kevin's appearance",
            39: "Past issues",
            40: "Money/Financial matters",
            41: "Future plans",
            42: "Daily activities",
            43: "Father's own problems",
            44: "Family obligations",
            99: "Custom topic"
        },
        'E': {
            41: "Mildly uncomfortable",
            42: "Moderately bad",
            43: "Very bad/distressing",
            44: "Extremely bad/traumatic",
            45: "Positive/Helpful",
            99: "Custom severity"
        },
        'F': {
            51: "Surprised/Shocked",
            52: "Stressed/Anxious", 
            53: "Insecure/Self-doubting",
            54: "Rejected/Unwanted",
            55: "Frustrated/Irritated",
            56: "Let down/Disappointed",
            57: "Humiliated/Embarrassed",
            58: "Hurt/Wounded",
            59: "Guilty/Self-blaming",
            60: "Isolated/Alone",
            61: "Fragile/Vulnerable",
            62: "Angry/Furious",
            63: "Sad/Depressed",
            64: "Confused/Uncertain",
            65: "Defensive/Protective",
            66: "Numb/Disconnected",
            67: "Relieved (when ended)",
            68: "Empowered/Strong",
            99: "Custom emotion"
        },
        'G': {
            71: "Confronted/Argued back",
            72: "Escaped/Hung up", 
            73: "De-escalated/Calmed",
            74: "Just listened/Neutral",
            75: "Defended self/Explained",
            76: "Yelled/Raised voice",
            77: "Shut down/Silent",
            78: "Gave in/Agreed",
            79: "Set boundaries",
            80: "Asked for help",
            81: "Changed subject",
            99: "Custom action"
        }
    }
    
    return {
        'matrix_labels': matrix_labels,
        'categories': {
            'A': 'Father vs Kevin main driver',
            'B': 'Father on call — personality', 
            'C': 'Specific to user?',
            'D': 'Content of call (dominant topic)',
            'E': 'How bad',
            'F': 'Kevin feelings on call',
            'G': 'Kevin actions on call'
        }
    }
