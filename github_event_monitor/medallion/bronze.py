"""
Bronze Layer Module

This module handles the ingestion of raw data from the GitHub API
and stores it in the bronze layer as JSON files.
"""
import json
import logging
import asyncio
import aiohttp
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from urllib.parse import urlencode

from github_event_monitor import config

logger = logging.getLogger(__name__)

class BronzeLayerIngestion:
    """
    Handles the ingestion of raw data from the GitHub API
    and stores it in the bronze layer as JSON files.
    """
    
    def __init__(self):
        self.api_url = f"{config.GITHUB_API_URL}?{urlencode({'per_page': config.PER_PAGE})}"
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "GitHub-Event-Monitor"
        }
        
        # Add GitHub token if available
        if config.GITHUB_TOKEN:
            self.headers["Authorization"] = f"token {config.GITHUB_TOKEN}"
            logger.info("Using GitHub token for authentication")
        else:
            logger.warning(
                "No GitHub token provided. API rate limits will be restricted. "
                "Set the GITHUB_TOKEN environment variable to increase rate limits."
            )
        
        # Ensure bronze directory exists
        config.BRONZE_DIR.mkdir(exist_ok=True, parents=True)
    
    async def ingest_events(self) -> List[Path]:
        """
        Ingest events from GitHub API and store them in the bronze layer.
        
        Returns:
            List of file paths where the raw data was stored
        """
        try:
            logger.info("Starting bronze layer ingestion")
            stored_files = []
            
            async with aiohttp.ClientSession() as session:
                # Start with the main events URL
                next_url = self.api_url
                page_count = 0
                
                while next_url and page_count < config.MAX_PAGES_PER_COLLECTION:
                    logger.info(f"Fetching page {page_count + 1} from {next_url}")
                    
                    async with session.get(next_url, headers=self.headers) as response:
                        if response.status == 200:
                            # Get the raw events data
                            events_data = await response.json()
                            
                            if not events_data:
                                logger.info("No events found in the response")
                                break
                            
                            # Store the raw data in a JSON file
                            file_path = self._store_raw_data(events_data)
                            stored_files.append(file_path)
                            logger.info(f"Stored {len(events_data)} events in {file_path}")
                            
                            # Check for pagination (Link header)
                            next_url = self._get_next_page_url(response.headers.get("Link", ""))
                            page_count += 1
                            
                            # Respect GitHub's rate limits with a small delay
                            await asyncio.sleep(1)
                        
                        elif response.status == 403:
                            # Rate limit exceeded
                            logger.error("GitHub API rate limit exceeded. Consider adding a GitHub token.")
                            rate_limit_reset = response.headers.get("X-RateLimit-Reset")
                            if rate_limit_reset:
                                reset_time = datetime.fromtimestamp(int(rate_limit_reset))
                                logger.info(f"Rate limit will reset at: {reset_time}")
                            break
                        
                        else:
                            logger.error(f"Failed to fetch events: {response.status}")
                            response_text = await response.text()
                            logger.error(f"Response: {response_text}")
                            break
            
            return stored_files
                        
        except Exception as e:
            logger.error(f"Error in bronze layer ingestion: {str(e)}")
            return []
    
    def _store_raw_data(self, data: List[Dict[str, Any]]) -> Path:
        """
        Store raw data in a JSON file in the bronze layer.
        
        Args:
            data: The raw data to store
            
        Returns:
            Path to the stored file
        """
        file_path = config.get_bronze_file_path()
        
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)
        
        return file_path
    
    def _get_next_page_url(self, link_header: str) -> Optional[str]:
        """
        Extract the next page URL from the Link header.
        
        Args:
            link_header: The Link header from the GitHub API response
            
        Returns:
            The URL of the next page, or None if there is no next page
        """
        if not link_header:
            return None
        
        # Parse the Link header
        links = {}
        for part in link_header.split(","):
            section = part.split(";")
            if len(section) != 2:
                continue
            
            url = section[0].strip()[1:-1]  # Remove < and >
            rel = section[1].strip()
            
            if 'rel="next"' in rel:
                return url
        
        return None
