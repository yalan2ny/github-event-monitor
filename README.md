# GitHub Event Monitor with Medallion Architecture

A Python application that monitors GitHub events and provides metrics through a REST API, implemented using the Medallion Architecture pattern.

## Features

- Streams events from the GitHub API
- Implements Medallion Architecture (Bronze, Silver, Gold layers)
- Provides metrics via a REST API:
  - Calculate the average time between pull requests for a given repository
  - Return the total number of events grouped by event type for a given time offset
- Visualization dashboard for metrics using Plotly Dash

## Architecture

The application follows the Medallion Architecture pattern:

1. **Bronze Layer**: Raw data from the GitHub API stored as JSON files
2. **Silver Layer**: Cleaned and structured data in SQLite database
3. **Gold Layer**: Business-specific aggregated metrics in SQLite database

![Architecture Diagram](architecture.mermaid)

### Data Flow

1. **Bronze Layer Ingestion**:
   - Fetches raw events from GitHub API
   - Stores complete event data as JSON files
   - No filtering or transformation at this stage
   - Files are named with timestamps for easy tracking

2. **Silver Layer Transformation**:
   - Reads raw JSON files from the Bronze layer
   - Transforms data into a structured schema
   - Loads data into a SQLite database
   - Still contains all events without business filtering

3. **Gold Layer Aggregation**:
   - Aggregates data from the Silver layer
   - Creates business-specific metrics and views
   - Stores results in a separate SQLite database
   - Optimized for query performance

## Requirements

- Python 3.11+
- Poetry (for dependency management)
- GitHub Personal Access Token (for API access)

## Installation

1. Clone the repository
2. Install dependencies with Poetry:
   \`\`\`
   poetry install
   \`\`\`

## Running the Application

1. Set your GitHub Personal Access Token as an environment variable:
   \`\`\`
   export GITHUB_TOKEN=your_github_personal_access_token
   \`\`\`

2. Run the application:
   \`\`\`
   poetry run python main.py
   \`\`\`

The application will start on http://localhost:8000

- REST API: http://localhost:8000/api
- Visualization Dashboard: http://localhost:8000/dashboard

## Configuration

The application can be configured using environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `GITHUB_TOKEN` | GitHub Personal Access Token | None |
| `COLLECTION_INTERVAL_MINUTES` | Interval between data collection in minutes | 1 |
| `MAX_PAGES_PER_COLLECTION` | Maximum number of pages to fetch per collection | 3 |

## Data Storage

All data is stored locally:

- **Bronze Layer**: JSON files in `./data/bronze/`
- **Silver Layer**: SQLite database at `./data/silver/github_events.db`
- **Gold Layer**: SQLite database at `./data/gold/github_metrics.db`

## API Endpoints

### Get Event Count by Type

\`\`\`
GET /api/events/count?offset={minutes}
\`\`\`

Returns the count of events grouped by event type for the specified time offset (in minutes).

### Get Average Time Between Pull Requests

\`\`\`
GET /api/repository/{repo}/avg_pr_time
\`\`\`

Calculates the average time between pull requests for the specified repository.

### Get Active Repositories

\`\`\`
GET /api/repositories/active?limit={limit}&offset={minutes}
\`\`\`

Returns the most active repositories based on event count within the specified time offset.

## GitHub API Behavior

### How does the API work?
The GitHub Events API (`https://api.github.com/events`) returns public events that have occurred on GitHub. Each request returns a JSON array of event objects.

### How many rows does it return?
By default, it returns up to 30 events per page. You can't increase this limit beyond 100 per page.

### Do we need to look at multiple pages?
Yes, for comprehensive data collection, we paginate through results. GitHub provides Link headers for pagination. However, GitHub only keeps events for a limited time (a few hours), so there's a finite number of pages.

### Do we catch all events with one query per minute?
No, we won't catch all events, especially during high-activity periods. GitHub generates thousands of events per minute across all repositories. With a 1-minute polling interval, we'll capture a subset of events.

To increase coverage, we:
- Paginate through multiple pages per collection (configurable)
- Store all events we encounter to build a more complete dataset over time
- Focus on specific event types in the Gold layer for business metrics

## Assumptions and Limitations

1. **GitHub API Rate Limits**: Without authentication, the GitHub API has strict rate limits (60 requests per hour). With a Personal Access Token, this increases to 5,000 requests per hour.

2. **Data Collection Frequency**: Events are collected every minute by default. This can be adjusted using the `COLLECTION_INTERVAL_MINUTES` environment variable.

3. **Event Types**: All event types are collected in the Bronze and Silver layers. The Gold layer focuses on WatchEvent, PullRequestEvent, and IssuesEvent for specific metrics.

4. **Time Calculations**: All timestamps are stored and processed in UTC.

5. **Data Retention**: There is no automatic data cleanup. For long-running deployments, you might want to implement data retention policies.

## Development

### Running Tests

\`\`\`
poetry run pytest
\`\`\`

### Code Formatting

\`\`\`
poetry run black .
poetry run isort .
\`\`\`

### Linting

\`\`\`
poetry run flake8
\`\`\`

## Project Structure

\`\`\`
github_event_monitor/
├── __init__.py           # Package initialization
├── api.py                # REST API endpoints
├── config.py             # Configuration settings
├── database.py           # Database connection utilities
├── models.py             # SQLAlchemy models
├── pipeline.py           # Data pipeline orchestration
├── visualization.py      # Dash visualization dashboard
└── medallion/            # Medallion architecture implementation
    ├── __init__.py
    ├── bronze.py         # Bronze layer (raw data ingestion)
    ├── silver.py         # Silver layer (data transformation)
    └── gold.py           # Gold layer (business metrics)
