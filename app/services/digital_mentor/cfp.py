class CognitiveFingerprint:
    def __init__(self, work_anxiety: float, social_anxiety: float, family_anxiety: float, eating_anxiety: float, sleeping_anxiety: float):
        self.work_anxiety = work_anxiety
        self.social_anxiety = social_anxiety
        self.family_anxiety = family_anxiety
        self.eating_anxiety = eating_anxiety
        self.sleeping_anxiety = sleeping_anxiety

    def __str__(self):
        return (
            f"Cognitive Fingerprint:\n"
            f"  - Work Anxiety: {self.work_anxiety}\n"
            f"  - Social Anxiety: {self.social_anxiety}\n"
            f"  - Family Anxiety: {self.family_anxiety}\n"
            f"  - Eating Anxiety: {self.eating_anxiety}\n"
            f"  - Sleeping Anxiety: {self.sleeping_anxiety}"
        )

    def to_list(self):
        return [
            ("work_anxiety", self.work_anxiety),
            ("social_anxiety", self.social_anxiety),
            ("family_anxiety", self.family_anxiety),
            ("eating_anxiety", self.eating_anxiety),
            ("sleeping_anxiety", self.sleeping_anxiety),
        ]

    def to_readable(self, text):
        return text.replace("_", " ")
