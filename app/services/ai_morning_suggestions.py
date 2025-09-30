"""
AI Morning Orientation Suggestions Service
Provides personalized daily suggestions for Kevin using GPT-4o
"""
import json
import logging
import random
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, List
from openai import OpenAI
from sqlalchemy.orm import Session

from app.constants import OPENAI_API_KEY
from app.postgres.crud.card import retrieve_all_card_details, create_card_details
from app.postgres.schema.card import CardDetail, TimeOfDay
from app.postgres.models.card import SpecialActions, CategoryEnum

logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# Kevin's AI Mentor Master Prompt (Modified for 5 suggestions)
KEVIN_MENTOR_PROMPT = """# Kevin's AI Digital Mentor - Master Prompt

## Context
You are Kevin's personal AI mentor. Kevin is a 28-year-old software developer who struggles with anxiety, work stress, and relationship balance. You provide exactly 5 personalized daily suggestions based on his cognitive fingerprint and current state.

## Kevin's Profile
- **Age**: 28, Software Developer
- **Relationship**: Sarah (2 years)
- **Key Challenges**: Morning anxiety, work confidence, boss relationships, family tensions (especially father), sleep anxiety
- **Strengths**: Technical skills, supportive mother, committed relationship

## Input Parameters
**Cognitive Fingerprint (1-10 scale):**
- work_anxiety: {work_anxiety}
- social_anxiety: {social_anxiety} 
- family_anxiety: {family_anxiety}
- eating_anxiety: {eating_anxiety}
- sleeping_anxiety: {sleeping_anxiety}

**Daily State (1-10 scale):**
- energy_level: {energy_level}
- stress_level: {stress_level}

**Context:**
- current_time: {current_time}
- day_of_week: {day_of_week}

## Decision Matrix Rules

### Energy Level Interpretation:
- 1-3: Very Low (gentle, minimal effort suggestions)
- 4-6: Moderate (balanced, achievable suggestions)  
- 7-10: High (challenging, proactive suggestions)

### Stress Level Interpretation:
- 1-3: Low Stress (growth-focused suggestions)
- 4-6: Moderate Stress (balance-focused suggestions)
- 7-10: High Stress (calming, grounding suggestions)

### Anxiety Level Interpretation (per domain):
- 1-3: Low (maintenance suggestions)
- 4-6: Moderate (preventive suggestions)
- 7-10: High (intervention suggestions)

## Time-Based Context

### Morning (6:00-9:00 AM):
- Focus: Morning routine, work preparation, anxiety management
- Kevin's Patterns: Morning anxiety spikes, breakfast stress, commute overwhelm

### Work Hours (9:00-18:00):
- Focus: Confidence building, productivity, boss interactions
- Kevin's Patterns: Standup anxiety, midday crashes, criticism sensitivity

### Evening (18:00-22:00):
- Focus: Relationship time, family communication, stress processing
- Kevin's Patterns: Work rumination, Sarah connection, family calls

### Night (22:00-23:00):
- Focus: Sleep preparation, worry management
- Kevin's Patterns: Sleep anxiety, next-day worry

## Weekly Patterns:
- **Monday**: Extra work anxiety (week ahead)
- **Wednesday**: Midweek energy dip
- **Friday**: Weekend transition anxiety
- **Sunday**: Sunday scaries (Monday anticipation)

## Suggestion Categories

### Work-Related:
- Confidence building exercises
- Boss interaction preparation
- Productivity techniques
- Stress management

### Relationship-Related:
- Communication with Sarah
- Family interaction strategies
- Boundary setting
- Presence practices

### Self-Care:
- Anxiety management techniques
- Energy regulation
- Sleep preparation
- Mindfulness practices

### Physical Well-being:
- Breathing exercises
- Movement/exercise
- Nutrition guidance
- Relaxation techniques

## Core Directive
Based on Kevin's current cognitive fingerprint, daily state, and time context, provide EXACTLY 5 suggestions that are:

1. **Specific and Actionable**: Clear, concrete steps Kevin can take
2. **Contextually Relevant**: Appropriate for his current situation and time
3. **Personalized**: Tailored to his known patterns and challenges
4. **Balanced**: Address different aspects of his wellbeing
5. **Realistic**: Achievable given his current energy and stress levels

## Response Format
Provide suggestions in this JSON format only:

{{
  "suggestion_1": {{
    "title": "Brief title (max 30 characters)",
    "category": "Sleep|Exercise|Nutrition|Mood|Social|Work|Self development"
  }},
  "suggestion_2": {{
    "title": "Brief title (max 30 characters)",
    "category": "Sleep|Exercise|Nutrition|Mood|Social|Work|Self development"
  }},
  "suggestion_3": {{
    "title": "Brief title (max 30 characters)",
    "category": "Sleep|Exercise|Nutrition|Mood|Social|Work|Self development"
  }},
  "suggestion_4": {{
    "title": "Brief title (max 30 characters)",
    "category": "Sleep|Exercise|Nutrition|Mood|Social|Work|Self development"
  }},
  "suggestion_5": {{
    "title": "Brief title (max 30 characters)",
    "category": "Sleep|Exercise|Nutrition|Mood|Social|Work|Self development"
  }}
}}

## Decision Logic Priority:

1. **High Stress (7-10)**: Prioritize calming, grounding suggestions regardless of other factors
2. **Low Energy (1-3)**: Gentle, minimal-effort suggestions only
3. **High Anxiety in Multiple Domains**: Focus on immediate anxiety management
4. **Morning Context**: Always include morning routine or work preparation element
5. **Evening Context**: Include relationship or sleep preparation element
6. **Work Hours**: Focus on professional confidence and productivity

## Advanced Combination Handling:

### High Stress + Low Energy:
- Gentle breathing exercise
- Simple grounding technique

### High Stress + High Energy:
- Physical stress release (walk, exercise)
- Proactive stress management

### Low Stress + High Energy:
- Growth-focused activities
- Relationship investment

### High Work Anxiety + Morning:
- Work confidence building
- Success visualization

### High Family Anxiety + Evening:
- Communication preparation
- Boundary setting practice

### High Sleep Anxiety + Night:
- Sleep hygiene routine
- Worry journaling

## Quality Checks:
- All 5 suggestions must be different from each other
- Each suggestion should take 5-20 minutes to complete
- Language should be encouraging but not overly positive
- Include specific techniques Kevin can remember and repeat
- Consider his relationship with Sarah and family dynamics
- Respect his software developer schedule and work demands
- Ensure variety across different categories (work, relationship, self-care, physical)

## Example Simple Suggestions:
- "fruit drink" (Nutrition)
- "morning affirmation" (Mood)
- "quick walk" (Exercise)
- "text Sarah" (Social)
- "work prep review" (Work)

Keep titles SHORT and match the style of existing activity cards in the system.

Generate exactly 5 suggestions now based on the provided inputs. Respond ONLY with the JSON format specified above."""


def get_time_period(hour: int) -> str:
    """Determine time period based on hour"""
    if 6 <= hour < 9:
        return "Morning"
    elif 9 <= hour < 18:
        return "Work Hours"
    elif 18 <= hour < 22:
        return "Evening"
    else:
        return "Night"


def get_kevin_ai_suggestions(
    db: Session,
    user_id: int,
    cognitive_fingerprint: Dict[str, float], 
    daily_state: Dict[str, float]
) -> Tuple[Optional[List[Dict]], Optional[str]]:
    """
    Get personalized suggestions for Kevin using GPT-4o
    
    Args:
        cognitive_fingerprint: Dict with anxiety levels for 5 domains
        daily_state: Dict with energy_level and stress_level
    
    Returns:
        Tuple of (suggestions_dict, error_message)
    """
    try:
        # Get current time context
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        day_of_week = now.strftime("%A")
        time_period = get_time_period(now.hour)
        
        # Format the prompt with input values
        formatted_prompt = KEVIN_MENTOR_PROMPT.format(
            work_anxiety=cognitive_fingerprint['work_anxiety'],
            social_anxiety=cognitive_fingerprint['social_anxiety'],
            family_anxiety=cognitive_fingerprint['family_anxiety'],
            eating_anxiety=cognitive_fingerprint['eating_anxiety'],
            sleeping_anxiety=cognitive_fingerprint['sleeping_anxiety'],
            energy_level=daily_state['energy_level'],
            stress_level=daily_state['stress_level'],
            current_time=f"{current_time} ({time_period})",
            day_of_week=day_of_week
        )
        print("=" * 50)
        print("FORMED PROMPT:")
        print(formatted_prompt)
        print("=" * 50)
        
        # Call GPT-4o
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system", 
                    "content": "You are Kevin's AI mentor. Respond ONLY with valid JSON as specified in the prompt."
                },
                {
                    "role": "user", 
                    "content": formatted_prompt
                }
            ],
            temperature=0.5,
            max_tokens=800  # Increased for 5 suggestions
        )
        
        # Parse the response
        ai_response = response.choices[0].message.content.strip()
        
        # Print the raw AI response for debugging
        print("=" * 50)
        print("AI RAW RESPONSE:")
        print(ai_response)
        print("=" * 50)
        
        # Clean and parse JSON response
        try:
            # Remove markdown code blocks if present
            cleaned_response = ai_response.strip()
            if cleaned_response.startswith('```json'):
                cleaned_response = cleaned_response[7:]  # Remove ```json
            if cleaned_response.startswith('```'):
                cleaned_response = cleaned_response[3:]   # Remove ```
            if cleaned_response.endswith('```'):
                cleaned_response = cleaned_response[:-3]  # Remove ending ```
            
            cleaned_response = cleaned_response.strip()
            
            suggestions = json.loads(cleaned_response)
            
            # Validate that we have exactly 5 suggestions
            expected_keys = [f"suggestion_{i}" for i in range(1, 6)]
            if not all(key in suggestions for key in expected_keys):
                logger.error(f"AI response missing expected suggestions: {suggestions.keys()}")
                return None, "AI response missing required suggestions"
            
            # Convert AI suggestions to card format
            card_suggestions = convert_ai_to_card_format(
                db, user_id, suggestions
            )
            
            return card_suggestions, None
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {ai_response}")
            logger.error(f"JSON parse error: {str(e)}")
            return None, "Failed to parse AI response"
            
    except Exception as e:
        logger.error(f"Error calling OpenAI API: {str(e)}")
        return None, f"AI service error: {str(e)}"


def convert_ai_to_card_format(
    db: Session, 
    user_id: int, 
    ai_suggestions: Dict
) -> List[Dict]:
    """
    Convert AI suggestions to the same format as existing morning-orientation API
    """
    try:
        formatted_suggestions = []
        # Use FIXED date for V1 (same as existing APIs)
        fixed_date = datetime(2025, 1, 17).date()  # Fixed date like existing APIs
        base_datetime = datetime.combine(fixed_date, datetime.min.time())
        
        # Process each AI suggestion
        for i, (key, suggestion) in enumerate(ai_suggestions.items()):
            ai_title = suggestion.get('title', '')
            ai_category_raw = suggestion.get('category', 'Mood')
            
            # Map AI categories to database enum values (uppercase)
            category_mapping = {
                'Exercise': 'EXERCISE',
                'Nutrition': 'NUTRITION', 
                'Sleep': 'SLEEP',
                'Mood': 'MOOD',
                'Social': 'RELATIONSHIPS',
                'Work': 'SELF_DEVELOPMENT',  # Map work suggestions to self development
                'Family': 'RELATIONSHIPS',
                'Self development': 'SELF_DEVELOPMENT'
            }
            
            ai_category = category_mapping.get(ai_category_raw, 'MOOD')
            
            print(f"🔍 Creating NEW card for AI suggestion {i+1}: '{ai_title}' ({ai_category_raw} → {ai_category})")
            
            # Create new CardDetail in database for this AI suggestion
            try:
                new_card = create_card_details(
                    db=db,
                    card_type="suggestion",
                    title=ai_title,
                    category=ai_category,  # Use the mapped string value
                    details={},
                    description=f"AI-generated suggestion based on your current state",
                    duration=timedelta(minutes=10),  # 10 minutes default
                    tod=TimeOfDay.ANY,
                    special_card_action=SpecialActions.NONE,
                )
                print(f"✅ NEW CARD CREATED: '{ai_title}' with ID {new_card.id}")
                matched_card = new_card
                
            except Exception as e:
                print(f"❌ FAILED to create card for '{ai_title}': {str(e)}")
                # Fallback to existing card if creation fails
                all_cards = retrieve_all_card_details(db)
                matched_card = all_cards[0] if all_cards else None
            
            if matched_card:
                # Generate simple time slots like existing API (10am, 2:30pm, 7:10pm, etc.)
                time_slots = [
                    (10, 0),   # 10:00 AM
                    (14, 30),  # 2:30 PM  
                    (19, 10),  # 7:10 PM
                    (15, 0),   # 3:00 PM
                    (22, 30),  # 10:30 PM
                ]
                
                if i < len(time_slots):
                    hour, minute = time_slots[i]
                    suggestion_time = base_datetime.replace(
                        hour=hour,
                        minute=minute,
                        second=0,
                        microsecond=0
                    )
                else:
                    # Fallback for extra suggestions
                    suggestion_time = base_datetime.replace(
                        hour=9 + (i * 2),
                        minute=0,
                        second=0,
                        microsecond=0
                    )
                
                # Create card in EXACT same format as existing API
                card_suggestion = {
                    "card_id": int(time.time() * 1000) + random.randint(1000, 9999),
                    "time": suggestion_time,  # Keep as datetime object like existing API
                    "user_id": user_id,
                    "card_details": matched_card,  # Use the actual CardDetail object
                }
                formatted_suggestions.append(card_suggestion)
        
        return formatted_suggestions
        
    except Exception as e:
        logger.error(f"Error converting AI suggestions to card format: {str(e)}")
        return []
