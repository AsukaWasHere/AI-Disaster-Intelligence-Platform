"""
database.py
-----------
Database configuration using SQLAlchemy with SQLite.
Provides engine, session factory, and declarative base.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# SQLite database URL (file-based, persistent)
DATABASE_URL = "sqlite:///./ai_disaster.db"

# Create engine with SQLite-specific options for thread safety
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

# SessionLocal: Factory for database sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all model classes
Base = declarative_base()

# Get database session (dependency)
def get_db():
    """Yields a database session and ensures cleanup."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
