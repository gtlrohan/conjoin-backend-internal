import random


class DecisionNode:
    def __init__(self, name):
        self.name = name
        self.outcomes = {}

    def add_outcome(self, condition, probability, node):
        if condition not in self.outcomes:
            self.outcomes[condition] = []
        self.outcomes[condition].append((probability, node))

    def next_node(self):
        if not self.outcomes:
            return None
        rand_val = random.random()
        cumulative_probability = 0.0
        for _condition, outcomes in self.outcomes.items():
            for probability, node in outcomes:
                cumulative_probability += probability
                if rand_val <= cumulative_probability:
                    return node
        return None

    def get_outcomes_as_string(self):
        outcome_strings = []
        for condition, outcomes in self.outcomes.items():
            outcome_strings.append(f"{condition}: {[(prob, node.name) for prob, node in outcomes]}")
        return "{" + ", ".join(outcome_strings) + "}"

    def __str__(self):
        return self.name


class CardActionsDecisionTree:
    def __init__(self, user_probabilities):
        self.user_probabilities = user_probabilities
        self.build_tree()

    def build_tree(self):
        # Creating nodes based on the provided decision tree
        self.do_nothing = DecisionNode("Finished - do nothing")
        self.scheduling_conflict = DecisionNode("Scheduling conflict")
        self.insert_card_next_free_slot = DecisionNode("Insert triggered card into next available slot")

        self.free_time_calendar = DecisionNode("Free time in Calendar?")
        self.free_time_calendar.add_outcome("free_time", self.user_probabilities["free_time_yes"], self.insert_card_next_free_slot)
        self.free_time_calendar.add_outcome("free_time", self.user_probabilities["free_time_no"], self.scheduling_conflict)

        self.reschedule_immediately = DecisionNode("Reschedule immediately?")
        self.reschedule_immediately.add_outcome(
            "reschedule_immediately", self.user_probabilities["reschedule_immediately_yes"], self.free_time_calendar
        )
        self.reschedule_immediately.add_outcome(
            "reschedule_immediately", self.user_probabilities["reschedule_immediately_no"], self.free_time_calendar
        )

        self.reschedule_by_user = DecisionNode("Reschedule by user?")
        self.reschedule_by_user.add_outcome("reschedule_by_user", self.user_probabilities["reschedule_by_user_yes"], self.do_nothing)
        self.reschedule_by_user.add_outcome("reschedule_by_user", self.user_probabilities["reschedule_by_user_no"], self.do_nothing)

        self.reschedule_by_mentor = DecisionNode("Reschedule by mentor?")
        self.reschedule_by_mentor.add_outcome(
            "reschedule_by_mentor", self.user_probabilities["reschedule_by_mentor_yes"], self.reschedule_immediately
        )
        self.reschedule_by_mentor.add_outcome("reschedule_by_mentor", self.user_probabilities["reschedule_by_mentor_no"], self.reschedule_by_user)

        self.trigger_nodes = {
            "completed": self.do_nothing,
            "missed": self.reschedule_by_mentor,
            "user_cancelled": self.reschedule_by_mentor,
            "participant_cancelled": self.reschedule_by_user,
        }

    def process(self, trigger):
        current_node = self.trigger_nodes[trigger]
        while current_node:
            print(f"At node: {current_node.name}")
            next_node = current_node.next_node()
            if not next_node:
                break
            current_node = next_node
