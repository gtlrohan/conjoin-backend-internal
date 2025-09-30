#
# These are functions for proposing schedules
#
from typing import Callable, List, Tuple, Union
import app.services.digital_mentor.user as User
import pandas as pd
from pandas import DataFrame, Timestamp
import numpy as np
from datetime import datetime, timedelta
import random

from app.services.digital_mentor.scoring import score_morning
from app.services.digital_mentor.mh_sug import *


def make_routines_day(day: Timestamp) -> DataFrame:
    day = day.floor("D")
    entries = [
        {"time": day + timedelta(hours=8), "activity": "breakfast", "location": "home", "duration": timedelta(hours=1)},
        {"time": day + timedelta(hours=12), "activity": "lunch", "location": "work", "duration": timedelta(hours=1)},
        {"time": day + timedelta(hours=19), "activity": "dinner", "location": "home", "duration": timedelta(hours=1)},
    ]

    if day.weekday() < 5:  # Weekday
        entries.append({"time": day + timedelta(hours=9), "activity": "work", "location": "work", "duration": timedelta(hours=3)})
        entries.append({"time": day + timedelta(hours=13), "activity": "work", "location": "work", "duration": timedelta(hours=4)})

    return pd.DataFrame(entries)


def get_available_times(day: DataFrame, resolution: timedelta = timedelta(minutes=1)) -> List[Tuple[datetime, datetime]]:
    date = day["time"].dt.floor("D").iloc[0]
    day = day[day["time"].dt.floor("D") == date]  # Filter to only include today's events

    t0 = date + timedelta(hours=6)  # Start 6 AM
    t1 = date + timedelta(hours=24)  # End 12 AM next day
    times = pd.date_range(t0, t1, freq=resolution)

    freetime = [not any((row["time"] < t < (row["time"] + row["duration"])) for _, row in day.iterrows()) for t in times]
    z = np.where(freetime)[0]

    def connected_components(z):
        blocks = []
        blocks.append([z[0]])
        iblock = 0
        for i in range(1, len(z)):
            if z[i] - blocks[iblock][-1] == 1:
                blocks[iblock].append(z[i])  # Existing block
            else:
                blocks.append([z[i]])  # Open new block
                iblock += 1
        return blocks

    blocks = connected_components(z)
    blocks = [(times[block[0]], times[block[-1]]) for block in blocks]
    blocks = [b for b in blocks if (b[1] - b[0]).total_seconds() > 0]
    return blocks


def split_blocks(blocks: List[Tuple[datetime, datetime]]) -> List[Tuple[datetime, datetime]]:
    new_blocks = []
    for b in blocks:
        split_points = list(pd.date_range(b[0], b[1], freq="30min"))

        # Check if there are enough points to split
        if len(split_points) <= 1:
            # If block is too small, just keep it as is
            new_blocks.append((b[0], b[1]))
            continue

        t = random.randint(1, len(split_points) - 1)
        new_blocks.append((split_points[t], split_points[-1]) if t > len(split_points) // 2 else (split_points[0], split_points[t]))

    return new_blocks


def draw(r, var):
    if r[var] is None:
        # Provide default values based on the variable type
        if var == "duration":
            return 30  # Default duration of 30 minutes
        # Add other default cases as needed
        return 0  # Generic default

    if isinstance(r[var], int):
        return r[var]
    else:
        return random.choice(list(map(int, r[var].split(","))))


def make_rand_proposal(current_day: Timestamp, user: User, n_goal: int = 3, n_mh: int = 3):
    prop = make_routines_day(current_day)
    blocks = get_available_times(prop)
    blocks = split_blocks(blocks)

    # Mental health suggestions
    ind = random.sample(range(len(mh_sug)), n_mh)

    for i in range(n_mh):
        if not blocks:  # Check if blocks is empty
            break
        time = blocks.pop(random.randint(0, len(blocks) - 1))
        r = mh_sug.iloc[ind[i]]

        # Create dictionary with list values
        new_row_dict = {
            "time": [time[0]],
            "duration": [timedelta(minutes=draw(r, "duration"))],
            "location": [None],
            "suggested": [True],
            "activity": [r["activity"]],
        }
        new_row = pd.DataFrame.from_dict(new_row_dict)
        prop = pd.concat([prop, new_row], ignore_index=True)

    prop = prop.sort_values("time")
    blocks = get_available_times(prop)
    blocks = split_blocks(blocks)

    # Goals
    goal = random.sample(user.goals, min(n_goal, len(user.goals)))

    for i in range(len(goal)):
        if not blocks:  # Check if blocks is empty
            break
        time = blocks.pop(random.randint(0, len(blocks) - 1))

        activity = goal[i].title if isinstance(goal[i].title, str) else random.choice(goal[i].title)

        # Create dictionary with list values
        new_row_dict = {
            "time": [time[0]],
            "duration": [goal[i].duration],  # Duration is fixed for now
            "location": [None],
            "suggested": [True],
            "activity": [activity],
        }
        new_row = pd.DataFrame.from_dict(new_row_dict)
        prop = pd.concat([prop, new_row], ignore_index=True)

    return prop.sort_values("time")


def propose(hour, current_day: Timestamp, user: User):
    proposal = make_rand_proposal(current_day, user)
    proposal = proposal[proposal["time"].dt.time > hour]
    return proposal


def propose_opt(score_func: Callable[[DataFrame], float], current_time: Timestamp, user: User, niter: int = 1) -> DataFrame:
    start_of_day = current_time.floor("D")
    p = make_rand_proposal(start_of_day, user)
    p = p[p["time"] > current_time]
    opt = score_func(p)

    for _ in range(niter):
        print(_)
        pcand = make_rand_proposal(start_of_day, user)
        pcand = pcand[pcand["time"] > current_time]
        optcand = score_func(pcand)

        if optcand > opt:
            opt = optcand
            p = pcand

    return p


def morning_orientation(user: User, time: datetime):
    current_time = Timestamp(time)
    result = propose_opt(score_func=lambda p: score_morning(user, p), current_time=current_time, user=user)

    # Convert DataFrame to dictionary and handle special data types
    result_dict = []
    for _, row in result.iterrows():
        row_dict = {
            "time": row["time"],
            "activity": row["activity"],
            "location": row["location"],
            "duration": int(row["duration"].total_seconds() / 60),  # Convert to minutes
            "suggested": bool(row["suggested"]) if pd.notna(row["suggested"]) else None,
        }
        result_dict.append(row_dict)

    return result_dict


def propose_next(prop, user: User):
    for cat in user.cognitive_fingerprint.keys():
        cfp = user.cognitive_fingerprint[cat]
        intensity = int(cfp * 4)

        if intensity == 0:
            r = random.choice(mh_sug[mh_sug["cat"] == "motivation"])
        else:
            if intensity > 3 and user.cognitive_score > 0.75:
                intensity = f"{intensity}+"
            else:
                intensity = str(intensity)

            try:
                sug = get_suggestion(cat, intensity, user.history)
            except Exception:
                return (cat, None)

            r = mh_sug[mh_sug["activity"] == sug]

        blocks = get_available_times(prop)
        blocks = split_blocks(blocks)
        time = blocks.pop(random.randint(0, len(blocks) - 1))

        prop = pd.concat(
            [
                prop,
                pd.DataFrame.from_dict(
                    {
                        "time": time[0],
                        "duration": timedelta(minutes=draw(r, "duration")),
                        "location": None,
                        "suggested": True,
                        "activity": r["activity"],
                    }
                ),
            ],
            ignore_index=True,
        )

        return (cat, prop.sort_values("time"))


# def propose3(user: User, current_time=None):
#     if current_time is None:
#         current_time = datetime.now()
#     prop = make_routines_day(current_time)[make_routines_day(current_time)['time'] > current_time]
#     prop = pd.concat([prop, user.calendar], ignore_index=True).sort_values('time')
#     props = propose_next(prop, user)
#     scores = [score_proposal(p[1], User) for p in props if p[1] is not None]
#     optimal_prop = [p[1] for p in props if p[1] is not None][np.argmax(scores)]
#     return optimal_prop


def get_mh_sug(cat, severity, cog_score=None):
    ind = mh_sug[(mh_sug["cat"] == cat) & (mh_sug["severity"] == severity)].index
    if len(ind) < 1:
        return None
    else:
        return random.choice(mh_sug.loc[ind, "activity"])


def find_time(plan, sug):
    blocks = get_available_times(plan)
    return random.choice(blocks)


def add_goal_activity(user: User):
    sug = random.choice(user.goals)
    starttime, endtime = find_time(user.plan, sug)
    dur = timedelta(minutes=random.choice([15, 30, 45, 60, 90]))
    user.add_to_plan({"activity": sug["activity"], "time": starttime, "duration": dur, "suggested": True})


def add_mh_activity(user: User):
    cfp = list(user.cognitive_fingerprint)
    # sample category by urgency
    cati = next(i for i, x in enumerate(np.random.rand() < np.cumsum([x[1] for x in cfp])) if x)
    ccat = cfp[cati][0]
    severity = int(np.floor(cfp[cati][1] * 4))
    sug = get_mh_sug(ccat, severity)
    if sug is None:
        # too low, use motivation
        sug = get_mh_sug("motivation", 0)
    # get time
    time = find_time(user.plan, sug)[0]
    dur_idx = next(i for i, x in enumerate(mh_sug["activity"]) if x == sug)
    dur = mh_sug.iloc[dur_idx]["duration"]
    if isinstance(dur, int):
        dur = pd.Timedelta(minutes=dur)
    elif isinstance(dur, str):
        dur = pd.Timedelta(minutes=draw(mh_sug.iloc[dur_idx]["duration"]))
    else:
        raise ValueError("duration must be int or string")
    user.add_to_plan({"activity": sug, "time": time, "duration": dur, "suggested": True})
