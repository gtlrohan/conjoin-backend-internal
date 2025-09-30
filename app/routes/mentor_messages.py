import logging
from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.middleware.jwt import JWTBearer, decodeJWT
from app.postgres.database import get_db
from app.postgres.crud.gpt import (
    get_mentor_messages,
    get_mentor_message_count,
    create_voice_session_summary,
    get_recent_voice_sessions,
)
from app.postgres.models.gpt import MentorMessagesResponse, VoiceTranscriptRequest

router = APIRouter(prefix="/mentor-messages", tags=["Mentor Messages"])
logger = logging.getLogger(__name__)


@router.get("/test")
async def test_mentor_messages():
    """
    Simple test endpoint to verify the router is working
    """
    return {
        "message": "Mentor messages router is working!", 
        "status": "success",
        "timestamp": datetime.now().isoformat()
    }


@router.get("/", response_model=MentorMessagesResponse)
async def get_user_mentor_messages(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    access_token: str = Depends(JWTBearer())
):
    """
    Retrieves mentor messages for the authenticated user including voice session transcripts
    """
    try:
        token = decodeJWT(access_token)
        user_id = token["user_id"]
        
        # Get messages from database
        messages = get_mentor_messages(db, user_id, limit, offset)
        total_count = get_mentor_message_count(db, user_id)
        
        return MentorMessagesResponse(
            messages=messages,
            total_count=total_count,
            status="success"
        )
        
    except Exception as e:
        logger.error(f"Error in get_mentor_messages: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/voice-session")
async def save_voice_session_to_chat(
    body: VoiceTranscriptRequest,
    db: Session = Depends(get_db),
    access_token: str = Depends(JWTBearer())
):
    """
    Saves a voice therapy session transcript to the mentor chat
    """
    try:
        token = decodeJWT(access_token)
        user_id = token["user_id"]
        
        # Format the voice session as a mentor message
        formatted_transcript = f"🎙️ **Voice Therapy Session**\nSession ID: {body.session_id}\nDate: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        for message in body.conversation:
            speaker_icon = "👤" if message.get("is_user", False) else "🤖"
            speaker_name = message.get("speaker", "Unknown")
            message_text = message.get("message", "")
            formatted_transcript += f"{speaker_icon} **{speaker_name}**: {message_text}\n\n"
        
        # Save to database as a mentor message
        mentor_message = create_voice_session_summary(
            db=db,
            user_id=user_id,
            session_id=body.session_id,
            conversation=body.conversation
        )
        
        logger.info(f"Voice session {body.session_id} saved as mentor message for user {user_id}")
        
        return {
            "status": "success",
            "message": "Voice session saved to mentor chat",
            "message_id": mentor_message.id
        }
        
    except Exception as e:
        logger.error(f"Error saving voice session: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error") 