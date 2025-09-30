from datetime import datetime
from sqlalchemy.orm import Session
from werkzeug.security import check_password_hash, generate_password_hash

from app.postgres.models.user import UserCreate
from app.postgres.schema.user import User


def create_user(db: Session, user: UserCreate):
    # Hash the password
    hash_pass = generate_password_hash(user.password, method="scrypt")
    db_user = User(
        email=user.email,
        password=hash_pass,
        firstname=user.firstname,
        surname=user.surname,
        completed_morning_orientation=False,
        completed_morning_orientation_date=None,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def retrieve_user_by_id(db: Session, user_id: str):
    # Get the user
    user = db.query(User).filter(User.user_id == user_id).first()

    if user and user.completed_morning_orientation and user.completed_morning_orientation_date:
        # Get current date (without time)
        current_date = datetime.utcnow().date()

        # Get orientation date (without time)
        orientation_date = user.completed_morning_orientation_date.date()

        # Check if current date is at least one day ahead of orientation date
        if current_date > orientation_date:
            # Reset the orientation status
            user.completed_morning_orientation = False
            user.completed_morning_orientation_date = None

            # Commit the changes
            db.commit()

            # Refresh the user object to ensure it reflects the latest changes
            db.refresh(user)

    return user


def authenticate_user(db: Session, user: UserCreate):
    # Query the database to find a user with the given email
    db_user = db.query(User).filter(User.email == user.email).first()

    if db_user is None:
        # User with the provided email does not exist
        return None

    # Verify the provided password against the hashed password in the database
    if not check_password_hash(db_user.password, user.password):
        # Passwords do not match
        return None

    # Authentication successful; return the user object
    return db_user


def update_morning_orientation_status(db: Session, user_id: int, completed: bool):
    try:
        # Get the user
        user = db.query(User).filter(User.user_id == user_id).first()

        if user is None:
            return None

        # Update the completion status
        user.completed_morning_orientation = completed
        if completed:
            user.completed_morning_orientation_date = datetime.utcnow()
        else:
            user.completed_morning_orientation_date = None

        # Commit the changes
        db.commit()

    except Exception as e:
        db.rollback()
        raise e
