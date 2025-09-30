from dataclasses import dataclass
from typing import List

from sqlalchemy.orm import Session

from app.postgres.schema.goals import Goal, Goals2Card, UserGoals


def create_goal(db: Session, name: str) -> Goal:
    # Create a new Goal instance
    new_goal = Goal(name=name)
    db.add(new_goal)
    db.commit()
    db.refresh(new_goal)

    # Return the goal object
    return new_goal


def create_user_goal(db: Session, user_id: int, goal_id: int, target: int) -> UserGoals:
    # Create a new Goal instance
    new_user_goal = UserGoals(user_id=user_id, goal_id=goal_id, target=target)
    db.add(new_user_goal)
    db.commit()
    db.refresh(new_user_goal)

    # Return the goal object
    return new_user_goal


def create_goals2card_from_list(db: Session, goals2card_data: List[any]):
    new_entries = []
    for data in goals2card_data:
        new_entry = Goals2Card(goal_id=data.goal_id, card_id=data.card_id)
        db.add(new_entry)
        new_entries.append(new_entry)

    db.commit()
    for entry in new_entries:
        db.refresh(entry)

    return new_entries


def retrieve_all_goals(db: Session) -> list[Goal]:
    # Query all entries in the Goal table
    return db.query(Goal).all()


@dataclass
class UserGoalResponse:
    id: int
    user_id: int
    goal_id: int
    goal_name: str
    target: int
    completed: int

    def __repr__(self):
        return f"UserGoal(id={self.id}, user_id={self.user_id}, goal_id='{self.goal_id}, goal_name='{self.goal_name}', target={self.target}, completed={self.completed})"


def retrieve_all_user_goals(db: Session, user_id: int) -> List[UserGoalResponse]:
    results = db.query(UserGoals, Goal.name).join(Goal).filter(UserGoals.user_id == user_id).all()

    return [
        UserGoalResponse(
            id=user_goal.id,
            user_id=user_goal.user_id,
            goal_id=user_goal.goal_id,
            goal_name=goal_name,
            target=user_goal.target,
            completed=user_goal.completed,
        )
        for user_goal, goal_name in results
    ]


def retrieve_all_goal_related_cards(db: Session, user_id: int):
    return db.query(Goals2Card).join(UserGoals, UserGoals.goal_id == Goals2Card.goal_id).filter(UserGoals.user_id == user_id).all()
