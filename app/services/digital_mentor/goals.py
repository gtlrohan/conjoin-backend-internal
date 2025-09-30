import re
import random
from datetime import datetime


class Goal:
    def __init__(self, activity, n, period):
        self.activity = activity
        self.n = n
        self.period = period


def create_goal(str):
    match = re.match(r"(.*) (\w) times a week", str)
    if match:
        a = match.group(1)
        n = int(match.group(2))
        return Goal(a, n, "week")
    return None


goals_options = [
    "gym",
    "yoga",
    "family call",
    "family meet",
    "see friends",
    "hobbies: play chess online",
    "hobbies: online chess lesson",
    "hobbies: reading",
    "TV: BBC wildlife",
    "Youtube: film reviews",
    "birding: observation / make photos",
    "birding: posting",
]
freq = [f"{i} times a week" for i in range(1, 8)]
goals_options_with_freq = [f"{g} {f}" for g in goals_options for f in freq]


class CognitiveFingerprint:
    def __init__(self, concerns):
        self.concerns = concerns


def random_goals(n=4):
    g = random.sample(goals_options, n)
    f = random.choices(freq, k=n)
    goals = [f"{go} {fr}" for go, fr in zip(g, f)]
    return [create_goal(goal) for goal in goals]


def get_activity_count(activity, data):
    return sum(1 for d in data if d["activity"] == activity)


def get_progress(g, date, database):
    week = date.isocalendar()[1]
    if g.period == "week":
        count = get_activity_count(g.activity, [d for d in database if d["date"].isocalendar()[1] == week])
    elif g.period == "day":
        count = get_activity_count(g.activity, [d for d in database if d["date"].date() == date.date()])
    else:
        raise NotImplementedError("not implemented")
    return count


def softmax(x):
    exp_x = [np.exp(i) for i in x]
    return [i / sum(exp_x) for i in exp_x]


def randp(p):
    return next(i for i, value in enumerate(np.cumsum(p)) if random.random() < value)


def expected_progress(g):
    now = datetime.now()
    if g.period == "week":
        return g.n * now.weekday() / 7
    else:
        return g.n * now.hour / 24


def get_goal_suggestion(date, usr):
    goals = usr["goals"]
    database = usr["history"]
    prog = [get_progress(g, date, database) for g in goals]
    obs_prog = [c for c in prog]
    exp_prog = [expected_progress(g) for g in goals]
    urgency = [1 - (o / e) if e > 0 else 1 for o, e in zip(obs_prog, exp_prog)]
    k = randp(softmax(urgency))
    return goals[k]
