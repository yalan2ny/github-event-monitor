"""
Configuration Module

This module contains configuration settings for the application.
"""
import os
from pathlib import Path
from datetime import datetime

# Load environment variables from .env file
from dotenv import load_dotenv

# Base directory - one level up from this file
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file from BASE_DIR (adjust path if your .env is elsewhere)
load_dotenv(BASE_DIR / ".env")

# Data storage paths for Medallion Architecture
DATA_DIR = BASE_DIR / "data"
BRONZE_DIR = DATA_DIR / "bronze"
SILVER_DIR = DATA_DIR / "silver"
GOLD_DIR = DATA_DIR / "gold"

# Ensure directories exist
for directory in [DATA_DIR, BRONZE_DIR, SILVER_DIR, GOLD_DIR]:
    directory.mkdir(exist_ok=True, parents=True)

# Database settings - using local SQLite databases
SILVER_DB_PATH = SILVER_DIR / "github_events.db"
SILVER_DB_URL = f"sqlite+aiosqlite:///{SILVER_DB_PATH}"

# GitHub API settings
GITHUB_API_URL = "https://api.github.com/events"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")  # Personal Access Token for GitHub API
EVENT_TYPES_FILTER = ["WatchEvent", "PullRequestEvent", "IssuesEvent"]  # Only used in Gold layer

# Data collection settings
COLLECTION_INTERVAL_SECONDS = int(os.getenv("COLLECTION_INTERVAL_SECONDS", "15"))
MAX_PAGES_PER_COLLECTION = int(os.getenv("MAX_PAGES_PER_COLLECTION", "3"))
PER_PAGE = int(os.getenv("PER_PAGE", 100))  # 100 is the max for GitHub API

# API settings
API_PREFIX = "/api"

# Dashboard settings
DASHBOARD_PREFIX = "/dashboard"

# Function to generate bronze layer file path
def get_bronze_file_path():
    """Generate a file path for storing raw GitHub events in the bronze layer."""
    timestamp = datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
    return BRONZE_DIR / f"github_events_{timestamp}.json"