from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.postgres.database import Base
from app.postgres.schema.card import CardDetail
from app.postgres.schema.user import User


class Goal(Base):
    __tablename__ = "Goal"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    # Relationship with UserGoals
    user_goals = relationship("UserGoals", back_populates="goal")
    # Relationship with Goals2Card
    goals_to_cards = relationship("Goals2Card", back_populates="goal")

    def __repr__(self):
        return f"Goal(id={self.id}, name='{self.name}')"

    def __str__(self):
        return f"Goal: {self.name} (ID: {self.id})"


class UserGoals(Base):
    __tablename__ = "UserGoals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("User.user_id"), nullable=False)
    goal_id = Column(Integer, ForeignKey("Goal.id"), nullable=False)
    target = Column(Integer, nullable=True)
    completed = Column(Integer, nullable=True, default=0)
    # Relationships
    user = relationship("User", back_populates="user_goals")
    goal = relationship("Goal", back_populates="user_goals")

    def __repr__(self):
        return f"UserGoals(id={self.id}, user_id={self.user_id}, goal_id={self.goal_id}, target={self.target})"

    def __str__(self):
        return f"User Goal: User ID {self.user_id} - Goal ID {self.goal_id} (Target: {self.target or 'Not set'})"


class Goals2Card(Base):
    __tablename__ = "Goals2Card"

    id = Column(Integer, primary_key=True, index=True)
    goal_id = Column(Integer, ForeignKey("Goal.id"), nullable=False)
    card_id = Column(Integer, ForeignKey("CardDetail.id"), nullable=False)
    # Relationships
    goal = relationship("Goal", back_populates="goals_to_cards")
    card_detail = relationship("CardDetail", back_populates="goals_to_card")

    def __repr__(self):
        return f"Goals2Card(id={self.id}, goal_id={self.goal_id}, card_id={self.card_id})"

    def __str__(self):
        return f"Goal-Card Link: Goal ID {self.goal_id} - Card ID {self.card_id}"


# Update relationships in existing classes
User.user_goals = relationship("UserGoals", back_populates="user")
CardDetail.goals_to_card = relationship("Goals2Card", back_populates="card_detail")
