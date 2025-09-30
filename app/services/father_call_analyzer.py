import logging
import re
from typing import List, Dict, Tuple, Optional, Any
from app.postgres.models.voice_therapy import VoiceSessionMessage
from app.services.openAI import client

logger = logging.getLogger(__name__)

class FatherCallAnalyzer:
    """Analyzes voice therapy transcripts for father call scenarios using A-G matrix."""
    
    # Enhanced A-G Matrix categories with multiple selections and dynamic assessment
    MATRIX_CATEGORIES = {
        'A': {  # Conversation Dynamics (Who dominated?)
            1: "90-100% Kevin talking (Kevin dominated)",
            2: "70-90% Kevin talking (Kevin led mostly)", 
            3: "50-70% Kevin talking (Kevin slightly more)",
            4: "About equal participation (50/50)",
            5: "50-70% Father talking (Father slightly more)",
            6: "70-90% Father talking (Father led mostly)",
            7: "90-100% Father talking (Father dominated)",
            99: "DYNAMIC: Custom assessment"
        },
        'B': {  # Father's Behavior (Multiple selections allowed)
            10: "Aggressive/Hostile/Angry",
            11: "Patronizing/Condescending",
            12: "Distant/Cold/Uninterested", 
            13: "Critical/Judgmental",
            14: "Intrusive/Nosy",
            15: "Lying/Deceptive",
            16: "Irrational/Unreasonable",
            17: "Self-obsessed/Narcissistic",
            18: "Dismissive/Invalidating",
            19: "Manipulative/Guilt-tripping",
            20: "Supportive/Understanding",
            21: "Neutral/Matter-of-fact",
            99: "DYNAMIC: Custom behavior"
        },
        'C': {  # Topic Frequency
            21: "Yes, very rare (almost never)",
            22: "Yes, somewhat rare (occasionally)",
            23: "Yes, frequent (regularly)", 
            24: "Yes, very frequent (constantly)",
            25: "No, not specific (general topic)",
            99: "DYNAMIC: Custom frequency"
        },
        'D': {  # Content/Topic (Multiple selections allowed)
            31: "Politics/Current events",
            32: "Sports/Hobbies",
            33: "Kevin's friendships",
            34: "Kevin's family relationships",
            35: "Kevin's romantic life",
            36: "Kevin's work/career issues",
            37: "Health issues",
            38: "Kevin's appearance",
            39: "Historic/past issues",
            40: "Money/Financial matters",
            41: "Future plans",
            42: "Daily activities",
            43: "Father's own problems",
            44: "Family obligations",
            99: "DYNAMIC: Custom topic"
        },
        'E': {  # Severity/Impact
            41: "Mildly uncomfortable",
            42: "Moderately bad",
            43: "Very bad/distressing",
            44: "Extremely bad/traumatic",
            45: "Actually positive",
            99: "DYNAMIC: Custom severity"
        },
        'F': {  # Kevin's Emotions (Multiple selections allowed)
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
            64: "Confused/Lost",
            65: "Defensive/Protective",
            66: "Numb/Disconnected",
            67: "Relieved (when ended)",
            68: "Empowered/Strong",
            99: "DYNAMIC: Custom emotion"
        },
        'G': {  # Kevin's Actions (Multiple selections allowed)
            71: "Confront/Argued back",
            72: "Escape/Hung up/Avoided",
            73: "Manage/De-escalate",
            74: "Neutral/Just listened",
            75: "Defended self",
            76: "Yelled/Raised voice",
            77: "Shut down/Went silent",
            78: "Agreed to avoid conflict",
            79: "Set boundaries",
            80: "Asked for help",
            81: "Changed subject",
            99: "DYNAMIC: Custom action"
        }
    }
    
    # Categories that allow multiple selections
    MULTI_SELECT_CATEGORIES = {'B', 'D', 'F', 'G'}
    
    def __init__(self):
        pass
    
    def analyze_transcript(self, transcript: List[VoiceSessionMessage]) -> Dict[str, Any]:
        """
        Analyze a voice therapy transcript to extract A-G matrix classifications.
        
        Args:
            transcript: List of voice session messages
            
        Returns:
            Dict containing matrix selections, rationales, and suggestions
        """
        logger.info(f"Analyzing transcript with {len(transcript)} messages")
        
        # Convert transcript to text
        conversation_text = self._extract_conversation_text(transcript)
        
        # Debug logging for conversation content
        user_content = " ".join([msg.message for msg in transcript if msg.speaker == "user" and msg.message])
        assistant_content = " ".join([msg.message for msg in transcript if msg.speaker == "assistant" and msg.message])
        
        logger.info(f"Conversation text length: {len(conversation_text)} characters")
        logger.info(f"User content length: {len(user_content)} characters")
        logger.info(f"Assistant content length: {len(assistant_content)} characters")
        logger.info(f"User content preview: '{user_content[:150]}{'...' if len(user_content) > 150 else ''}'")
        logger.info(f"Full conversation preview: '{conversation_text[:200]}{'...' if len(conversation_text) > 200 else ''}'")
        
        # Use AI to analyze the conversation
        matrix_analysis = self._ai_analyze_conversation(conversation_text)
        
        # CRITICAL: If AI analysis returns None (no meaningful conversation), return failure
        if matrix_analysis is None:
            logger.warning("Father call analysis failed - no meaningful conversation detected")
            logger.info(f"Failed analysis conversation text: '{conversation_text}'")
            return {
                'matrix_selections': {},
                'rationales': {},
                'conversation_summary': 'Analysis could not be completed due to insufficient conversation content.',
                'suggestions': [],
                'analysis_complete': False
            }
        
        # Generate suggestions based on matrix selections
        suggestions = self._generate_suggestions(matrix_analysis['matrix_selections'])
        
        # Create comprehensive response
        result = {
            'matrix_selections': matrix_analysis['matrix_selections'],
            'rationales': matrix_analysis['rationales'],
            'conversation_summary': matrix_analysis.get('conversation_summary', ''),
            'suggestions': suggestions,
            'analysis_complete': True
        }
        
        logger.info(f"Analysis complete. Matrix selections: {result['matrix_selections']}")
        return result
    
    def _extract_conversation_text(self, transcript: List[VoiceSessionMessage]) -> str:
        """Extract and format conversation text from transcript."""
        conversation_lines = []
        
        for msg in transcript:
            speaker = "Kevin" if msg.speaker == "user" else "AI Therapist"
            conversation_lines.append(f"{speaker}: {msg.message}")
        
        return "\n".join(conversation_lines)
    
    def _ai_analyze_conversation(self, conversation_text: str) -> Optional[Dict[str, Any]]:
        """Use OpenAI synchronously to analyze the conversation and extract matrix classifications."""

        # CRITICAL VALIDATION: Check if conversation contains meaningful father call discussion
        if not self._validate_father_call_content(conversation_text):
            logger.warning("Conversation does not contain meaningful father call discussion - aborting analysis")
            return None

        analysis_prompt = f"""
You are analyzing a voice therapy session where Kevin discussed a difficult phone call with his father.
Based on the conversation below, classify it using the ENHANCED A-G matrix system and provide rationales.

NOTE: This conversation may contain speech-to-text errors, fragmented sentences, or incomplete words. 
Try to interpret the meaning despite technical imperfections. Look for emotional context and key themes.

CONVERSATION:
{conversation_text}

ENHANCED A-G MATRIX CATEGORIES:

A (Conversation Dynamics - Who did most of the talking?):
1=90-100% Kevin talking (Kevin dominated), 2=70-90% Kevin talking (Kevin led mostly), 3=50-70% Kevin talking (Kevin slightly more)
4=About equal participation (50/50), 5=50-70% Father talking (Father slightly more), 6=70-90% Father talking (Father led mostly)
7=90-100% Father talking (Father dominated), 99=DYNAMIC (provide custom assessment)

B (Father's Behavior - MULTIPLE SELECTIONS ALLOWED):
10=Aggressive/Hostile, 11=Patronizing/Condescending, 12=Distant/Cold, 13=Critical/Judgmental, 14=Intrusive/Nosy
15=Lying/Deceptive, 16=Irrational/Unreasonable, 17=Self-obsessed, 18=Dismissive/Invalidating, 19=Manipulative
20=Supportive/Understanding, 21=Neutral/Matter-of-fact, 99=DYNAMIC (provide custom description)

C (Topic Frequency - How often does this type of conversation happen?):
21=Yes, very rare (almost never), 22=Yes, somewhat rare (occasionally), 23=Yes, frequent (regularly)
24=Yes, very frequent (constantly), 25=No, not specific to Kevin (general topic), 99=DYNAMIC (custom assessment)

D (Content/Topic - MULTIPLE SELECTIONS ALLOWED):
31=Politics/Current events, 32=Sports/Hobbies, 33=Kevin's friendships, 34=Kevin's family relationships, 35=Kevin's romantic life
36=Kevin's work/career issues, 37=Health issues, 38=Kevin's appearance, 39=Historic/past issues, 40=Money/Financial matters
41=Future plans, 42=Daily activities, 43=Father's own problems, 44=Family obligations, 99=DYNAMIC (custom topic)

E (Severity/Impact - How bad did it feel for Kevin?):
41=Mildly uncomfortable, 42=Moderately bad, 43=Very bad/distressing, 44=Extremely bad/traumatic
45=Actually positive, 99=DYNAMIC (custom severity assessment)

F (Kevin's Emotions - MULTIPLE SELECTIONS ALLOWED):
51=Surprised/Shocked, 52=Stressed/Anxious, 53=Insecure/Self-doubting, 54=Rejected/Unwanted, 55=Frustrated/Irritated
56=Let down/Disappointed, 57=Humiliated/Embarrassed, 58=Hurt/Wounded, 59=Guilty/Self-blaming, 60=Isolated/Alone
61=Fragile/Vulnerable, 62=Angry/Furious, 63=Sad/Depressed, 64=Confused/Lost, 65=Defensive/Protective
66=Numb/Disconnected, 67=Relieved (when ended), 68=Empowered/Strong, 99=DYNAMIC (custom emotion)

G (Kevin's Actions/Responses - MULTIPLE SELECTIONS ALLOWED):
71=Confront/Argued back, 72=Escape/Hung up/Avoided, 73=Manage/De-escalate, 74=Neutral/Just listened
75=Defended self, 76=Yelled/Raised voice, 77=Shut down/Went silent, 78=Agreed to avoid conflict
79=Set boundaries, 80=Asked for help, 81=Changed subject, 99=DYNAMIC (custom action)

Instructions:
- Listen carefully to Kevin's actual words and descriptions
- For B, D, F, G categories: Select multiple numbers if Kevin describes multiple behaviors/emotions/actions  
- Use DYNAMIC (99) when Kevin's experience doesn't fit the predefined categories
- Base your analysis on Kevin's direct statements

Analyze the conversation and respond in this EXACT JSON format:
{{
  "matrix_selections": {{
    "A": [<number>],
    "B": [<number1>, <number2>, ...],
    "C": [<number>],
    "D": [<number1>, <number2>, ...],
    "E": [<number>],
    "F": [<number1>, <number2>, ...],
    "G": [<number1>, <number2>, ...]
  }},
  "rationales": {{
    "A": "Kevin explicitly said he... (base on his exact words about who talked more)",
    "B": "Based on Kevin's description, father was... (list each behavior Kevin mentioned)",
    "C": "Kevin indicated this type of conversation... (frequency based on his words)",
    "D": "The main topics Kevin mentioned were... (each topic he discussed)",
    "E": "Kevin described the emotional impact as... (severity he expressed)",
    "F": "Kevin expressed feeling... (each emotion he mentioned - be comprehensive)",
    "G": "Kevin said he responded by... (each action/response he described)"
  }},
  "dynamic_assessments": {{
    "A": "Custom assessment if 99 selected",
    "B": "Custom behavior description if 99 selected",
    "C": "Custom frequency assessment if 99 selected",
    "D": "Custom topic description if 99 selected", 
    "E": "Custom severity assessment if 99 selected",
    "F": "Custom emotion description if 99 selected",
    "G": "Custom action description if 99 selected"
  }},
  "conversation_summary": "2-3 sentence summary of what happened in the call",
  "confidence_score": 0.85
}}

REMEMBER: Listen to Kevin's actual words. If he says he yelled, he dominated the conversation (A=1-3). If he felt both angry AND sad, include both emotions in F.
"""

        try:
            # Build messages as in our OpenAI service (developer + user)
            api_messages = [
                {"role": "developer", "content": "You are an expert in conversation analysis and psychological assessment."},
                {"role": "user", "content": analysis_prompt},
            ]

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=api_messages,
                temperature=0.0,
            )
            content = response.choices[0].message.content or ""

            # Try to parse JSON strictly; if it fails, try to extract the JSON block
            import json, re
            try:
                parsed = json.loads(content)
                # Check if AI determined analysis is impossible
                if parsed.get("analysis_impossible"):
                    logger.info("AI determined father call analysis is not possible from this conversation")
                    return None
                    
                # Normalize the parsed result for enhanced matrix format
                normalized = self._normalize_analysis_result(parsed)
                return normalized
                
            except Exception:
                # Extract first JSON object
                match = re.search(r"\{[\s\S]*\}", content)
                if match:
                    try:
                        parsed = json.loads(match.group(0))
                        if parsed.get("analysis_impossible"):
                            logger.info("AI determined father call analysis is not possible from this conversation")
                            return None
                            
                        # Normalize the parsed result for enhanced matrix format  
                        normalized = self._normalize_analysis_result(parsed)
                        return normalized
                        
                    except Exception:
                        pass
                logger.error("Model did not return valid JSON")
                return None

        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            # CRITICAL: NO FALLBACK ANALYSIS - Return None instead of generating fake data
            logger.error("No fallback analysis will be performed to prevent fake matrix generation")
            return None

    def _normalize_analysis_result(self, parsed_result: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize the AI analysis result to ensure proper format for enhanced matrix."""
        from datetime import datetime
        
        # Validate required fields
        required_fields = ["matrix_selections", "rationales", "conversation_summary"]
        for field in required_fields:
            if field not in parsed_result:
                logger.error(f"Missing required field: {field}")
                return None
        
        # Normalize matrix selections to arrays
        matrix_selections = parsed_result["matrix_selections"]
        expected_categories = ["A", "B", "C", "D", "E", "F", "G"]
        
        for cat in expected_categories:
            if cat not in matrix_selections:
                logger.error(f"Missing matrix category: {cat}")
                return None
            
            # Ensure selections are arrays
            selections = matrix_selections[cat]
            if not isinstance(selections, list):
                # Convert single selection to array
                matrix_selections[cat] = [selections]
                selections = matrix_selections[cat]
            
            # Validate each selection in the array
            for selection in selections:
                if not self._is_valid_selection(cat, selection):
                    logger.warning(f"Invalid selection for category {cat}: {selection}")
        
        # Ensure rationales are arrays for multi-select categories
        rationales = parsed_result["rationales"]
        for cat in self.MULTI_SELECT_CATEGORIES:
            if cat in rationales and not isinstance(rationales[cat], list):
                rationales[cat] = [rationales[cat]]
        
        # Ensure dynamic_assessments exists
        if "dynamic_assessments" not in parsed_result:
            parsed_result["dynamic_assessments"] = {}
        
        # Ensure confidence_score exists
        if "confidence_score" not in parsed_result:
            parsed_result["confidence_score"] = 0.75  # Default confidence
        
        # Add metadata
        parsed_result["analysis_timestamp"] = datetime.utcnow().isoformat()
        parsed_result["analyzer_version"] = "3.0"  # Enhanced matrix version
        
        # Log analysis summary
        total_selections = sum(len(selections) if isinstance(selections, list) else 1 
                             for selections in matrix_selections.values())
        logger.info(f"Enhanced AI analysis normalized: {total_selections} total matrix selections across {len(matrix_selections)} categories")
        
        # Log multi-select categories usage
        for cat in self.MULTI_SELECT_CATEGORIES:
            if cat in matrix_selections and len(matrix_selections[cat]) > 1:
                logger.info(f"Category {cat} has multiple selections: {matrix_selections[cat]}")
        
        return parsed_result
    
    def _is_valid_selection(self, category: str, selection: int) -> bool:
        """Validate that a selection is valid for the given category."""
        if category not in self.MATRIX_CATEGORIES:
            return False
        return selection in self.MATRIX_CATEGORIES[category]

    def _validate_father_call_content(self, conversation_text: str) -> bool:
        """Validate that the conversation contains meaningful father call discussion."""
        text_lower = conversation_text.lower()
        
        # Check for father-related keywords (more comprehensive and forgiving)
        father_keywords = ['father', 'dad', 'papa', 'my dad', 'my father', 'he called', 'phone call', 'called me', 'called', 'him']
        has_father_reference = any(keyword in text_lower for keyword in father_keywords)
        
        # Check for call-related context (more forgiving)
        call_keywords = ['call', 'phone', 'rang', 'talked', 'spoke', 'conversation', 'said', 'told', 'speak', 'discuss']
        has_call_reference = any(keyword in text_lower for keyword in call_keywords)
        
        # Check for emotional/problematic context (expanded)
        problem_keywords = ['wrong', 'difficult', 'bad', 'upset', 'angry', 'yelled', 'shouted', 'argued', 'problem', 'issue', 'stress', 'hurt', 'frustrated', 'sad', 'agresiv', 'aggressive']
        has_problem_reference = any(keyword in text_lower for keyword in problem_keywords)
        
        # More lenient validation: father reference OR call reference, plus some substantial content
        # This accounts for speech-to-text errors and fragmented speech
        is_valid = has_father_reference or (has_call_reference and has_problem_reference)
        
        # Lower threshold for meaningful content to account for speech-to-text fragmentation
        meaningful_content = text_lower.replace('hello', '').replace('hi', '').replace('there', '').replace('how', '').replace('are', '').replace('you', '').replace('thank', '').replace('thanks', '').strip()
        has_substantial_content = len(meaningful_content) > 15  # Reduced from 30 to 15
        
        # Additional check: if the conversation mentions therapy session types, consider it valid
        therapy_keywords = ['therapy', 'therapist', 'session', 'analyze', 'analysis', 'discuss', 'talk about']
        has_therapy_context = any(keyword in text_lower for keyword in therapy_keywords)
        
        # Final validation: (father/call reference OR therapy context) AND substantial content
        final_valid = (is_valid or has_therapy_context) and has_substantial_content
        
        logger.info(f"Content validation: father={has_father_reference}, call={has_call_reference}, problem={has_problem_reference}, therapy={has_therapy_context}, substantial={has_substantial_content}, final={final_valid}")
        logger.info(f"Sample content (first 100 chars): '{text_lower[:100]}'")
        
        return final_valid
    
    # REMOVED: _fallback_analysis method that generated fake matrix data
    # This prevents fake analysis when real conversation analysis fails
    
    def _generate_suggestions(self, matrix_selections: Dict[str, int]) -> List[Dict[str, Any]]:
        """Generate therapeutic suggestions based on matrix selections."""
        
        # Map combinations to suggestions
        suggestions = []
        
        # Get the selected numbers
        a_val = matrix_selections.get('A')
        b_val = matrix_selections.get('B') 
        f_val = matrix_selections.get('F')
        g_val = matrix_selections.get('G')
        
        # Generate specific suggestions based on patterns
        if b_val == 10:  # Aggressive father
            suggestions.append({
                'id': 'aggressive_father_boundary',
                'category': 'Boundary Setting',
                'name': 'Boundary Setting with Aggressive Parent',
                'description': 'Strategies for maintaining emotional safety when dealing with an aggressive father',
                'triggered_by': [a_val, b_val, f_val],
                'rationale': f"Selected because father showed aggressive behavior (B{b_val}) causing emotional impact (F{f_val})",
                'recommended_actions': [
                    'Practice the "broken record" technique - repeat your boundary calmly',
                    'Use "I" statements to express your feelings without accusation',
                    'Have an exit strategy ready for future calls',
                    'Consider setting time limits for future conversations'
                ]
            })
        
        if f_val in [58, 55, 56]:  # Hurt, frustrated, let down
            suggestions.append({
                'id': 'emotional_processing',
                'category': 'Emotional Processing', 
                'name': 'Processing Hurt from Family Conflict',
                'description': 'Techniques for working through emotional pain from family relationships',
                'triggered_by': [f_val, b_val],
                'rationale': f"Selected because Kevin experienced significant emotional pain (F{f_val})",
                'recommended_actions': [
                    'Practice self-compassion - this hurt is valid and understandable',
                    'Journal about your feelings to process them fully',
                    'Consider what your father\'s behavior says about him, not you',
                    'Discuss healthy boundaries with Sarah for emotional support'
                ]
            })
        
        if g_val == 72:  # Escape/withdraw
            suggestions.append({
                'id': 'assertiveness_training',
                'category': 'Communication Skills',
                'name': 'Building Assertiveness with Difficult Family',
                'description': 'Developing skills to communicate needs effectively with challenging family members',
                'triggered_by': [g_val, a_val],
                'rationale': f"Selected because Kevin tends to withdraw (G{g_val}) when father dominates",
                'recommended_actions': [
                    'Practice assertive phrases beforehand: "I need to be heard too"',
                    'Use the DEAR method: Describe, Express, Assert, Reinforce',
                    'Start with smaller assertions in safer relationships',
                    'Remember: you have the right to express your thoughts'
                ]
            })
        
        # Default suggestion if none match
        if not suggestions:
            suggestions.append({
                'id': 'general_family_coping',
                'category': 'General Coping',
                'name': 'Managing Difficult Family Relationships',
                'description': 'General strategies for coping with challenging family dynamics',
                'triggered_by': list(matrix_selections.values()),
                'rationale': 'Selected based on overall pattern of difficult father relationship',
                'recommended_actions': [
                    'Focus on what you can control - your responses and boundaries',
                    'Build a support network outside the family relationship',
                    'Practice emotional regulation techniques before family interactions',
                    'Consider professional counseling for ongoing family trauma'
                ]
            })
        
        return suggestions[:2]  # Return top 2 suggestions
