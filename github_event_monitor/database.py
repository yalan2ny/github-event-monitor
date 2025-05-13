"""
Database Module

This module handles database connections and provides session management.
"""
import logging
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
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
        AsyncEngine instance
    """
    if database_url not in _engines:
        _engines[database_url] = create_async_engine(
            database_url, 
            echo=False,
            connect_args={"check_same_thread": False} if "sqlite" in database_url else {}
        )
    
    return _engines[database_url]

@asynccontextmanager
async def get_session(database_url):
    """
    Get a database session for the given URL.
    
    Args:
        database_url: SQLAlchemy database URL
        
    Yields:
        AsyncSession instance
    """
    engine = get_engine(database_url)
    
    # Create session factory
    async_session = sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    # Create and yield session
    session = async_session()
    try:
        yield session
    finally:
        await session.close()
