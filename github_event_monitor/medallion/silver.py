"""
Silver Layer Module

This module transforms raw data from the bronze layer
and loads it into the silver layer database.
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy import select

from github_event_monitor import config
from github_event_monitor.models import Base, Event
from github_event_monitor.database import get_engine, get_session

logger = logging.getLogger(__name__)

class SilverLayerTransformation:
    """
    Transforms raw data from the bronze layer
    and loads it into the silver layer database.
    """
    
    async def initialize(self):
        """Initialize the silver layer database."""
        engine = get_engine(config.SILVER_DB_URL)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info(f"Silver layer database initialized at {config.SILVER_DB_PATH}")
    
    async def process_bronze_files(self, file_paths: List[Path]) -> int:
        """
        Process bronze layer files and load them into the silver layer.
        
        Args:
            file_paths: List of bronze layer file paths to process
            
        Returns:
            Number of events processed
        """
        total_processed = 0
        
        for file_path in file_paths:
            try:
                # Read the bronze layer file
                with open(file_path, "r") as f:
                    events_data = json.load(f)
                
                # Transform and load the data
                processed = await self._transform_and_load(events_data)
                total_processed += processed
                
                logger.info(f"Processed {processed} events from {file_path}")
                
            except Exception as e:
                logger.error(f"Error processing bronze file {file_path}: {str(e)}")
        
        return total_processed
    
    async def _transform_and_load(self, events_data: List[Dict[str, Any]]) -> int:
        """
        Transform raw events data and load it into the silver layer.
        
        Args:
            events_data: Raw events data from the bronze layer
            
        Returns:
            Number of events processed
        """
        if not events_data:
            return 0
        
        processed_count = 0
        
        async with get_session(config.SILVER_DB_URL) as session:
            for event_data in events_data:
                try:
                    # Check if event already exists
                    event_id = event_data.get("id")
                    if not event_id:
                        logger.warning(f"Event missing ID: {event_data}")
                        continue
                    
                    existing = await session.execute(
                        select(Event).where(Event.id == event_id)
                    )
                    if existing.scalar_one_or_none():
                        continue
                    
                    # Transform the event data
                    event = self._transform_event(event_data)
                    if not event:
                        continue
                    
                    # Insert the event
                    stmt = insert(Event).values(**event)
                    await session.execute(stmt)
                    processed_count += 1
                    
                except Exception as e:
                    logger.error(f"Error processing event: {str(e)}")
            
            # Commit the transaction
            await session.commit()
        
        return processed_count
    
    def _transform_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform a raw event into the silver layer schema. Remove events with unknown types.
        This function also handles the conversion of date strings to datetime objects.
        It validates the required fields and logs any issues.
        The function returns None if the event is invalid or if an error occurs during transformation.
        
        Args:
            event_data: Raw event data
            
        Returns:
            Transformed event data
        """
        try:

            # Filter by event type
            event_type = event_data.get("type")
            if event_type not in config.EVENT_TYPES_FILTER:
                logger.debug(f"Skipping event with unknown type '{event_type}': {event_data.get('id')}")
                return None

            # Extract basic fields
            event = {
                "id": event_data.get("id"),
                "type": event_data.get("type"),
                "actor": event_data.get("actor", {}).get("login"),
                "actor_id": event_data.get("actor", {}).get("id"),
                "repo": event_data.get("repo", {}).get("name"),
                "repo_id": event_data.get("repo", {}).get("id"),
                "public": event_data.get("public", True),
                "created_at": datetime.strptime(
                    event_data.get("created_at"), 
                    "%Y-%m-%dT%H:%M:%SZ"
                ).replace(tzinfo=timezone.utc),
                "payload": event_data.get("payload", {})
            }
            
            # Validate required fields
            if not all([event["id"], event["type"], event["actor"], event["repo"], event["created_at"]]):
                logger.warning(f"Event missing required fields: {event}")
                return None
            
            return event
            
        except Exception as e:
            logger.error(f"Error transforming event: {str(e)}")
            return None
