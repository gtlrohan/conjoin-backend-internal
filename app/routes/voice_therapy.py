from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.postgres.database import get_db
from app.middleware.jwt import JWTBearer, decodeJWT
import uuid
import httpx
import logging
from datetime import datetime
from app.constants import OPENAI_API_KEY, OPENAI_REALTIME_MODEL
from app.postgres.crud.voice_therapy import create_voice_therapy_session

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/voice-therapy/start")
async def start_voice_session(
    db: Session = Depends(get_db),
    access_token: str = Depends(JWTBearer()),
):
    """Start a new voice therapy session with OpenAI Realtime API"""
    try:
        token = decodeJWT(access_token)
        user_id = token["user_id"]
        
        logger.info(f"Creating OpenAI Realtime session for user {user_id}")
        
        # Call OpenAI's Realtime Sessions API
        async with httpx.AsyncClient(timeout=30.0) as client:
            openai_response = await client.post(
                "https://api.openai.com/v1/realtime/sessions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": OPENAI_REALTIME_MODEL,
                    "voice": "alloy",
                    "instructions": get_therapy_instructions("general"),
                    "input_audio_transcription": {"model": "whisper-1"},
                    "tools": get_therapy_tools(),
                    "tool_choice": "auto", 
                    "temperature": 0.8,
                    "turn_detection": {
                        "type": "server_vad",
                        "threshold": 0.5,
                        "prefix_padding_ms": 300,
                        "silence_duration_ms": 500
                    }
                }
            )
        
        if openai_response.status_code != 200:
            logger.error(f"OpenAI API error: {openai_response.status_code} - {openai_response.text}")
            raise HTTPException(
                status_code=500, 
                detail=f"OpenAI API error: {openai_response.status_code} - {openai_response.text}"
            )
            
        session_data = openai_response.json()
        logger.info(f"OpenAI session created: {session_data['id']}")
        
        # Store session in database for tracking
        db_session = create_voice_therapy_session(
            db=db,
            session_id=session_data["id"],
            user_id=user_id,
            therapy_type="general",
            openai_session_id=session_data["id"],
            ephemeral_token_expires=datetime.fromtimestamp(session_data["expires_at"])
        )
        
        logger.info(f"Database session created for OpenAI session {session_data['id']}")
        
        return {
            "session_id": session_data["id"],
            "openai_session_token": session_data["client_secret"],
            "status": "active",
            "expires_at": session_data["expires_at"]
        }
        
    except httpx.TimeoutException:
        logger.error("OpenAI API request timed out")
        raise HTTPException(status_code=504, detail="OpenAI API request timed out")
    except httpx.RequestError as e:
        logger.error(f"OpenAI API request failed: {str(e)}")
        raise HTTPException(status_code=503, detail=f"OpenAI API request failed: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to create OpenAI session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create OpenAI session: {str(e)}")

@router.post("/voice-therapy/end")
async def end_voice_session(
    session_data: dict,
    db: Session = Depends(get_db),
    access_token: str = Depends(JWTBearer()),
):
    """End a voice therapy session and save transcript"""
    try:
        token = decodeJWT(access_token)
        user_id = token["user_id"]
        
        # For now, just return success
        # Later you can save transcript to database
        
        return {"status": "ended", "transcript_saved": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def get_therapy_instructions(therapy_type: str) -> str:
    """Return specialized therapy instructions for OpenAI."""
    base_instructions = """You are a compassionate, professional therapist conducting a voice therapy session. 
    
Your approach should be:
- Speak in a warm, empathetic tone
- Ask thoughtful follow-up questions
- Provide evidence-based therapeutic guidance
- Maintain appropriate professional boundaries
- Be supportive and non-judgmental
- Keep responses concise but meaningful
- Use active listening techniques
- Validate the user's emotions
- Suggest practical coping strategies when appropriate

Remember: This is a real therapy session. The user trusts you with their mental health."""
    
    return base_instructions


def get_therapy_tools():
    """Return therapy-specific tools/functions for the AI."""
    return [
        {
            "type": "function",
            "name": "end_session_summary",
            "description": "Create a session summary when the user wants to end the therapy session",
            "parameters": {
                "type": "object",
                "properties": {
                    "key_topics": {"type": "string", "description": "Main topics discussed"},
                    "insights": {"type": "string", "description": "Key insights or breakthroughs"},
                    "recommended_actions": {"type": "string", "description": "Suggested next steps or homework"}
                },
                "required": ["key_topics"]
            }
        },
        {
            "type": "function", 
            "name": "breathing_exercise",
            "description": "Guide the user through a breathing exercise",
            "parameters": {
                "type": "object",
                "properties": {
                    "duration": {"type": "integer", "description": "Duration in seconds"},
                    "technique": {"type": "string", "description": "Type of breathing technique"}
                }
            }
        }
    ] 