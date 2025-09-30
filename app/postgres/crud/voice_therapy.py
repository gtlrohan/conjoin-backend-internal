from datetime import datetime
from typing import List, Optional

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.postgres.crud.gpt import create_mentor_message
from app.postgres.models.voice_therapy import (
    VoiceSessionMessage,
)
from app.postgres.schema.voice_therapy import VoiceTherapySession


def create_voice_therapy_session(
    db: Session,
    session_id: str,
    user_id: int,
    therapy_type: str,
    mood_before: Optional[str] = None,
    openai_session_id: Optional[str] = None,
    ephemeral_token_expires: Optional[datetime] = None,
) -> VoiceTherapySession:
    """Create a new voice therapy session."""
    db_session = VoiceTherapySession(
        session_id=session_id,
        user_id=user_id,
        therapy_type=therapy_type,
        start_time=datetime.utcnow(),
        mood_before=mood_before,
        openai_session_id=openai_session_id or session_id,  # Default to session_id if not provided
        ephemeral_token_expires=ephemeral_token_expires,
    )
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session


def get_voice_therapy_session(db: Session, session_id: str) -> Optional[VoiceTherapySession]:
    """Get a voice therapy session by session_id."""
    return db.query(VoiceTherapySession).filter(VoiceTherapySession.session_id == session_id).first()


def end_voice_therapy_session(
    db: Session,
    session_id: str,
    session_summary: Optional[str] = None,
    mood_after: Optional[str] = None,
    transcript: Optional[List[VoiceSessionMessage]] = None,
    linked_user_card_id: Optional[int] = None,
) -> Optional[VoiceTherapySession]:
    """End a voice therapy session and update its details."""
    db_session = get_voice_therapy_session(db, session_id)
    if db_session:
        db_session.end_time = datetime.utcnow()
        # Calculate duration in minutes
        if db_session.start_time:
            duration = db_session.end_time - db_session.start_time
            db_session.duration_minutes = int(duration.total_seconds() / 60)

        db_session.session_summary = session_summary
        db_session.mood_after = mood_after
        if linked_user_card_id is not None:
            db_session.linked_user_card_id = linked_user_card_id

        # Store transcript if provided
        if transcript:
            # Serialize timestamps to ISO strings so they can be stored as JSON
            db_session.transcript = [
                {
                    **msg.dict(),
                    "timestamp": msg.timestamp.isoformat() if hasattr(msg, "timestamp") and msg.timestamp else None,
                }
                for msg in transcript
            ]

        db.commit()
        db.refresh(db_session)
    return db_session


def get_user_voice_therapy_sessions(db: Session, user_id: int, limit: int = 20, offset: int = 0) -> List[VoiceTherapySession]:
    """Get voice therapy sessions for a user."""
    return (
        db.query(VoiceTherapySession)
        .filter(VoiceTherapySession.user_id == user_id)
        .order_by(desc(VoiceTherapySession.start_time))
        .offset(offset)
        .limit(limit)
        .all()
    )


def delete_voice_therapy_session(db: Session, session_id: str) -> bool:
    """Delete a voice therapy session."""
    db_session = get_voice_therapy_session(db, session_id)
    if db_session:
        db.delete(db_session)
        db.commit()
        return True
    return False


def process_voice_transcript_for_chat(db: Session, user_id: int, session_id: str, transcript: List[VoiceSessionMessage]) -> str:
    """Process voice transcript and create mentor messages for chat integration.

    This function creates individual mentor messages for each conversation turn,
    making the voice conversation appear naturally in the chat history like ChatGPT.
    """
    try:
        # Create individual mentor messages for each conversation turn
        for i, msg in enumerate(transcript):
            # Determine the role based on speaker
            role = "user" if msg.speaker.lower() == "user" else "assistant"

            # Create mentor message for this conversation turn
            create_mentor_message(
                db=db, user_id=user_id, role=role, content=msg.message, message_type="voice_session", session_id=session_id, message_count=i + 1
            )

        # Create a session completion message
        completion_message = f"""🎤 **Voice Therapy Session Completed**

**Session Summary:**
- Messages exchanged: {len(transcript)}
- Session ID: {session_id}
- Main topics: {_extract_main_topics(transcript)}

**Session Insights:**
This voice therapy session has been completed and integrated into your chat history. You can continue the conversation in text format.

---
*Voice session completed at {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}*"""

        # Create completion mentor message
        create_mentor_message(
            db=db,
            user_id=user_id,
            role="system",
            content=completion_message,
            message_type="voice_session",
            session_id=session_id,
            message_count=len(transcript) + 1,
        )

        return completion_message

    except Exception as e:
        print(f"Error processing voice transcript: {e}")
        return "Voice therapy session completed. Please check your session history for details."


def add_voice_transcript_to_chat(db: Session, user_id: int, transcript: List[VoiceSessionMessage]) -> str:
    """Add voice conversation transcript to main mentor chat and return summary.

    This function formats the voice transcript and creates mentor messages that can be
    integrated with the existing chat system. The summary is returned as a string
    that can be used in the main chat interface.
    """
    try:
        # Generate a unique session ID for this voice session
        session_id = f"voice_session_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

        # Process the transcript and create mentor messages
        return process_voice_transcript_for_chat(db, user_id, session_id, transcript)

    except Exception as e:
        print(f"Error processing voice transcript: {e}")
        return "Voice therapy session completed. Please check your session history for details."


def _extract_main_topics(transcript: List[VoiceSessionMessage]) -> str:
    """Extract main topics from the transcript for summary generation."""
    if not transcript:
        return "general mental health topics"

    # Simple topic extraction based on common therapy keywords
    user_messages = [msg.message.lower() for msg in transcript if msg.speaker == "user"]

    topics = []
    if any(word in " ".join(user_messages) for word in ["anxiety", "worried", "stress"]):
        topics.append("anxiety and stress management")
    if any(word in " ".join(user_messages) for word in ["sleep", "tired", "rest"]):
        topics.append("sleep and rest")
    if any(word in " ".join(user_messages) for word in ["relationship", "partner", "family"]):
        topics.append("relationships")
    if any(word in " ".join(user_messages) for word in ["work", "job", "career"]):
        topics.append("work and career")
    if any(word in " ".join(user_messages) for word in ["depression", "sad", "down"]):
        topics.append("mood and emotional wellbeing")

    if topics:
        return ", ".join(topics)
    else:
        return "general mental health and wellbeing"
