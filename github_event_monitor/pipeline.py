"""
Data Pipeline Module

This module orchestrates the data flow through the simplified medallion architecture.
"""
import logging
from datetime import datetime, timezone

from github_event_monitor.medallion.bronze import BronzeLayerIngestion
from github_event_monitor.medallion.silver import SilverLayerTransformation

logger = logging.getLogger(__name__)


class DataPipeline:
    """
    Orchestrates the data flow through the bronze and silver layers.
    """

    def __init__(self):
        self.bronze = BronzeLayerIngestion()
        self.silver = SilverLayerTransformation()

    def initialize(self):
        """Initialize the pipeline components."""
        self.silver.initialize()
        logger.info("Data pipeline initialized")

    def run(self):
        """Run the complete data pipeline."""
        try:
            start_time = datetime.now(timezone.utc)
            logger.info(f"Starting data pipeline run at {start_time}")

            # Bronze layer: Ingest raw data
            bronze_files = self.bronze.ingest_events()
            logger.info(f"Bronze layer ingestion completed: {len(bronze_files)} files")

            if not bronze_files:
                logger.info("No new data to process")
                return

            # Silver layer: Transform and load data
            processed_count = self.silver.process_bronze_files(bronze_files)
            logger.info(
                f"Silver layer transformation completed: {processed_count} events processed"
            )

            end_time = datetime.now(timezone.utc)
            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()
            logger.info(f"Data pipeline run completed in {duration:.2f} seconds")

        except Exception as e:
            logger.error(f"Error in data pipeline: {str(e)}")
