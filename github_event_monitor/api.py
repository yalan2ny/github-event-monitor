"""
API Module

Sync version, querying directly from the Silver (events) table.
"""
import logging
from typing import Dict
from fastapi import APIRouter, HTTPException, Query

from sqlalchemy.orm import Session
from sqlalchemy import create_engine, func, desc

from github_event_monitor import config
from github_event_monitor.models import Event

logger = logging.getLogger(__name__)
router = APIRouter()

engine = create_engine(config.SILVER_DB_URL, future=True)


def get_session():
    # Context manager for DB session
    with Session(engine) as session:
        yield session


@router.get("/events/count", response_model=Dict[str, int])
def get_event_count_by_type(
    offset: int = Query(10, description="Time offset in minutes")
):
    """
    Get the count of events grouped by type in the last `offset` minutes.
    """
    try:
        from datetime import datetime, timezone, timedelta

        now = datetime.now(timezone.utc)
        window_start = now - timedelta(minutes=offset)
        with Session(engine) as session:
            rows = (
                session.query(Event.type, func.count().label("cnt"))
                .filter(Event.created_at >= window_start)
                .group_by(Event.type)
                .all()
            )
            return {type_: cnt for type_, cnt in rows}
    except Exception as e:
        logger.error(f"Error getting event counts: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/repositories/active")
def get_active_repositories(
    limit: int = Query(10, description="Number of repositories to return"),
    offset: int = Query(60, description="Time offset in minutes"),
):
    """
    Get the most active repositories (by event count) over the given time window.
    """
    try:
        from datetime import datetime, timezone, timedelta

        now = datetime.now(timezone.utc)
        window_start = now - timedelta(minutes=offset)
        with Session(engine) as session:
            rows = (
                session.query(Event.repo, func.count().label("cnt"))
                .filter(Event.created_at >= window_start)
                .group_by(Event.repo)
                .order_by(desc("cnt"))
                .limit(limit)
                .all()
            )
            return [{"repository": repo, "event_count": cnt} for repo, cnt in rows]
    except Exception as e:
        logger.error(f"Error getting active repos: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/repository/{repo:path}/avg_pr_time")
def get_avg_pr_time(repo: str):
    """
    Compute the average time between PullRequestEvents for the given repository.
    """
    try:
        with Session(engine) as session:
            # Get all PR events for this repo, sorted by time
            pr_events = (
                session.query(Event)
                .filter(Event.repo == repo, Event.type == "PullRequestEvent")
                .order_by(Event.created_at)
                .all()
            )
            if not pr_events or len(pr_events) < 2:
                return {
                    "average_time_seconds": None,
                    "message": "Not enough PRs in this repo",
                }
            # Calculate deltas between successive PRs
            deltas = [
                (pr_events[i].created_at - pr_events[i - 1].created_at).total_seconds()
                for i in range(1, len(pr_events))
            ]
            avg_sec = sum(deltas) / len(deltas)
            return {
                "average_time_seconds": avg_sec,
                "average_time_minutes": avg_sec / 60,
                "average_time_hours": avg_sec / 3600,
                "pr_count": len(pr_events),
            }
    except Exception as e:
        logger.error(f"Error calculating average PR time: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/repositories/with_multiple_prs")
def get_repos_with_multiple_prs():
    try:
        with Session(engine) as session:
            repos = (
                session.query(Event.repo)
                .filter(Event.type == "PullRequestEvent")
                .group_by(Event.repo)
                .having(func.count(Event.id) > 1)
                .order_by(func.count(Event.id).desc())
                .all()
            )
            return [repo[0] for repo in repos]
    except Exception as e:
        logger.error(f"Error fetching repos with >1 PR: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
