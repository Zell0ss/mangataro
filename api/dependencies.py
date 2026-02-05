from api.database import SessionLocal
from fastapi import Depends
from sqlalchemy.orm import Session


def get_db():
    """
    Database session dependency for FastAPI routes.

    Yields a database session and ensures it's properly closed after use.
    This is already defined in database.py but re-exported here for clarity.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
