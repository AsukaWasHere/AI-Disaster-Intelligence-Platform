"""
models.py
---------
SQLAlchemy ORM models for the application.
Currently defines the User model for authentication.
"""

from sqlalchemy import Column, Integer, String, Text
from .database import Base


class User(Base):
    """User model for authentication."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="Intelligence Officer")

    def __repr__(self):
        return f"<User(username='{self.username}', role='{self.role}')>"
