"""
Database Models

This module defines the database models for the application.
"""
from sqlalchemy import Column, String, Integer, Boolean, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Event(Base):
    """GitHub event model for the silver layer."""
    
    __tablename__ = "events"
    
    id = Column(String, primary_key=True, index=True)
    type = Column(String, index=True)
    actor = Column(String, index=True)
    actor_id = Column(Integer, index=True)
    repo = Column(String, index=True)
    repo_id = Column(Integer, index=True)
    public = Column(Boolean, default=True)
    created_at = Column(DateTime, index=True)
    payload = Column(JSON)
    
    def __repr__(self):
        return f"<Event(id={self.id}, type={self.type}, repo={self.repo})>"
