import logging
from datetime import datetime
from typing import Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.constants import (
    OPENAI_API_KEY,
    OPENAI_REALTIME_MODEL,
    REALTIME_STT_LANGUAGE,
    REALTIME_STT_MODEL,
    REALTIME_VAD_PREFIX_PADDING_MS,
    REALTIME_VAD_SILENCE_DURATION_MS,
    REALTIME_VAD_THRESHOLD,
)
from app.middleware.jwt import JWTBearer, decodeJWT
from app.postgres.crud.gpt import create_mentor_message, get_mentor_messages
from app.postgres.crud.voice_therapy import (
    add_voice_transcript_to_chat,
    create_voice_therapy_session,
    end_voice_therapy_session,
    get_user_voice_therapy_sessions,
    get_voice_therapy_session,
    process_voice_transcript_for_chat,
)
from app.postgres.database import get_db
from app.postgres.models.voice_therapy import (
    AnalysisSuggestion,
    FatherCallAnalysisRequest,
    FatherCallAnalysisResponse,
    MatrixSelection,
    VoiceSessionEndRequest,
    VoiceSessionMessage,
    VoiceSessionResponse,
    VoiceSessionsListResponse,
    VoiceSessionStartRequest,
    VoiceSessionStartResponse,
)

router = APIRouter(prefix="/voice-therapist", tags=["Voice Therapist"])
logger = logging.getLogger(__name__)


@router.post("/session/start", response_model=VoiceSessionStartResponse)
async def start_voice_session(
    request: VoiceSessionStartRequest,
    db: Session = Depends(get_db),
    access_token: str = Depends(JWTBearer()),
):
    """
    Create OpenAI Realtime API session and return ephemeral credentials.
    """
    try:
        token = decodeJWT(access_token)
        user_id = token["user_id"]

        logger.info(f"Creating OpenAI Realtime session for user {user_id}, therapy type: {request.therapy_type}")
        logger.info(
            f"Kevin's context will be included in session instructions (entry_source: {request.entry_source}, context_summary: {request.context_summary})"
        )

        # Resolve VAD/STT settings (request overrides env defaults)
        vad_threshold = request.vad_threshold if getattr(request, "vad_threshold", None) is not None else REALTIME_VAD_THRESHOLD
        vad_prefix_padding_ms = (
            request.vad_prefix_padding_ms if getattr(request, "vad_prefix_padding_ms", None) is not None else REALTIME_VAD_PREFIX_PADDING_MS
        )
        vad_silence_duration_ms = (
            request.vad_silence_duration_ms if getattr(request, "vad_silence_duration_ms", None) is not None else REALTIME_VAD_SILENCE_DURATION_MS
        )
        stt_language = request.stt_language or REALTIME_STT_LANGUAGE

        # Call OpenAI's Realtime Sessions API
        async with httpx.AsyncClient(timeout=30.0) as client:
            openai_response = await client.post(
                "https://api.openai.com/v1/realtime/sessions",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
                json={
                    "model": OPENAI_REALTIME_MODEL,
                    "voice": "alloy",
                    "instructions": build_contextual_instructions(db, user_id, request.therapy_type, request.entry_source, request.context_summary),
                    "input_audio_transcription": {"model": REALTIME_STT_MODEL, "language": stt_language},
                    "tools": get_therapy_tools(),
                    "tool_choice": "auto",
                    "temperature": 0.8,
                    "turn_detection": {
                        "type": "server_vad",
                        "threshold": vad_threshold,
                        "prefix_padding_ms": vad_prefix_padding_ms,
                        "silence_duration_ms": vad_silence_duration_ms,
                    },
                },
            )

        if openai_response.status_code != 200:
            logger.error(f"OpenAI API error: {openai_response.status_code} - {openai_response.text}")
            raise HTTPException(status_code=500, detail=f"OpenAI API error: {openai_response.status_code} - {openai_response.text}")

        session_data = openai_response.json()
        logger.info(f"OpenAI session created: {session_data['id']}")

        # Store session in database for tracking
        db_session = create_voice_therapy_session(
            db=db,
            session_id=session_data["id"],
            user_id=user_id,
            therapy_type=request.therapy_type,
            mood_before=request.mood_before,
            openai_session_id=session_data["id"],
            ephemeral_token_expires=datetime.fromtimestamp(session_data["expires_at"]),
        )

        logger.info(f"Database session created for OpenAI session {session_data['id']}")

        return VoiceSessionStartResponse(
            session_id=session_data["id"],
            websocket_url=None,  # Not used for WebRTC
            therapy_type=request.therapy_type,
            start_time=db_session.start_time,
            client_secret=session_data["client_secret"],
            expires_at=session_data["expires_at"],
        )

    except httpx.TimeoutException:
        logger.error("OpenAI API request timed out")
        raise HTTPException(status_code=504, detail="OpenAI API request timed out")
    except httpx.RequestError as e:
        logger.error(f"OpenAI API request failed: {str(e)}")
        raise HTTPException(status_code=503, detail=f"OpenAI API request failed: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to create OpenAI session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create OpenAI session: {str(e)}")


@router.post("/session/{session_id}/end", response_model=VoiceSessionResponse)
async def end_voice_session(
    session_id: str,
    request: VoiceSessionEndRequest,
    db: Session = Depends(get_db),
    access_token: str = Depends(JWTBearer()),
):
    """
    End OpenAI Realtime session and save session data with transcript integration.
    Automatically saves voice transcript to mentor chat.
    """
    try:
        token = decodeJWT(access_token)
        user_id = token["user_id"]

        # Find session in database
        db_session = get_voice_therapy_session(db, session_id)
        if not db_session:
            raise HTTPException(status_code=404, detail="Session not found")

        if db_session.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to end this session")

        # End the session in database with transcript
        updated_session = end_voice_therapy_session(
            db=db,
            session_id=session_id,
            session_summary=request.session_summary,
            mood_after=request.mood_after,
            transcript=request.transcript,
            linked_user_card_id=request.linked_user_card_id,
        )

        if not updated_session:
            raise HTTPException(status_code=404, detail="Failed to end session")

        # Optionally save transcript to mentor chat (opt-in)
        chat_summary = None
        if request.save_to_chat and request.transcript:
            try:
                chat_summary = process_voice_transcript_for_chat(db, user_id, session_id, request.transcript)
                logger.info(f"Voice transcript saved to mentor chat for session {session_id}")
            except Exception as e:
                logger.error(f"Failed to save transcript to mentor chat: {e}")

        # For father call analysis sessions, analyze transcript and return preview (don't auto-schedule)
        analysis_preview = None
        logger.info(
            f"Checking for father call analysis: therapy_type={updated_session.therapy_type}, has_transcript={bool(request.transcript)}, transcript_length={len(request.transcript) if request.transcript else 0}"
        )

        if updated_session.therapy_type == "father_call_analysis" and request.transcript and len(request.transcript) > 0:
            # COMPREHENSIVE VALIDATION: Ensure transcript has meaningful conversation content
            total_content = "".join([msg.message for msg in request.transcript if msg.message])
            user_messages = [msg.message for msg in request.transcript if msg.speaker == "user" and msg.message]
            assistant_messages = [msg.message for msg in request.transcript if msg.speaker == "assistant" and msg.message]

            total_user_content = "".join(user_messages).strip()
            total_assistant_content = "".join(assistant_messages).strip()

            logger.info("Transcript validation:")
            logger.info(f"- Total content: {len(total_content)} chars")
            logger.info(f"- User content: {len(total_user_content)} chars")
            logger.info(f"- Assistant content: {len(total_assistant_content)} chars")
            logger.info(f"- User messages: {len(user_messages)}")
            logger.info(f"- Assistant messages: {len(assistant_messages)}")
            logger.info(f"- First 200 chars: '{total_content[:200]}'")

            # STRICT VALIDATION: Must have real conversation from both sides
            greeting_words = ["hello", "hi", "hey", "hello there", "hi there", "thank you", "thanks"]
            non_greeting_messages = [msg for msg in user_messages if msg.lower().strip() not in greeting_words and len(msg.strip()) > 3]

            logger.info(f"- Non-greeting messages: {len(non_greeting_messages)}")
            logger.info(f"- Sample non-greetings: {non_greeting_messages[:3] if non_greeting_messages else 'None'}")

            has_meaningful_conversation = (
                len(request.transcript) >= 2
                and len(total_user_content) >= 20  # At least 2 messages
                and len(total_assistant_content) >= 50  # User said at least 20 meaningful characters
                and len(user_messages) >= 2  # AI responded meaningfully
                and len(assistant_messages) >= 2  # Has multiple user messages
                and len(non_greeting_messages) >= 1  # Has multiple AI responses  # At least one substantive message beyond greetings
            )

            if not has_meaningful_conversation:
                logger.warning("Insufficient meaningful conversation for father call analysis:")
                logger.warning(
                    f"- Messages: {len(request.transcript)}, User chars: {len(total_user_content)}, AI chars: {len(total_assistant_content)}"
                )
                logger.warning("- Skipping analysis to prevent fake matrix generation")
                analysis_preview = None
            else:
                try:
                    analysis_result = await _analyze_father_call_transcript(db, user_id, session_id, request.transcript)
                    if analysis_result and analysis_result.get("analysis_complete", False):
                        logger.info(f"Father call analysis completed successfully for session {session_id}")
                        analysis_preview = {
                            "session_id": session_id,
                            "matrix": analysis_result.get("matrix_selections"),
                            "summary": analysis_result.get("conversation_summary", ""),
                            "suggestions": analysis_result.get("suggestions", []),
                            "cta": {
                                "label": "Add to plan",
                                "action": f"/voice-therapist/session/{session_id}/schedule-father-reflection",
                                "title": "Follow up on bad call with father",
                            },
                        }
                    else:
                        logger.info(f"Father call analysis could not be completed for session {session_id} - insufficient conversation content")
                        analysis_preview = None
                except Exception as e:
                    logger.error(f"Error in father call analysis for session {session_id}: {e}")

        logger.info(f"Final analysis_preview status: {bool(analysis_preview)} for session {session_id}")

        logger.info(f"Ended voice therapy session {session_id} for user {user_id}")

        # Create response with session data
        response = VoiceSessionResponse.from_orm(updated_session)
        if analysis_preview:
            # Attach non-ORM field manually
            response.analysis_preview = analysis_preview

        # Add chat summary to response if available
        if chat_summary:
            # We could extend the response model to include this, but for now
            # we'll log it and the frontend can handle it appropriately
            logger.info(f"Chat summary generated for session {session_id}: {chat_summary[:100]}...")

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ending voice session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to end session: {str(e)}")


@router.get("/sessions", response_model=VoiceSessionsListResponse)
async def get_user_sessions(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    access_token: str = Depends(JWTBearer()),
):
    """
    Get user's voice therapy session history.
    """
    try:
        token = decodeJWT(access_token)
        user_id = token["user_id"]

        sessions = get_user_voice_therapy_sessions(
            db=db,
            user_id=user_id,
            limit=limit,
            offset=offset,
        )

        session_responses = [VoiceSessionResponse.from_orm(session) for session in sessions]

        return VoiceSessionsListResponse(
            sessions=session_responses,
            total_count=len(session_responses),
        )

    except Exception as e:
        logger.error(f"Error retrieving user sessions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve sessions: {str(e)}")


@router.get("/session/{session_id}/summary")
async def get_session_summary(
    session_id: str,
    db: Session = Depends(get_db),
    access_token: str = Depends(JWTBearer()),
):
    """
    Get a formatted summary of a voice therapy session for chat integration.
    """
    try:
        token = decodeJWT(access_token)
        user_id = token["user_id"]

        # Find session in database
        db_session = get_voice_therapy_session(db, session_id)
        if not db_session:
            raise HTTPException(status_code=404, detail="Session not found")

        if db_session.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to access this session")

        # Generate summary from transcript if available
        if db_session.transcript:
            # Convert stored transcript back to VoiceSessionMessage objects
            transcript_messages = [
                VoiceSessionMessage(speaker=msg["speaker"], message=msg["message"], timestamp=datetime.fromisoformat(msg["timestamp"]))
                for msg in db_session.transcript
            ]

            summary = add_voice_transcript_to_chat(db, user_id, transcript_messages)
        else:
            # Create a basic summary if no transcript is available
            summary = f"""🎤 **Voice Therapy Session Summary**

**Session Details:**
- Therapy Type: {db_session.therapy_type}
- Duration: {db_session.duration_minutes or 'Unknown'} minutes
- Mood Before: {db_session.mood_before or 'Not recorded'}
- Mood After: {db_session.mood_after or 'Not recorded'}

**Session Summary:**
{db_session.session_summary or 'No summary available'}

---
*This summary was generated from your voice therapy session.*"""

        return {
            "session_id": session_id,
            "summary": summary,
            "therapy_type": db_session.therapy_type,
            "duration_minutes": db_session.duration_minutes,
            "has_transcript": bool(db_session.transcript),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session summary for {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get session summary: {str(e)}")


@router.get("/session/{session_id}/transcript")
async def get_session_transcript(
    session_id: str,
    db: Session = Depends(get_db),
    access_token: str = Depends(JWTBearer()),
):
    """Return raw transcript messages for a completed session without posting to chat."""
    try:
        token = decodeJWT(access_token)
        user_id = token["user_id"]

        db_session = get_voice_therapy_session(db, session_id)
        if not db_session:
            raise HTTPException(status_code=404, detail="Session not found")
        if db_session.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to access this session")

        return {
            "session_id": session_id,
            "transcript": db_session.transcript or [],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session transcript for {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get transcript: {str(e)}")


@router.post("/session/{session_id}/send-to-chat")
async def send_session_to_chat(
    session_id: str,
    db: Session = Depends(get_db),
    access_token: str = Depends(JWTBearer()),
):
    """
    Send a voice therapy session summary to the main chat system.
    This creates a seamless integration between voice therapy and chat.
    """
    try:
        token = decodeJWT(access_token)
        user_id = token["user_id"]

        # Find session in database
        db_session = get_voice_therapy_session(db, session_id)
        if not db_session:
            raise HTTPException(status_code=404, detail="Session not found")

        if db_session.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to access this session")

        # Generate summary from transcript if available
        if db_session.transcript:
            # Convert stored transcript back to VoiceSessionMessage objects
            transcript_messages = [
                VoiceSessionMessage(speaker=msg["speaker"], message=msg["message"], timestamp=datetime.fromisoformat(msg["timestamp"]))
                for msg in db_session.transcript
            ]

            summary = process_voice_transcript_for_chat(db, user_id, session_id, transcript_messages)
        else:
            # Create a basic summary if no transcript is available
            summary = f"""🎤 **Voice Therapy Session Summary**

**Session Details:**
- Therapy Type: {db_session.therapy_type}
- Duration: {db_session.duration_minutes or 'Unknown'} minutes
- Mood Before: {db_session.mood_before or 'Not recorded'}
- Mood After: {db_session.mood_after or 'Not recorded'}

**Session Summary:**
{db_session.session_summary or 'No summary available'}

---
*This summary was generated from your voice therapy session.*"""

            # Create mentor message for basic summary
            # Assuming create_mentor_message is defined elsewhere or will be added
            # For now, we'll just log the summary and the session_id
            logger.info(f"Voice session {session_id} sent to mentor chat for user {user_id} (no transcript)")

        logger.info(f"Voice session {session_id} sent to mentor chat for user {user_id}")

        return {"status": "success", "message": "Voice session sent to mentor chat", "session_id": session_id, "summary": summary}

    except Exception as e:
        logger.error(f"Error sending session to chat: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send session to chat: {str(e)}")


@router.post("/test/voice-to-chat")
async def test_voice_to_chat_integration(
    db: Session = Depends(get_db),
    access_token: str = Depends(JWTBearer()),
):
    """
    Test endpoint to verify voice-to-chat integration works.
    Creates a sample voice transcript and saves it to mentor chat.
    """
    try:
        token = decodeJWT(access_token)
        user_id = token["user_id"]

        # Create a sample transcript for testing
        sample_transcript = [
            VoiceSessionMessage(speaker="user", message="Hello, I'm feeling a bit anxious today.", timestamp=datetime.utcnow()),
            VoiceSessionMessage(
                speaker="assistant",
                message="I understand you're feeling anxious. Can you tell me more about what's causing this anxiety?",
                timestamp=datetime.utcnow(),
            ),
            VoiceSessionMessage(speaker="user", message="I have a big presentation tomorrow and I'm worried about it.", timestamp=datetime.utcnow()),
            VoiceSessionMessage(
                speaker="assistant",
                message="That's a common source of anxiety. Let's talk about some strategies to help you feel more prepared and confident.",
                timestamp=datetime.utcnow(),
            ),
        ]

        # Process the sample transcript
        session_id = f"test_session_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        summary = process_voice_transcript_for_chat(db, user_id, session_id, sample_transcript)

        return {
            "status": "success",
            "message": "Test voice-to-chat integration completed",
            "session_id": session_id,
            "messages_created": len(sample_transcript) + 1,  # +1 for completion message
            "summary": summary,
        }

    except Exception as e:
        logger.error(f"Error in test voice-to-chat integration: {e}")
        raise HTTPException(status_code=500, detail=f"Test failed: {str(e)}")


@router.post("/session/{session_id}/force-to-chat")
async def force_session_to_chat(
    session_id: str,
    db: Session = Depends(get_db),
    access_token: str = Depends(JWTBearer()),
):
    """
    Force a voice therapy session to be saved to mentor chat.
    This can be used to manually trigger the integration for existing sessions.
    """
    try:
        token = decodeJWT(access_token)
        user_id = token["user_id"]

        # Find session in database
        db_session = get_voice_therapy_session(db, session_id)
        if not db_session:
            raise HTTPException(status_code=404, detail="Session not found")

        if db_session.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to access this session")

        # Create a basic summary for the session
        basic_summary = f"""🎤 **Voice Therapy Session Completed**

**Session Details:**
- Session ID: {session_id}
- Therapy Type: {db_session.therapy_type}
- Duration: {db_session.duration_minutes or 'Unknown'} minutes
- Mood Before: {db_session.mood_before or 'Not recorded'}
- Mood After: {db_session.mood_after or 'Not recorded'}

**Session Summary:**
{db_session.session_summary or 'Voice therapy session completed successfully.'}

**Note:** This session was completed via voice interaction. The conversation has been integrated into your chat history.

---
*Voice session completed at {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}*"""

        # Create a mentor message for the session summary
        mentor_message = create_mentor_message(
            db=db, user_id=user_id, role="system", content=basic_summary, message_type="voice_session", session_id=session_id
        )

        logger.info(f"Voice session {session_id} manually saved to mentor chat for user {user_id}")

        return {
            "status": "success",
            "message": "Voice session manually saved to mentor chat",
            "session_id": session_id,
            "message_id": mentor_message.id,
            "summary": basic_summary,
        }

    except Exception as e:
        logger.error(f"Error forcing session to chat: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to force session to chat: {str(e)}")


def get_therapy_instructions(therapy_type: str) -> str:
    """Return specialized therapy instructions for OpenAI."""

    # Kevin's personal context from kevin_daily_scenarios.md
    kevin_context = """You are talking to Kevin, a 28-year-old software developer who is your regular client.

KEVIN'S PERSONAL CONTEXT:
- Lives alone in an apartment, in a 2-year relationship with Sarah
- Has strained relationship with his father, supportive relationship with his mother
- Works in a demanding tech environment with a critical boss
- Struggles with morning anxiety, work stress, and relationship communication
- Uses public transport and feels overwhelmed by crowds during commute
- Has specific daily patterns: morning anxiety (6:30-7:00 AM), work stress (9 AM-6 PM), evening decompression (7-10 PM), sleep anxiety (10:30-11 PM)
- Weekly patterns: Monday blues, Wednesday midweek slump, Friday weekend transition anxiety, Sunday scaries
- Key relationships: Father (high conflict), Boss (authority anxiety), Sarah (relationship maintenance)

IMPORTANT: You know Kevin well from previous sessions. Use his name naturally, reference his specific situations, and build on previous conversations. This is not a first-time meeting."""

    base_instructions = f"""{kevin_context}

You are a compassionate, professional therapist conducting a voice therapy session with Kevin.

Your approach should be:
- Speak in a warm, empathetic tone, using Kevin's name naturally
- Ask thoughtful follow-up questions based on his specific life patterns
- Provide evidence-based therapeutic guidance tailored to his software developer lifestyle
- Maintain appropriate professional boundaries while acknowledging your ongoing therapeutic relationship
- Be supportive and non-judgmental, especially regarding his family and work relationships
- Keep responses concise but meaningful
- Use active listening techniques and validate his emotions
- Suggest practical coping strategies that fit his daily routine and living situation
- Reference his specific triggers (morning anxiety, work stress, father calls, relationship with Sarah)
- Consider the time of day and his typical emotional state at that hour

Remember: This is a real therapy session with Kevin, who trusts you with his mental health. You have context about his life and should use it to provide personalized support."""

    therapy_specific = {
        "general": """Focus on Kevin's current life situation and provide personalized support.
        Help him explore his thoughts and feelings in a safe, non-judgmental space,
        considering his specific challenges with work, family, and relationships.""",
        "anxiety": """Specialize in anxiety management techniques tailored to Kevin's lifestyle:
        - Deep breathing exercises for morning anxiety and work stress
        - Cognitive reframing for boss criticism and family conflicts
        - Grounding exercises (5-4-3-2-1 technique) for commute overwhelm
        - Progressive muscle relaxation for shoulder tension
        - Challenging catastrophic thinking patterns about work and relationships
        - Specific strategies for his father calls and work presentations""",
        "stress": """Focus on stress reduction techniques for Kevin's software developer lifestyle:
        - Mindfulness and present-moment awareness during work hours
        - Time management strategies for his demanding tech environment
        - Boundary setting techniques with his boss and family
        - Work-life balance discussions considering his relationship with Sarah
        - Identifying stress triggers specific to his daily routine
        - Commute stress management and transition techniques""",
        "depression": """Focus on depression support considering Kevin's living situation:
        - Cognitive behavioral therapy techniques for work and relationship challenges
        - Behavioral activation strategies for his apartment living
        - Mood tracking and awareness throughout his daily schedule
        - Building support systems with Sarah and his mother
        - Self-care and routine building for living alone""",
        "sleep": """Focus on sleep hygiene and improvement for Kevin's night routine:
        - Sleep hygiene education for his apartment environment
        - Relaxation techniques for bedtime anxiety about tomorrow
        - Addressing sleep anxiety related to work presentations and family calls
        - Creating optimal sleep environments in his living space
        - Managing racing thoughts about work and relationships at night
        - Specific techniques for his 10:30-11 PM worry window""",
        "father_call_analysis": """Help Kevin process a difficult phone call through natural conversation.

Your approach:
- Be warm and genuinely interested in understanding what happened
- Listen to Kevin's experience and help him work through his feelings about the call
- Naturally explore what happened: who was involved, how it went, what was discussed, how Kevin felt, and how he responded
- Provide supportive insights when appropriate

Keep the conversation focused on helping Kevin process the call experience, but let it flow naturally rather than following a rigid script.""",
    }

    return f"{base_instructions}\n\nSpecialization: {therapy_specific.get(therapy_type, therapy_specific['general'])}"


def build_contextual_instructions(
    db: Session, user_id: int, therapy_type: str, entry_source: Optional[str] = None, context_summary: Optional[str] = None
) -> str:
    """Augment base instructions with lightweight, recent user context to reduce duplicate greetings
    and incorporate user's ongoing scenario (e.g., Kevin's daily scenarios) into the session.
    """

    # SPECIAL CASE: Father call analysis - completely override everything
    if entry_source == "father_call_analysis":
        # For father_call_analysis entry source, we always assume it's about the father
        # No need to ask "who was the call with" - skip straight to A-G matrix questions
        logger.info("Father call analysis session - assuming father call context")
        logger.info(f"Context summary: {context_summary}")

        # Focused approach for gathering A-G matrix information quickly
        conversation_guidance = """Quickly gather information about Kevin's phone call with his father for analysis purposes. Ask targeted questions to understand:

- Who did most of the talking during the call?
- How did his father behave? (was he critical, supportive, dismissive, etc.)
- What was the main topic discussed?
- How often do these types of conversations happen?
- How did Kevin feel emotionally during/after the call?
- How did Kevin respond or react?

Keep questions brief and focused. DO NOT provide therapeutic advice, coping strategies, or solutions. Just gather the facts about what happened. Kevin has dinner with Charlie coming up, so keep this session short and efficient."""

        return f"""You are an information-gathering assistant helping to collect details about Kevin's phone call with his father for later analysis.

IMPORTANT - SESSION OPENING: When the session starts, immediately greet Kevin with this exact sequence:

"Hi Kevin, let's talk about your recent call. We'll discuss the content of the call. Next, we can understand the call. Then, we'll work on responding to the problem. Finally, we'll relate this to your long-term goals. Alright Kevin, ready to dive in?"

After this opening, proceed with gathering information:

IMMEDIATE CONTEXT: {context_summary if context_summary else 'Kevin reported a difficult phone call with his father'}

{conversation_guidance}

Keep the conversation focused and brief. Once you have enough information about the call dynamics, emotions, and responses, wrap up the session quickly so Kevin can move on with his day.
"""

    base = get_therapy_instructions(therapy_type)

    # Add time-aware Kevin context
    current_time = datetime.utcnow()
    current_hour = current_time.hour
    current_weekday = current_time.strftime("%A")

    time_context = f"""
CURRENT TIME CONTEXT:
- Time: {current_hour:02d}:00 UTC, {current_weekday}
- Kevin's typical state at this hour: """

    if 6 <= current_hour < 9:
        time_context += "Morning anxiety and motivation struggles. Focus on grounding, preparation, and positive day framework."
    elif 9 <= current_hour < 12:
        time_context += "Work stress and morning standup anxiety. Support confidence building and task prioritization."
    elif 12 <= current_hour < 14:
        time_context += "Midday productivity crash. Help with energy management and refocusing strategies."
    elif 14 <= current_hour < 18:
        time_context += "Afternoon work pressure and boss interactions. Support feedback reception and boundary setting."
    elif 18 <= current_hour < 20:
        time_context += "Evening commute stress and work rumination. Help transition from work to personal time."
    elif 20 <= current_hour < 22:
        time_context += "Evening personal time with Sarah and family calls. Support relationship communication and presence."
    else:
        time_context += "Night routine and sleep anxiety. Focus on relaxation and worry management."

    # Pull a few recent chat messages, excluding the standard greeting to prevent repetition
    try:
        recent = get_mentor_messages(db, user_id, limit=10, offset=0)
    except Exception:
        recent = []

    # Extract a short context window
    recent_user_points: list[str] = []
    for m in recent:
        if getattr(m, "role", "") == "user":
            txt = (m.content or "").strip()
            if txt:
                recent_user_points.append(txt)
        if len(recent_user_points) >= 3:
            break

    recent_context = "\n".join(f"- {p[:240]}" for p in recent_user_points)

    context_block = ""
    if recent_context:
        context_block = "\n\nRECENT CONVERSATION CONTEXT (build on this, avoid repeating greetings):\n" + recent_context

    natural_guidance = (
        "\n\nGuidance for natural conversation: "
        "Kevin knows you well from previous sessions, so greet him naturally and build on your existing relationship. "
        "Reference his specific situations and daily patterns when relevant. "
        "Use active listening and provide thoughtful responses that show you understand his unique circumstances."
    )

    entry_note = ""
    if entry_source == "card_followup":
        entry_note = (
            "\n\nENTRY SOURCE: Kevin entered from a card follow-up. Acknowledge the card context briefly, "
            "ask one clarifying question about his current situation, then proceed supportively."
        )
    elif entry_source == "text_chat":
        entry_note = "\n\nENTRY SOURCE: Kevin was chatting in text; continue the same topic naturally, building on the conversation."
    elif entry_source == "father_call_analysis":
        entry_note = "\n\nThis is a father call analysis session - Kevin needs support processing a difficult call with his father."
    else:
        entry_note = "\n\nENTRY SOURCE: General voice chat. Use time context to provide relevant support."

    context_line = f"\n\nIMMEDIATE CONTEXT: {context_summary}" if context_summary else ""

    # For father call analysis, override everything else and focus only on the call, but allow a closing redirect to dinner with Charlie
    # This father_call_analysis case is handled above, this should never execute
    if entry_source == "father_call_analysis":
        logger.warning("Unexpected fallthrough to general father_call_analysis handler - this should not happen")
        return f"{base}\n\nHelp Kevin process a difficult phone call naturally and supportively."

    return base + time_context + context_block + natural_guidance + entry_note + context_line


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
                    "recommended_actions": {"type": "string", "description": "Suggested next steps or homework"},
                },
                "required": ["key_topics"],
            },
        },
        {
            "type": "function",
            "name": "breathing_exercise",
            "description": "Guide the user through a breathing exercise",
            "parameters": {
                "type": "object",
                "properties": {
                    "duration": {"type": "integer", "description": "Duration in seconds"},
                    "technique": {"type": "string", "description": "Type of breathing technique"},
                },
            },
        },
    ]


async def _analyze_father_call_transcript(db: Session, user_id: int, session_id: str, transcript: List[VoiceSessionMessage]) -> Optional[Dict]:
    """Analyze father call transcript and create analysis summary."""
    try:
        from app.postgres.crud.gpt import create_mentor_message
        from app.services.father_call_analyzer import FatherCallAnalyzer

        logger.info(f"Starting father call analysis for session {session_id} with {len(transcript)} messages")

        # Debug: Show transcript summary
        user_msgs = [msg.message for msg in transcript if msg.speaker == "user"]
        ai_msgs = [msg.message for msg in transcript if msg.speaker == "assistant"]
        logger.info(f"Transcript summary: {len(user_msgs)} user messages, {len(ai_msgs)} AI messages")
        logger.info(f"Sample user content: {str(user_msgs[:3])[:200]}")

        analyzer = FatherCallAnalyzer()
        analysis_result = analyzer.analyze_transcript(transcript)

        logger.info(f"Analysis result: {bool(analysis_result)}, complete: {analysis_result.get('analysis_complete') if analysis_result else False}")

        if analysis_result and analysis_result.get("analysis_complete"):
            # Create analysis summary for mentor chat
            matrix_text_lines = []
            for cat, val in analysis_result["matrix_selections"].items():
                # Handle both single values and lists (multi-select categories)
                if isinstance(val, list):
                    for v in val:
                        label = analyzer.MATRIX_CATEGORIES[cat].get(v, f"Unknown {cat}{v}")
                        matrix_text_lines.append(f"**{cat}{v}**: {label}")
                else:
                    label = analyzer.MATRIX_CATEGORIES[cat].get(val, f"Unknown {cat}{val}")
                    matrix_text_lines.append(f"**{cat}{val}**: {label}")
            matrix_text = "\n".join(matrix_text_lines)

            suggestions_text = "\n".join([f"• **{s['name']}**: {s['description']}" for s in analysis_result["suggestions"][:2]])
            analysis_summary = f"""🔍 **Father Call Analysis Complete**

**Matrix Classifications:**
{matrix_text}

**Key Insights:**
{analysis_result['conversation_summary']}

**Therapeutic Suggestions:**
{suggestions_text}

Would you like to add a follow-up card for this evening? Tap "Add to plan" to schedule "Follow up on bad call with father" after dinner so we can review your A–G results and plan next steps.

---
*This analysis helps identify patterns in family communication and suggests targeted therapeutic approaches.*"""

            # Save analysis to mentor chat
            create_mentor_message(
                db=db, user_id=user_id, role="assistant", content=analysis_summary, message_type="father_call_analysis", session_id=session_id
            )

            return analysis_result

        return None

    except Exception as e:
        logger.error(f"Error analyzing father call transcript: {e}")
        logger.error("Exception details: ", exc_info=True)
        return None


async def _create_father_call_reflection_card(db: Session, user_id: int, session_id: str, analysis_result: Dict):
    """Create a follow-up reflection item: add a card to the user's plan (9 PM) with embedded A–G analysis,
    and post a short chat note."""
    try:
        from datetime import timedelta

        from app.postgres.crud.card import create_card_details, create_user_card
        from app.postgres.schema.card import (
            CardType,
            CategoryEnum,
            SpecialActions,
            TimeOfDay,
        )

        # 1) Create a special CardDetail with matrix data embedded
        logger.info(f"Creating CardDetail for father call reflection, user {user_id}, session {session_id}")
        reflection_card_detail = create_card_details(
            db=db,
            card_type=CardType.suggestion,
            title="Follow up on bad call with father",
            category=CategoryEnum.SELF_DEVELOPMENT,
            details={
                "session_id": session_id,
                "matrix_analysis": analysis_result["matrix_selections"],
                "conversation_summary": analysis_result.get("conversation_summary", ""),
                "suggestions": analysis_result.get("suggestions", []),
                "rationales": analysis_result.get("rationales", {}),
                "reflection_type": "father_call",
            },
            description="Review your A–G analysis and discuss strategies for future calls",
            duration=timedelta(minutes=30),
            tod=TimeOfDay.EVENING,
            special_card_action=SpecialActions.NONE,
        )
        logger.info(f"Created CardDetail with ID: {reflection_card_detail.id}")

        # 2) Schedule after the last evening card (typically "Dinner with Charlie")
        from app.postgres.crud.card import retrieve_cards

        today = datetime.now().date()
        start_of_day = datetime.combine(today, datetime.min.time())
        end_of_day = datetime.combine(today, datetime.max.time())

        logger.info(f"Retrieving cards for today ({today}) to schedule reflection")
        # Get today's cards sorted by time
        today_cards = retrieve_cards(db, user_id, start_of_day, end_of_day, load_card_details=True)
        logger.info(f"Found {len(today_cards)} cards for today")

        # Find the last evening card (after 6 PM)
        evening_cards = [card for card in today_cards if card.time.hour >= 18]
        logger.info(f"Found {len(evening_cards)} evening cards")

        if evening_cards:
            # Schedule 30 minutes after the last evening card ends
            last_card = max(evening_cards, key=lambda x: x.time)
            logger.info(f"Last evening card: {last_card.card_details.title} at {last_card.time}")
            card_end_time = last_card.time + last_card.card_details.duration
            follow_up_time = card_end_time + timedelta(minutes=30)
            logger.info(f"Scheduling reflection at {follow_up_time} (30 min after {last_card.card_details.title})")
        else:
            # Fallback to 9 PM if no evening cards found
            follow_up_time = datetime.now().replace(hour=21, minute=0, second=0, microsecond=0)
            logger.info(f"No evening cards found, scheduling at 9 PM: {follow_up_time}")

        # If the calculated time is in the past, schedule for tomorrow
        if follow_up_time <= datetime.now():
            follow_up_time = follow_up_time + timedelta(days=1)
            logger.info(f"Time was in past, moved to tomorrow: {follow_up_time}")

        logger.info("Creating UserCard for reflection")
        user_card = create_user_card(
            db=db,
            user_id=user_id,
            card_details_id=reflection_card_detail.id,
            card={
                "time": follow_up_time,
                "recurrence": None,
                "location": "Home - Quiet space",
            },
        )

        if user_card:
            logger.info(f"Created UserCard with ID: {user_card.card_id} at {user_card.time}")
        else:
            logger.error("Failed to create UserCard - create_user_card returned None")
            raise Exception("Failed to create UserCard")

        # 3) Post a short chat note so the user knows it was scheduled
        from app.postgres.crud.gpt import create_mentor_message

        chat_note = (
            "📝 Added 'Follow up on bad call with father' to your evening plan (after dinner). "
            "Tap the card later to view the full A–G matrix analysis and summary."
        )
        create_mentor_message(
            db=db,
            user_id=user_id,
            role="assistant",
            content=chat_note,
            message_type="activity_suggestion",
            session_id=session_id,
        )

        return True

    except Exception as e:
        logger.error(f"Error creating father call reflection card: {e}")
        logger.error("Full exception details: ", exc_info=True)
        return False


@router.post("/session/{session_id}/analyze-father-call", response_model=FatherCallAnalysisResponse)
async def analyze_father_call_session(
    session_id: str,
    request: FatherCallAnalysisRequest,
    db: Session = Depends(get_db),
    access_token: str = Depends(JWTBearer()),
):
    """
    Analyze a completed voice therapy session for father call using A-G matrix classification.
    This endpoint processes the transcript and provides therapeutic insights.
    """
    try:
        token = decodeJWT(access_token)
        user_id = token["user_id"]

        # Find session in database
        db_session = get_voice_therapy_session(db, session_id)
        if not db_session:
            raise HTTPException(status_code=404, detail="Session not found")

        if db_session.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to access this session")

        # Check if session has transcript
        if not db_session.transcript:
            raise HTTPException(status_code=400, detail="Session has no transcript to analyze")

        # Convert stored transcript back to VoiceSessionMessage objects
        transcript_messages = [
            VoiceSessionMessage(
                speaker=msg["speaker"],
                message=msg["message"],
                timestamp=datetime.fromisoformat(msg["timestamp"]) if msg.get("timestamp") else datetime.utcnow(),
            )
            for msg in db_session.transcript
        ]

        # Analyze the transcript
        from app.services.father_call_analyzer import FatherCallAnalyzer

        analyzer = FatherCallAnalyzer()
        analysis_result = analyzer.analyze_transcript(transcript_messages)

        # Convert analysis result to response format
        matrix_selections = []
        for category, value in analysis_result["matrix_selections"].items():
            # Handle both single values and lists (multi-select categories)
            if isinstance(value, list):
                for v in value:
                    label = analyzer.MATRIX_CATEGORIES[category].get(v, f"Unknown {category}{v}")
                    rationale = analysis_result["rationales"].get(category, "Selected based on conversation analysis")
                    matrix_selections.append(MatrixSelection(category=category, value=v, label=label, rationale=rationale))
            else:
                label = analyzer.MATRIX_CATEGORIES[category].get(value, f"Unknown {category}{value}")
                rationale = analysis_result["rationales"].get(category, "Selected based on conversation analysis")
                matrix_selections.append(MatrixSelection(category=category, value=value, label=label, rationale=rationale))

        # Convert suggestions
        suggestions = [
            AnalysisSuggestion(
                id=s["id"],
                category=s["category"],
                name=s["name"],
                description=s["description"],
                triggered_by=s["triggered_by"],
                rationale=s["rationale"],
                recommended_actions=s["recommended_actions"],
            )
            for s in analysis_result["suggestions"]
        ]

        logger.info(f"Father call analysis completed for session {session_id}")

        # Create analysis summary for chat integration
        analysis_summary = f"""🔍 **Father Call Analysis Complete**

**Session Analysis:**
- Session Duration: {db_session.duration_minutes or 'Unknown'} minutes
- Analysis Type: A-G Matrix Classification

**Matrix Selections:**
{chr(10).join([f'- **{sel.category}{sel.value}**: {sel.label}' for sel in matrix_selections])}

**Key Insights:**
{analysis_result['conversation_summary']}

**Therapeutic Suggestions:**
{chr(10).join([f'• **{s.name}**: {s.description}' for s in suggestions[:2]])}

---
*This analysis helps identify patterns in family communication and suggests targeted therapeutic approaches.*"""

        # Save analysis summary to mentor chat
        try:
            create_mentor_message(
                db=db, user_id=user_id, role="assistant", content=analysis_summary, message_type="father_call_analysis", session_id=session_id
            )
            logger.info(f"Father call analysis saved to mentor chat for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to save analysis to chat: {e}")

        return FatherCallAnalysisResponse(
            session_id=session_id,
            matrix_selections=matrix_selections,
            conversation_summary=analysis_result["conversation_summary"],
            suggestions=suggestions,
            analysis_complete=analysis_result["analysis_complete"],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing father call session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to analyze session: {str(e)}")


@router.post("/session/{session_id}/schedule-father-reflection")
async def schedule_father_reflection(
    session_id: str,
    db: Session = Depends(get_db),
    access_token: str = Depends(JWTBearer()),
):
    """
    Schedule a follow-up reflection at 21:00 for a father call analysis session.
    If analysis is not cached, it will be recomputed from the stored transcript.
    """
    try:
        token = decodeJWT(access_token)
        user_id = token["user_id"]

        db_session = get_voice_therapy_session(db, session_id)
        if not db_session:
            raise HTTPException(status_code=404, detail="Session not found")
        if db_session.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to access this session")

        # Build transcript messages if available
        transcript_messages = None
        if db_session.transcript:
            transcript_messages = [
                VoiceSessionMessage(
                    speaker=msg["speaker"],
                    message=msg["message"],
                    timestamp=datetime.fromisoformat(msg["timestamp"]) if msg.get("timestamp") else datetime.utcnow(),
                )
                for msg in db_session.transcript
            ]

        if not transcript_messages:
            raise HTTPException(status_code=400, detail="No transcript available to analyze")

        analysis_result = await _analyze_father_call_transcript(db, user_id, session_id, transcript_messages)
        if not analysis_result:
            raise HTTPException(
                status_code=400,
                detail="Unable to analyze transcript - conversation does not contain sufficient father call discussion for reflection card creation",
            )

        if not analysis_result.get("analysis_complete", False):
            raise HTTPException(status_code=400, detail="Father call analysis incomplete - insufficient conversation content for reflection card")

        ok = await _create_father_call_reflection_card(db, user_id, session_id, analysis_result)
        if not ok:
            raise HTTPException(status_code=500, detail="Analysis completed successfully but failed to create reflection card - please try again")

        return {"status": "scheduled", "session_id": session_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error scheduling father reflection for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to schedule reflection: {str(e)}")
