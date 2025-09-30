from typing import Any, Dict, List, Tuple
from datetime import datetime, timedelta

from app.postgres.schema.card import UserCard
from app.postgres.schema.cognitive_score import CognitiveScore
from app.services.digital_mentor.cfp import CognitiveFingerprint


class User:
    def __init__(
        self,
        user_id,
        preferences,
        goals,
        cognitive_fingerprint: CognitiveFingerprint,
        cognitive_score: CognitiveScore,
        history: List[Dict[str, Any]],
        plan: List[UserCard],
    ):
        self.user_id = user_id
        self.preferences = preferences
        self.goals = goals
        self.cognitive_fingerprint = cognitive_fingerprint
        self.cognitive_score = cognitive_score
        self.history = history
        self.plan = plan

    def get_available_times(self, start_of_day: datetime, end_of_day: datetime) -> List[Tuple[datetime, datetime]]:
        # If no plan, return the entire day as available
        if not self.plan:
            return [(self.round_up_to_nearest_5(start_of_day), end_of_day)]

        # Create and sort busy periods in one step
        busy = sorted((card.time, card.time + card.card_details.duration) for card in self.plan)

        # Find available times around busy periods
        available_times = []
        current_time = start_of_day

        for start, end in busy:
            # Check if there's free time before the next busy period
            # Add 30-minute buffer before the busy period
            buffer_start = start - timedelta(minutes=30)

            if current_time < buffer_start:
                # Round the start time up to the nearest multiple of 5 minutes
                rounded_start = self.round_up_to_nearest_5(current_time)
                if rounded_start < buffer_start:
                    available_times.append((rounded_start, buffer_start))

            # Move current_time forward
            # Add 30-minute buffer after the busy period
            current_time = max(current_time, end + timedelta(minutes=30))

        # If there's free time after the last busy period
        if current_time < end_of_day:
            rounded_start = self.round_up_to_nearest_5(current_time)
            available_times.append((rounded_start, end_of_day))

        return available_times

    def round_up_to_nearest_5(self, dt: datetime) -> datetime:
        """Round up the given datetime to the nearest 5-minute mark."""
        # Calculate minutes to add to round up
        additional_minutes = (5 - (dt.minute % 5)) % 5
        return dt + timedelta(minutes=additional_minutes)
