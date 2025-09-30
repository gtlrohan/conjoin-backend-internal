import logging
import os
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.middleware.jwt import JWTBearer, decodeJWT
from app.postgres.database import get_db
from app.postgres.crud.gpt import get_mentor_messages, get_recent_voice_sessions
from app.services.openAI import ask_gpt
from app.postgres.models.gpt import GPTRequest

router = APIRouter(prefix="/gpt", tags=["Prompt GPT's"])

# initiates logger
log = logging.getLogger(__name__)


def get_kevin_current_activity_context(db: Session, user_id: int, current_time: Optional[datetime] = None) -> str:
	"""
	Get Kevin's current activity context and complete daily plan
	This helps the AI understand what Kevin is currently doing AND his full schedule for the day
	
	Args:
		db: Database session
		user_id: User ID
		current_time: Current time to use for context (defaults to UTC now if not provided)
	"""
	try:
		from app.postgres.crud.card import retrieve_cards
		from app.postgres.crud.user import retrieve_user_by_id
		
		# Use provided current_time or fall back to UTC now
		now = current_time if current_time else datetime.utcnow()
		start_of_day = datetime(now.year, now.month, now.day, 0, 0, 0)
		end_of_day = datetime(now.year, now.month, now.day, 23, 59, 59)
		
		# Get all cards for today
		cards = retrieve_cards(db, user_id, start_of_day, end_of_day, load_card_details=True)
		
		if not cards:
			return "\n\nTODAY'S PLAN: No scheduled activities found."
		
		# Sort cards by time for better organization
		cards.sort(key=lambda x: x.time)
		
		# Build concise daily plan summary (one line per card)
		plan_summary_lines: List[str] = []
		for c in cards:
			time_str = c.time.strftime("%H:%M")
			# duration minutes (safe for timedelta)
			try:
				minutes = int(c.duration.total_seconds() // 60)
			except Exception:
				minutes = max(1, (c.duration.seconds // 60) if hasattr(c, "duration") else 30)
			title = getattr(c.card_details, "title", "Activity")
			location_piece = f" @ {c.location}" if getattr(c, "location", None) else ""
			plan_summary_lines.append(f"- {time_str} — {title} ({minutes}m){location_piece}")
		
		concise_plan = "\n".join(plan_summary_lines)
		
		# Build complete daily plan overview (kept for richer context, not for output)
		daily_plan = "\n\nKEVIN'S COMPLETE DAILY PLAN:\n"
		for i, card in enumerate(cards, 1):
			time_str = card.time.strftime("%H:%M")
			minutes = int(card.duration.total_seconds() // 60) if hasattr(card, "duration") else 30
			# Determine status
			card_start = card.time
			card_end = card_start + card.duration
			if now >= card_start and now <= card_end:
				status = "IN PROGRESS"
			elif now > card_end:
				status = "COMPLETED"
			else:
				status = "UPCOMING"
			daily_plan += f"{i}. {time_str} - {card.card_details.title} [{minutes}m] · {status}\n"
		
		# Find the current/ongoing or next upcoming card
		current_card = None
		for card in cards:
			card_start = card.time
			card_end = card_start + card.duration
			if now >= card_start and now <= card_end:
				current_card = card
				break
		
		if not current_card:
			upcoming_cards = [c for c in cards if c.time > now]
			if upcoming_cards:
				upcoming_cards.sort(key=lambda x: x.time)
				current_card = upcoming_cards[0]
		
		# Build current activity context
		if current_card:
			time_context = f"Demo Time: {now.strftime('%H:%M')}" if current_time else f"Real Time: {now.strftime('%H:%M')}"
			duration_min = int(current_card.duration.total_seconds() // 60) if hasattr(current_card, "duration") else 30
			current_context = f"""
TODAY'S PLAN (concise):
{concise_plan}

CURRENT ACTIVITY CONTEXT:
- {time_context}
- Activity: {current_card.card_details.title}
- Starts: {current_card.time.strftime('%H:%M')} · Duration: {duration_min}m
- Location: {current_card.location or 'Not specified'}
- Status: {'In Progress' if now >= current_card.time and now <= current_card.time + current_card.duration else 'Upcoming'}
"""
		else:
			current_context = f"""
TODAY'S PLAN (concise):
{concise_plan}

CURRENT ACTIVITY: No current or upcoming activities found.
"""
		
		# Combine daily plan (rich) with concise and current context
		return current_context + "\n" + daily_plan
			
	except Exception as e:
		log.error(f"Error getting current activity context: {e}")
		return "\n\nTODAY'S PLAN: Unable to determine."


def _detect_current_activity_query(text: str) -> bool:
    if not text:
        return False
    t = text.lower().strip()
    return (
        ("activity" in t and "right now" in t)
        or ("current" in t and "activity" in t)
        or t in {
            "what's my current activity",
            "what is my current activity",
            "what activity is right now",
            "what activity is it right now",
            "what activity do i have right now",
            "what am i doing right now",
        }
    )


def _detect_plan_today_query(text: str) -> bool:
    if not text:
        return False
    t = text.lower().strip()
    return (
        ("plan" in t and ("today" in t or "for today" in t))
        or t in {"what is my plan today", "whats my plan today", "my plan today"}
    )


def _get_current_activity_title(db: Session, user_id: int, current_time: Optional[datetime] = None) -> str:
    from app.postgres.crud.card import retrieve_cards

    now = current_time if current_time else datetime.utcnow()
    start_of_day = datetime(now.year, now.month, now.day, 0, 0, 0)
    end_of_day = datetime(now.year, now.month, now.day, 23, 59, 59)

    cards = retrieve_cards(db, user_id, start_of_day, end_of_day, load_card_details=True)
    if not cards:
        return "No current or upcoming activity."

    # Find in-progress; else next upcoming
    for card in cards:
        if card.time <= now <= card.time + card.card_details.duration:
            return getattr(card.card_details, "title", "Activity")

    upcoming = [c for c in cards if c.time > now]
    if not upcoming:
        return "No current or upcoming activity."
    upcoming.sort(key=lambda x: x.time)
    return getattr(upcoming[0].card_details, "title", "Activity")


def _build_concise_plan_list(db: Session, user_id: int, current_time: Optional[datetime] = None) -> str:
    from app.postgres.crud.card import retrieve_cards

    now = current_time if current_time else datetime.utcnow()
    start_of_day = datetime(now.year, now.month, now.day, 0, 0, 0)
    end_of_day = datetime(now.year, now.month, now.day, 23, 59, 59)

    cards = retrieve_cards(db, user_id, start_of_day, end_of_day, load_card_details=True)
    if not cards:
        return "No scheduled activities found."

    cards.sort(key=lambda x: x.time)
    lines: List[str] = []
    for c in cards:
        time_str = c.time.strftime("%H:%M")
        title = getattr(c.card_details, "title", "Activity")
        lines.append(f"- {time_str} — {title}")
    return "\n".join(lines)


@router.post("/openAI/chatGPT")
async def prompt_chatGPT(
    body: GPTRequest, 
    access_token: str = Depends(JWTBearer()),
    db: Session = Depends(get_db)
):
    """
    Enhanced GPT endpoint with voice therapy session awareness
    """
    try:
        # Get user context
        token = decodeJWT(access_token)
        user_id = token["user_id"]
        
        # Get recent voice therapy context
        recent_voice_sessions = get_recent_voice_sessions(db, user_id, limit=3)
        
        # Lightweight intent overrides for deterministic answers
        last_user_text = next((m.content for m in reversed(body.messages) if m.role == "user"), "")
        if _detect_current_activity_query(last_user_text):
            return _get_current_activity_title(db, user_id, body.current_time)
        if _detect_plan_today_query(last_user_text):
            return _build_concise_plan_list(db, user_id, body.current_time)

        # Read Kevin's scenarios (existing code)
        markdown_file_path = Path("kevin_daily_scenarios.md")
        kevin_scenarios = ""
        
        if markdown_file_path.exists():
            with open(markdown_file_path, 'r', encoding='utf-8') as file:
                kevin_scenarios = file.read()
        
        # Build voice therapy context
        voice_context = ""
        if recent_voice_sessions:
            voice_context = "\n\nRECENT VOICE THERAPY SESSIONS:\n"
            for session in recent_voice_sessions:
                voice_context += f"- {session.timestamp.strftime('%Y-%m-%d %H:%M')}: {session.content[:200]}...\n"
        
        # Get Kevin's current activity context
        current_activity_context = get_kevin_current_activity_context(db, user_id, body.current_time)
        
        # Enhanced system prompt that acknowledges voice therapy sessions and current activity
        enhanced_system_prompt = f"""You are Kevin's trusted AI mentor and daily companion. You know Kevin's background, patterns, preferences, and current schedule. You are warm, concise, and practical. Speak naturally like a supportive coach who remembers context across the day.

{kevin_scenarios}

{current_activity_context}

Your style:
- When Kevin asks about his plan, share his scheduled activities clearly and concisely
- Keep responses helpful and personalized, like someone who knows him well  
- Reference what's coming up next and offer practical support
- Be empathetic about any challenges or successes

IMPORTANT: Kevin also participates in voice therapy sessions where he talks through his feelings and challenges in real-time. These conversations provide additional context about his emotional state and current situation.{voice_context}

When you see transcripts from voice therapy sessions in the chat, use them to understand Kevin's emotional state, reference specific topics he discussed, and build continuity between voice sessions and text conversations.

Provide personalized, empathetic guidance that recognizes Kevin's current situation, acknowledges what he's doing, references his schedule when relevant, and offers practical support for his anxiety, relationships, and overall wellbeing. Build on insights from voice therapy sessions when appropriate.

Keep answers short and useful. Avoid repeating the schedule if Kevin already saw it in the immediately prior message unless explicitly asked to repeat.

{body.system_prompt}"""
        
        # Call the GPT service with the enhanced system prompt
        original_response, tokens = await ask_gpt(body.messages, enhanced_system_prompt, body.gpt_model)
        return original_response

    except HTTPException as e:
        raise e
    except Exception as e:
        log.error(f"Error in prompt_chatGPT: {str(e)}")
        # Fallback to original behavior on error
        try:
            original_response, tokens = await ask_gpt(body.messages, body.system_prompt, body.gpt_model)
            return original_response
        except Exception as fallback_error:
            log.error(f"Fallback error in prompt_chatGPT: {str(fallback_error)}")
            raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/openAI/kevin_scenario")
async def gpt_kevin_scenario(
    body: GPTRequest,
    access_token: str = Depends(JWTBearer()),
    db: Session = Depends(get_db)
):
    """
    Makes an API call to chatGPT with Kevin's daily scenario context incorporated into the system prompt
    """
    try:
        # Get user ID from token
        token = decodeJWT(access_token)
        user_id = token["user_id"]
        
        # Lightweight intent overrides for deterministic answers
        last_user_text = next((m.content for m in reversed(body.messages) if m.role == "user"), "")
        if _detect_current_activity_query(last_user_text):
            return _get_current_activity_title(db, user_id, body.current_time)
        if _detect_plan_today_query(last_user_text):
            return _build_concise_plan_list(db, user_id, body.current_time)

        # Read the markdown file with Kevin's daily scenarios
        markdown_file_path = Path("kevin_daily_scenarios.md")
        
        if not markdown_file_path.exists():
            raise HTTPException(
                status_code=404, 
                detail="Kevin's daily scenarios markdown file not found"
            )
        
        with open(markdown_file_path, 'r', encoding='utf-8') as file:
            kevin_scenarios = file.read()
        
        # Get Kevin's current activity context
        current_activity_context = get_kevin_current_activity_context(db, user_id, body.current_time)
        
        # Create enhanced system prompt that includes Kevin's scenarios and current activity
        enhanced_system_prompt = f"""You are an AI digital mentor specifically designed to help Kevin, a 28-year-old software developer dealing with anxiety, work stress, and relationship challenges.

{kevin_scenarios}

{current_activity_context}

IMPORTANT INSTRUCTIONS FOR USING KEVIN'S DAILY PLAN:
- When Kevin asks about his plan for today, ALWAYS reference the specific activities from his daily schedule above
- Use the exact times, locations, and activity names from his plan
- Acknowledge the current status of each activity (completed, in progress, upcoming)
- Provide specific guidance based on what's coming next in his schedule
- If activities are completed, celebrate his progress
- If activities are upcoming, help him prepare mentally and practically
- If he's currently in an activity, focus on supporting that specific task

Based on the detailed scenarios above and Kevin's daily plan, provide personalized, empathetic guidance that:
1. Recognizes the specific time, location, and emotional context of Kevin's situation
2. Acknowledges what Kevin is currently doing or about to do
3. References his specific daily schedule when discussing plans
4. Offers practical coping strategies and techniques relevant to his current activity
5. Helps Kevin build confidence and resilience
6. Supports healthy communication in his relationships
7. Provides grounding techniques for anxiety and stress management

Always consider the current time, Kevin's emotional state, his current/upcoming activity, his full daily schedule, and the specific scenario he might be facing when providing guidance."""
        
        # Call the GPT service with the enhanced system prompt
        original_response, tokens = await ask_gpt(body.messages, enhanced_system_prompt, body.gpt_model)
        return original_response

    except HTTPException as e:
        raise e  # Reraise the HTTPException
    except Exception as e:
        log.error(f"Error in gpt_kevin_scenario: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/openAI/generic")
async def prompt_generic_chatGPT(body: GPTRequest, access_token: str = Depends(JWTBearer())):
    """
    Makes a API call to chatGPT with generic system prompt (no Kevin scenarios)
    """
    try:
        original_response, tokens = await ask_gpt(body.messages, body.system_prompt, body.gpt_model)
        return original_response

    except HTTPException as e:
        raise e  # Reraise the HTTPException
