from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.constants import DATABASE_URL

# Create a SQLAlchemy engine with connection pool configuration
engine = create_engine(
    DATABASE_URL,
    pool_size=10,  # Number of connections to maintain persistently
    max_overflow=20,  # Additional connections allowed beyond pool_size
    pool_timeout=30,  # Seconds to wait before giving up on getting connection
    pool_recycle=3600,  # Seconds after which connection is recreated
    pool_pre_ping=True,  # Validate connections before use
)

# Create a session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create a declarative base
Base = declarative_base()


# Dependency to get a database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
