"""
Bronze Layer Module

This module handles the ingestion of raw data from the GitHub API
and stores it in the bronze layer as JSON files.
"""
import json
import logging
import time
import requests
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
from urllib.parse import urlencode

from github_event_monitor import config

logger = logging.getLogger(__name__)


class BronzeLayerIngestion:
    """
    Handles the ingestion of raw data from the GitHub API
    and stores it in the bronze layer as JSON files.
    """

    def __init__(self):
        self.api_url = (
            f"{config.GITHUB_API_URL}?{urlencode({'per_page': config.PER_PAGE})}"
        )
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "GitHub-Event-Monitor",
        }
        if config.GITHUB_TOKEN:
            self.headers["Authorization"] = f"token {config.GITHUB_TOKEN}"
            logger.info("Using GitHub token for authentication")
        else:
            logger.warning(
                "No GitHub token provided. API rate limits will be restricted. "
                "Set the GITHUB_TOKEN environment variable to increase rate limits."
            )
        config.BRONZE_DIR.mkdir(exist_ok=True, parents=True)

    def ingest_events(self) -> List[Path]:
        """
        Ingest events from GitHub API and store them in the bronze layer.
        Returns: List of file paths where the raw data was stored
        """
        try:
            logger.info("Starting bronze layer ingestion")
            stored_files = []
            next_url = self.api_url
            page_count = 0

            while next_url and page_count < config.MAX_PAGES_PER_COLLECTION:
                logger.info(f"Fetching page {page_count + 1} from {next_url}")
                response = requests.get(next_url, headers=self.headers)
                if response.status_code == 200:
                    events_data = response.json()
                    if not events_data:
                        logger.info("No events found in the response")
                        break
                    file_path = self._store_raw_data(events_data)
                    stored_files.append(file_path)
                    logger.info(f"Stored {len(events_data)} events in {file_path}")

                    next_url = self._get_next_page_url(response.headers.get("Link", ""))
                    page_count += 1
                    time.sleep(1)

                elif response.status_code == 403:
                    logger.error(
                        "GitHub API rate limit exceeded. Consider adding a GitHub token."
                    )
                    rate_limit_reset = response.headers.get("X-RateLimit-Reset")
                    if rate_limit_reset:
                        reset_time = datetime.fromtimestamp(int(rate_limit_reset))
                        logger.info(f"Rate limit will reset at: {reset_time}")
                    break
                else:
                    logger.error(f"Failed to fetch events: {response.status_code}")
                    logger.error(f"Response: {response.text}")
                    break
            return stored_files

        except Exception as e:
            logger.error(f"Error in bronze layer ingestion: {str(e)}")
            return []

    def _store_raw_data(self, data: List[Dict[str, Any]]) -> Path:
        file_path = config.get_bronze_file_path()
        with open(file_path, "w") as f:
            json.dump(data, f)
        return file_path

    def _get_next_page_url(self, link_header: str) -> str:
        if 'rel="next"' in link_header:
            for part in link_header.split(","):
                if 'rel="next"' in part:
                    url_part = part.split(";")[0].strip().strip("<>")
                    return url_part
        return None
