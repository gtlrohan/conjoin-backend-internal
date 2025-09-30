from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class VoiceMessage(BaseModel):
    speaker: str
    message: str
    timestamp: str
    is_user: bool


class GPTRequest(BaseModel):
    id: int
    messages: List[Message]
    system_prompt: str = "You're a helpful healthcare mentor with knowledge of Kevin's daily scenarios"
    gpt_model: str = "gpt-4.1"
    current_time: Optional[datetime] = None  # User's current demo time for context


class MentorMessage(BaseModel):
    id: int
    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: datetime
    message_type: Literal["text", "voice_session", "system"] = "text"
    session_id: Optional[str] = None  # For voice therapy sessions
    message_count: Optional[int] = None  # Number of messages in voice session

    class Config:
        from_attributes = True


class MentorMessagesResponse(BaseModel):
    messages: List[MentorMessage]
    total_count: int
    status: str = "success"


class VoiceTranscriptRequest(BaseModel):
    session_id: str
    conversation: List[dict]  # List of voice messages with speaker, message, timestamp, is_user fields
