from typing import List
from sqlalchemy.orm import Session

from app.postgres.schema.objective import Objective


def create_objective(db: Session, name: str):
    objective = Objective(name=name)
    db.add(objective)
    db.commit()
    db.refresh(objective)
    return objective


def retrieve_objective_by_id(db: Session, objective_id: int):
    return db.query(Objective).filter(Objective.id == objective_id).first()


def retrieve_objectives(db: Session):
    return db.query(Objective)


def retrieve_user_objectives(db: Session, user_id: int) -> List[Objective]:
    try:
        # Base query to filter by user_id
        query = db.query(Objective).filter(Objective.user_id == user_id)

        return query.all()

    except Exception as e:
        raise e
