#!/usr/bin/env python3
"""
Create all database tables directly using SQLAlchemy.
This bypasses the broken Alembic migration chain.
"""
import sys
import os

# Add the app directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.postgres.database import engine, Base

# Import all schema models to ensure they're registered with Base
from app.postgres.schema.user import User
from app.postgres.schema.card import CardCompletionDetail, CardDetail, UserCard, CardMHCategory, MHCategory
from app.postgres.schema.cognitive_score import CognitiveScore, CognitiveScoreImpact
from app.postgres.schema.external_token import ExternalToken
from app.postgres.schema.fitbit_heart import FitbitHeartLog, FitbitHeartRateZone, FitbitCustomHeartRateZone
from app.postgres.schema.fitbit_sleep import FitbitSleepLog, FitbitSleepLevel, FitbitSleepSummary
from app.postgres.schema.google_calendar import CalendarEvent, EventCreator, EventOrganizer, EventDate, EventAttendee
from app.postgres.schema.objective import Objective
from app.postgres.schema.user_preferences import UserPreferences
from app.postgres.schema.cognitive_fingerprint import CognitiveFingerprint
from app.postgres.schema.voice_therapy import VoiceTherapySession
from app.postgres.schema.gpt import MentorMessage
from app.postgres.schema.goals import Goal, UserGoals, Goals2Card

def create_all_tables():
    """Create all database tables."""
    print("Creating all database tables...")
    
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("✅ All tables created successfully!")
        
        # List created tables
        inspector = engine.dialect.get_foreign_table_names
        print("\n📋 Tables created:")
        for table_name in Base.metadata.tables.keys():
            print(f"  - {table_name}")
            
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = create_all_tables()
    sys.exit(0 if success else 1)
