from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class TherapyType(str, Enum):
    GENERAL = "general"
    ANXIETY = "anxiety"
    STRESS = "stress"
    DEPRESSION = "depression"
    SLEEP = "sleep"
    FATHER_CALL_ANALYSIS = "father_call_analysis"


class VoiceSessionStartRequest(BaseModel):
    therapy_type: TherapyType
    mood_before: Optional[str] = None
    # Optional frontend-provided context
    entry_source: Optional[str] = None  # "voice_chat" | "card_followup" | "text_chat"
    context_summary: Optional[str] = None  # short 1-2 sentence summary for greeting
    # Optional overrides for VAD/STT
    vad_threshold: Optional[float] = None
    vad_prefix_padding_ms: Optional[int] = None
    vad_silence_duration_ms: Optional[int] = None
    stt_language: Optional[str] = None


class VoiceSessionStartResponse(BaseModel):
    session_id: str
    websocket_url: Optional[str] = None  # Not used for WebRTC
    therapy_type: str
    start_time: datetime
    client_secret: Optional[dict] = None  # OpenAI ephemeral token
    expires_at: Optional[int] = None  # Token expiration timestamp


class VoiceSessionMessage(BaseModel):
    speaker: str  # "user" or "ai"
    message: str
    timestamp: datetime
    source: Optional[str] = None  # "stt" | "tts" | None


class VoiceSessionEndRequest(BaseModel):
    session_summary: Optional[str] = None
    mood_after: Optional[str] = None
    transcript: Optional[List[VoiceSessionMessage]] = None
    save_to_chat: bool = False
    linked_user_card_id: Optional[int] = None


class VoiceSessionResponse(BaseModel):
    session_id: str
    user_id: int
    therapy_type: str
    start_time: datetime
    end_time: Optional[datetime]
    duration_minutes: Optional[int]
    session_summary: Optional[str]
    mood_before: Optional[str]
    mood_after: Optional[str]
    transcript: Optional[List[VoiceSessionMessage]]
    created_at: datetime
    # Optional preview of analysis for special sessions (e.g., father_call_analysis)
    analysis_preview: Optional[dict] = None

    class Config:
        from_attributes = True


class VoiceSessionsListResponse(BaseModel):
    sessions: List[VoiceSessionResponse]
    total_count: int


# Models for Father Call Analysis
class FatherCallAnalysisRequest(BaseModel):
    session_id: str = Field(..., description="Voice therapy session ID to analyze")


class MatrixSelection(BaseModel):
    category: str = Field(..., description="Matrix category (A-G)")
    value: int = Field(..., description="Selected number for this category")
    label: str = Field(..., description="Human-readable label for this selection")
    rationale: str = Field(..., description="AI explanation for why this was selected")


class AnalysisSuggestion(BaseModel):
    id: str = Field(..., description="Unique suggestion identifier")
    category: str = Field(..., description="Suggestion category")
    name: str = Field(..., description="Suggestion name/title")
    description: str = Field(..., description="Detailed description")
    triggered_by: List[int] = Field(..., description="Matrix numbers that triggered this suggestion")
    rationale: str = Field(..., description="Why this suggestion was selected")
    recommended_actions: List[str] = Field(..., description="Specific recommended actions")


class FatherCallAnalysisResponse(BaseModel):
    session_id: str = Field(..., description="Analyzed session ID")
    matrix_selections: List[MatrixSelection] = Field(..., description="A-G matrix categorizations")
    conversation_summary: str = Field(..., description="Summary of the father call discussion")
    suggestions: List[AnalysisSuggestion] = Field(..., description="Therapeutic suggestions based on analysis")
    analysis_complete: bool = Field(True, description="Whether analysis was completed successfully")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Analysis timestamp")


class WebSocketMessage(BaseModel):
    type: str  # "audio", "text", "control"
    data: Optional[str] = None  # Base64 encoded audio or text message
    timestamp: Optional[datetime] = None


class WebSocketResponse(BaseModel):
    type: str  # "audio", "text", "error", "status"
    data: Optional[str] = None
    session_id: Optional[str] = None
    timestamp: datetime = None
