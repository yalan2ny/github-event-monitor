from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import argparse
import logging
import threading
import time

from github_event_monitor.pipeline import DataPipeline
from github_event_monitor.api import router as api_router
from github_event_monitor.visualization import create_dash_app
from github_event_monitor import config


parser = argparse.ArgumentParser(description="GitHub Event Monitor entry point.")
parser.add_argument(
    "--dashboard-only",
    action="store_true",
    help="Run only the dashboard and API (no pipeline/scheduler).",
)
args, _ = parser.parse_known_args()
DASHBOARD_ONLY = args.dashboard_only

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
pipeline = DataPipeline()


@asynccontextmanager
async def lifespan(app: FastAPI):
    stop_thread = False  # Signal for background thread stop

    def pipeline_loop():
        while not stop_thread:
            try:
                pipeline.run()
            except Exception as e:
                logger.error(f"Pipeline loop error: {e}")
            time.sleep(config.COLLECTION_INTERVAL_SECONDS)

    try:
        if not DASHBOARD_ONLY:
            if not config.GITHUB_TOKEN:
                logger.warning(
                    "No GitHub token provided. API rate limits will be restricted. "
                    "Set the GITHUB_TOKEN environment variable to increase rate limits."
                )
            pipeline.initialize()
            logger.info("Data pipeline initialized")
            # Start background pipeline thread
            thread = threading.Thread(target=pipeline_loop, daemon=True)
            thread.start()
            logger.info("Started background pipeline loop")
        else:
            logger.info(
                "Running in DASHBOARD ONLY mode: pipeline/scheduler will not start."
            )
        yield
    finally:
        # There is no robust thread kill in Python;
        # for production, use a more advanced method (event, etc)
        stop_thread = True
        logger.info("Application shutdown.")

app = FastAPI(
    title="GitHub Event Monitor",
    description="A system to monitor GitHub events and provide metrics using Medallion Architecture",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=config.API_PREFIX)
create_dash_app(app)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
