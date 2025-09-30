from datetime import datetime, timedelta
from datetime import time as datetime_time
import random
from typing import List, Tuple
import time
from requests import Session

from app.postgres.crud.card import retrieve_filtered_card_details
from app.postgres.crud.goal import retrieve_all_goal_related_cards
from app.postgres.schema.card import CardDetail, UserCard
from app.services.digital_mentor.cfp import CognitiveFingerprint
from app.services.digital_mentor.user import User


class Mentor:
    def __init__(self):
        pass

    def morning_orientation(self, db: Session, user: User, fake_time: datetime):
        """
        How it works:
        - Finds blank slots during the day that need filling
        - Retrieves a list of goal_cards where the goal hasn't yet been completed
        - loops through each free block in day:
            * uses a probabilistic function to choose which cfp_attr to use as filter
            * Retrieves all card details filtering for
                + duration
                + a specific cfp_attr (ie family anxiety)
                + excludes repeating suggestions (ie ones that are already in user.plan)

            * Then splits up retrieved card details into two lists
                + List of card details that also link to a users goal
                + list of card detals that don't link to a users goal

            * Then chooses randomly from goal_related_suggestions if its not empty
            * otherwise it chooses from non_goal_related_suggestions

            * then adds the selected card to list of plan_ids so same suggestion cant be recommended twice
        """
        # time_now = datetime.now()
        time_now = fake_time
        start_time = time_now.replace(hour=8, minute=30, second=0, microsecond=0)

        start_of_day = max(time_now, start_time)

        available_times = user.get_available_times(start_of_day=start_of_day, end_of_day=time_now.replace(hour=23, minute=0, second=0, microsecond=0))

        free_blocks = self.split_times(available_times)

        suggested_plan = []
        plan_ids = [card.card_details_id for card in user.plan]  # THIS NEEDS CHANGING AS user.plan is empty (need to use history)

        # Get all cards associated with user's goals
        goals2Cards = retrieve_all_goal_related_cards(db, user.user_id)
        # Create a set of card IDs related to user's goals for efficient lookup, excluding completed goals
        goal_card_ids = {
            card.card_id for card in goals2Cards if any(goal.goal_id == card.goal_id and goal.completed < goal.target for goal in user.goals)
        }

        for start, end in free_blocks:
            duration = end - start
            chosen_cfp_attr = self.cognitive_weights_temp(user.cognitive_fingerprint, 0.5)[0]
            suggestion_results = retrieve_filtered_card_details(
                session=db, mh_category_name=user.cognitive_fingerprint.to_readable(chosen_cfp_attr), max_duration=duration, exclude_ids=plan_ids
            )

            if len(suggestion_results) == 0:
                print("no results found")
                continue

            # Split suggestions into two lists
            goal_related_suggestions = []
            non_goal_suggestions = []

            # See if suggestion_resulst also contains suggestions that meet goals
            for suggestion in suggestion_results:
                if suggestion.id in goal_card_ids:
                    goal_related_suggestions.append(suggestion)
                else:
                    non_goal_suggestions.append(suggestion)

            if goal_related_suggestions:
                chosen_card = random.choice(goal_related_suggestions)
            else:
                chosen_card = random.choice(non_goal_suggestions)

            potential_card = {
                "card_id": int(time.time() * 1000) + random.randint(1000, 9999),
                "time": start,
                "user_id": user.user_id,
                "card_details": chosen_card,
            }
            suggested_plan.append(potential_card)
            plan_ids.append(chosen_card.id)  # this ensures repeating card details aren't chosen

        suggested_plan.sort(key=lambda x: x["time"])
        return suggested_plan

    # Returns a cfp attribute probabilisitically based on temp
    def cognitive_weights_temp(self, cfp: CognitiveFingerprint, temp: float):
        # Convert CFP to list of tuples (attribute_name, value)
        attributes = cfp.to_list()

        # Get the weights (anxiety values)
        weights = [value for _, value in attributes]

        # Find the index of the highest weight
        max_index = weights.index(max(weights))

        # Generate a random number between 0 and 1
        rand = random.random()

        if rand < temp:
            # Return the highest weighted attribute based on temperature probability
            return attributes[max_index]
        else:
            # Remove the highest weight option but maintain weighted probability for others
            # remaining_attributes = attributes[:max_index] + attributes[max_index+1:]
            # remaining_weights = weights[:max_index] + weights[max_index+1:]

            remaining_attributes = attributes
            remaining_weights = weights

            # Normalize the remaining weights
            total = sum(remaining_weights)
            if total > 0:  # Avoid division by zero
                normalized_weights = [w / total for w in remaining_weights]
            else:
                normalized_weights = [1 / len(remaining_weights)] * len(remaining_weights)

            # Choose based on the normalized weights
            return random.choices(remaining_attributes, weights=normalized_weights, k=1)[0]

    def split_times(self, blocks: List[Tuple[datetime, datetime]]) -> List[Tuple[datetime, datetime]]:
        MAX_DURATION = timedelta(hours=4)  # Maximum block size allowed

        # Define time periods and their limits
        MORNING_START = datetime_time(6, 0)  # 6 AM
        AFTERNOON_START = datetime_time(12, 0)  # 12 PM
        EVENING_START = datetime_time(18, 0)  # 6 PM

        # Maximum blocks allowed per period
        MAX_MORNING_BLOCKS = 1
        MAX_AFTERNOON_BLOCKS = 1
        MAX_EVENING_BLOCKS = 0

        new_blocks = []
        morning_count = 0
        afternoon_count = 0
        evening_count = 0

        for start, end in blocks:
            current_start = start

            while current_start < end:
                current_time = current_start.time()
                current_end = min(current_start + MAX_DURATION, end)

                # Determine which period we're in and check limits
                if MORNING_START <= current_time < AFTERNOON_START:
                    if morning_count >= MAX_MORNING_BLOCKS:
                        break
                    morning_count += 1
                elif AFTERNOON_START <= current_time < EVENING_START:
                    if afternoon_count >= MAX_AFTERNOON_BLOCKS:
                        break
                    afternoon_count += 1
                else:  # Evening period
                    if evening_count >= MAX_EVENING_BLOCKS:
                        break
                    evening_count += 1

                new_blocks.append((current_start, current_end))
                current_start = current_end

        return new_blocks

    def suggest_alternatives(self, db: Session, user: User, activity: UserCard):
        suggested_plan = []
        plan_ids = [card.card_details_id for card in user.plan]
        plan_ids.append(activity.card_details.id)

        # Get all cards associated with user's goals
        goals2Cards = retrieve_all_goal_related_cards(db, user.user_id)
        # Create a set of card IDs related to user's goals for efficient lookup, excluding completed goals
        goal_card_ids = {
            card.card_id for card in goals2Cards if any(goal.goal_id == card.goal_id and goal.completed < goal.target for goal in user.goals)
        }

        for i in range(3):
            duration = activity.card_details.duration
            chosen_cfp_attr = self.cognitive_weights_temp(user.cognitive_fingerprint, 0.5)[0]
            suggestion_results = retrieve_filtered_card_details(
                session=db, mh_category_name=user.cognitive_fingerprint.to_readable(chosen_cfp_attr), max_duration=duration, exclude_ids=plan_ids
            )

            if len(suggestion_results) == 0:
                print("no results found")
                continue

            # Split suggestions into two lists
            goal_related_suggestions = []
            non_goal_suggestions = []

            # See if suggestion_resulst also contains suggestions that meet goals
            for suggestion in suggestion_results:
                if suggestion.id in goal_card_ids:
                    goal_related_suggestions.append(suggestion)
                else:
                    non_goal_suggestions.append(suggestion)

            if goal_related_suggestions:
                chosen_card = random.choice(goal_related_suggestions)
            else:
                chosen_card = random.choice(non_goal_suggestions)

            potential_card = {
                "card_id": int(time.time() * 1000) + random.randint(1000, 9999),
                "time": activity.time,
                "user_id": user.user_id,
                "card_details": chosen_card,
            }
            suggested_plan.append(potential_card)
            plan_ids.append(chosen_card.id)  # this ensures repeating card details aren't chosen

        suggested_plan.sort(key=lambda x: x["time"])
        return suggested_plan
