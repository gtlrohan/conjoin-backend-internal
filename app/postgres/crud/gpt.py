from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.postgres.schema.gpt import MentorMessage


def create_mentor_message(
    db: Session,
    user_id: int,
    role: str,
    content: str,
    message_type: str = "text",
    session_id: Optional[str] = None,
    message_count: Optional[int] = None,
) -> MentorMessage:
    """Create a new mentor message."""
    db_message = MentorMessage(
        user_id=user_id,
        role=role,
        content=content,
        timestamp=datetime.utcnow(),
        message_type=message_type,
        session_id=session_id,
        message_count=message_count,
    )
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    return db_message


def get_mentor_messages(db: Session, user_id: int, limit: int = 50, offset: int = 0) -> List[MentorMessage]:
    """Get mentor messages for a user, ordered by timestamp descending."""
    return db.query(MentorMessage).filter(MentorMessage.user_id == user_id).order_by(desc(MentorMessage.timestamp)).offset(offset).limit(limit).all()


def get_mentor_message_count(db: Session, user_id: int) -> int:
    """Get total count of mentor messages for a user."""
    return db.query(MentorMessage).filter(MentorMessage.user_id == user_id).count()


def get_recent_voice_sessions(db: Session, user_id: int, limit: int = 5, days_back: int = 7) -> List[MentorMessage]:
    """Get recent voice therapy session summaries."""
    cutoff_date = datetime.utcnow() - timedelta(days=days_back)

    return (
        db.query(MentorMessage)
        .filter(MentorMessage.user_id == user_id, MentorMessage.message_type == "voice_session", MentorMessage.timestamp >= cutoff_date)
        .order_by(desc(MentorMessage.timestamp))
        .limit(limit)
        .all()
    )


def create_voice_session_summary(db: Session, user_id: int, session_id: str, conversation: List[dict]) -> MentorMessage:
    """Create a mentor message from a voice therapy session transcript."""

    # Format the voice session as a readable conversation
    formatted_transcript = f"🎙️ **Voice Therapy Session**\nSession ID: {session_id}\nDate: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

    for message in conversation:
        speaker_icon = "👤" if message.get("is_user", False) else "🤖"
        speaker_name = message.get("speaker", "Unknown")
        message_text = message.get("message", "")
        message.get("timestamp", "")

        formatted_transcript += f"{speaker_icon} **{speaker_name}**: {message_text}\n\n"

    # Add session summary footer
    formatted_transcript += f"---\n*Voice therapy session completed at {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}*"

    # Create the mentor message
    return create_mentor_message(
        db=db, user_id=user_id, role="system", content=formatted_transcript, message_type="voice_session", session_id=session_id
    )


def delete_mentor_message(db: Session, message_id: int, user_id: int) -> bool:
    """Delete a mentor message (only if owned by the user)."""
    db_message = db.query(MentorMessage).filter(MentorMessage.id == message_id, MentorMessage.user_id == user_id).first()

    if db_message:
        db.delete(db_message)
        db.commit()
        return True
    return False
