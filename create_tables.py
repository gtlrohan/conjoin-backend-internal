#!/usr/bin/env python3
"""
Create all database tables directly using SQLAlchemy.
This bypasses the broken Alembic migration chain.
"""
import os
import sys

# Add the app directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.postgres.database import Base, engine

# Import all schema models to ensure they're registered with Base


def create_all_tables():
    """Create all database tables."""
    print("Creating all database tables...")

    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("✅ All tables created successfully!")

        # List created tables
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
