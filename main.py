"""
GitHub Event Monitor - Main Application

This script initializes and runs the GitHub Event Monitor system.
It can run in full mode (ingestion pipeline + API + dashboard)
or dashboard/API-only mode via the --dashboard-only command-line flag.
"""

import argparse
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from github_event_monitor.pipeline import DataPipeline
from github_event_monitor.api import router as api_router
from github_event_monitor.visualization import create_dash_app
from github_event_monitor import config

# ------------------- Command Line Argument Parsing -------------------
parser = argparse.ArgumentParser(description="GitHub Event Monitor entry point.")
parser.add_argument(
    "--dashboard-only",
    action="store_true",
    help="Run only the dashboard and API (no pipeline/scheduler)."
)
args, _ = parser.parse_known_args()
DASHBOARD_ONLY = args.dashboard_only
# ---------------------------------------------------------------------

# ------------------------- Logging Setup -----------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
# ---------------------------------------------------------------------

# ----------------- Data Pipeline & Scheduler Objects -----------------
pipeline = DataPipeline()
scheduler = AsyncIOScheduler()
# ---------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI application.
    Handles startup and shutdown events.
    (Pipeline and scheduler disabled if --dashboard-only is used.)
    """
    try:
        if not DASHBOARD_ONLY:
            # Setup and start pipeline/scheduler
            if not config.GITHUB_TOKEN:
                logger.warning(
                    "No GitHub token provided. API rate limits will be restricted. "
                    "Set the GITHUB_TOKEN environment variable to increase rate limits."
                )
            await pipeline.initialize()
            logger.info("Data pipeline initialized")
            await pipeline.run()
            logger.info("Initial data pipeline run completed")
            scheduler.add_job(
                pipeline.run,
                'interval',
                seconds=config.COLLECTION_INTERVAL_SECONDS,
                id='pipeline_job'
            )
            scheduler.start()
            logger.info(
                f"Data pipeline scheduler started (interval: {config.COLLECTION_INTERVAL_SECONDS} seconds)"
            )
        else:
            logger.info("Running in DASHBOARD ONLY mode: pipeline/scheduler will not start.")
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")

    yield

    try:
        if not DASHBOARD_ONLY:
            if scheduler.running:
                scheduler.shutdown()
                logger.info("Scheduler shutdown")
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")

# ------------------------- FastAPI App Setup ------------------------
app = FastAPI(
    title="GitHub Event Monitor",
    description="A system to monitor GitHub events and provide metrics using Medallion Architecture",
    version="0.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=config.API_PREFIX)

# ------------------------- Dash Dashboard Setup ----------------------
create_dash_app(app)

if __name__ == "__main__":
    import uvicorn
    # Use reload=True for development only; omit for production
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)