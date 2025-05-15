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

from sqlalchemy.dialects.sqlite import insert
from sqlalchemy import select

from github_event_monitor import config
from github_event_monitor.models import Base, Event
from github_event_monitor.database import get_engine, get_sync_session

logger = logging.getLogger(__name__)


class SilverLayerTransformation:
    """
    Transforms raw data from the bronze layer
    and loads it into the silver layer database.
    """

    def initialize(self):
        engine = get_engine(config.SILVER_DB_URL)
        with engine.begin() as conn:
            Base.metadata.create_all(bind=conn)
        logger.info(f"Silver layer database initialized at {config.SILVER_DB_PATH}")

    def process_bronze_files(self, file_paths: List[Path]) -> int:
        total_processed = 0
        for file_path in file_paths:
            try:
                with open(file_path, "r") as f:
                    events_data = json.load(f)

                processed = self._transform_and_load(events_data)
                total_processed += processed

                logger.info(f"Processed {processed} events from {file_path}")
            except Exception as e:
                logger.error(f"Error processing bronze file {file_path}: {str(e)}")
        return total_processed

    def _transform_and_load(self, events_data: List[Dict[str, Any]]) -> int:
        if not events_data:
            return 0

        processed_count = 0
        engine = get_engine(config.SILVER_DB_URL)
        with get_sync_session(engine) as session:
            for event_data in events_data:
                try:
                    event_id = event_data.get("id")
                    if not event_id:
                        logger.warning(f"Event missing ID: {event_data}")
                        continue

                    existing = session.execute(
                        select(Event).where(Event.id == event_id)
                    ).scalar_one_or_none()
                    if existing:
                        continue

                    event = self._transform_event(event_data)
                    if not event:
                        continue

                    stmt = insert(Event).values(**event)
                    session.execute(stmt)
                    processed_count += 1
                except Exception as e:
                    logger.error(f"Error processing event: {str(e)}")
            session.commit()
        return processed_count

    def _transform_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            event_type = event_data.get("type")
            if event_type not in config.EVENT_TYPES_FILTER:
                logger.debug(
                    f"Skipping event with unknown type '{event_type}': {event_data.get('id')}"
                )
                return None
            event = {
                "id": event_data.get("id"),
                "type": event_data.get("type"),
                "actor": event_data.get("actor", {}).get("login"),
                "actor_id": event_data.get("actor", {}).get("id"),
                "repo": event_data.get("repo", {}).get("name"),
                "repo_id": event_data.get("repo", {}).get("id"),
                "public": event_data.get("public", True),
                "created_at": datetime.strptime(
                    event_data.get("created_at"), "%Y-%m-%dT%H:%M:%SZ"
                ).replace(tzinfo=timezone.utc),
                "payload": event_data.get("payload", {}),
            }
            if not all(
                [
                    event["id"],
                    event["type"],
                    event["actor"],
                    event["repo"],
                    event["created_at"],
                ]
            ):
                logger.warning(f"Event missing required fields: {event}")
                return None
            return event
        except Exception as e:
            logger.error(f"Error transforming event: {str(e)}")
            return None
