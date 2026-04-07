"""
deps.py
-------
Database dependency functions for FastAPI route handlers.
"""

from sqlalchemy.orm import Session
from .database import SessionLocal


def get_db_session() -> Session:
    """
    FastAPI dependency that yields a database session.

    Usage in routes:
        @router.get("/items")
        def read_items(db: Session = Depends(get_db_session)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
