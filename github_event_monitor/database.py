"""
Database Module

This module handles database connections and provides session management.
"""
import logging
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

# Cache for database engines
_engines = {}


def get_engine(database_url):
    """
    Get or create a database engine for the given URL.

    Args:
        database_url: SQLAlchemy database URL

    Returns:
        Engine instance
    """
    if database_url not in _engines:
        _engines[database_url] = create_engine(
            database_url,
            echo=False,
            connect_args={"check_same_thread": False}
            if "sqlite" in database_url
            else {},
        )
    return _engines[database_url]


@contextmanager
def get_sync_session(engine):
    """
    Get a database session for the given engine.

    Args:
        engine: SQLAlchemy Engine instance

    Yields:
        Session instance
    """
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
