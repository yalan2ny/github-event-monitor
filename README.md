# GitHub Event Monitor with Medallion Architecture

A Python application that monitors GitHub events and provides metrics through a REST API, implemented using the Medallion Architecture pattern.

## Features

- Streams events from the GitHub API
- Implements Medallion Architecture with Bronze, Silver and Gold Layers
- Provides metrics via a REST API:
  - Calculate the average time between pull requests for a given repository
  - Get a list of unique repository names that has more than 1 pull request.
  - Return the total number of events grouped by event type for a given time offset
  - Calculate the most active repositories by event amount in a given time frame.
- Visualization dashboard for metrics using Plotly Dash

## Architecture

The application follows the Medallion Architecture pattern:

1. **Bronze Layer**: Raw data from the GitHub API stored as JSON files
2. **Silver Layer**: Cleaned and structured data in SQLite database
3. **Gold Layer**: Data exposed via APIs that respond to specific business metrics

![Architecture Diagram C4 Level 1](c4_level1.mermaid)

### Data Flow

1. **Bronze Layer Ingestion**:
   - Fetches raw events from GitHub API
   - Stores complete event data as JSON files
   - No filtering or transformation at this stage
   - Files are named with timestamps for easy tracking

2. **Silver Layer Transformation**:
   - Reads raw JSON files from the Bronze layer
   - Transforms data into a structured schema
   - Filters for the events that we are interested in
   - Loads data into a SQLite database

3. **Gold Layer Aggregation**:
   - Aggregates data from the Silver layer
   - Creates business-specific metrics
   - Doesn't store data, just exposed through the APIs. It can be tables or views butit wasn't necessary for this project.
   - Optimized for query performance

## Requirements

- I developed the project on a Windows OS. Please let me know if there are issues with running this on macOS.
- Python 3.11+
- Poetry (version 2.1.2)
- GitHub Personal Access Token (should be put into the .env file)

## Installation

1. Clone the repository
2. Install dependencies with Poetry:

         poetry install


## Running the Application

1. Create a .env file and store your GitHub Personal Access Token there:

         GITHUB_TOKEN=your_github_personal_access_token


2. Run the application with the Data Ingestion and the Dash Interface:

         poetry run python main.py


3. Run the application only with the Dash Interface without Data Ingestion:

         poetry run python main.py --dashboard-only


The application will start on http://localhost:8000 (you might not  see anything here, go to the links below)

- REST API: http://localhost:8000/docs#/
- Visualization Dashboard: http://localhost:8000/dashboard

## Configuration

The application can be configured using environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `GITHUB_TOKEN` | GitHub Personal Access Token | None |
| `COLLECTION_INTERVAL_SECONDS` | Interval between data collection in seconds | 15 |
| `MAX_PAGES_PER_COLLECTION` | Maximum number of pages to fetch per collection | 3 |

## Data Storage

All data is stored locally:

- **Bronze Layer**: JSON files in `./data/bronze/`
- **Silver Layer**: SQLite database at `./data/silver/github_events.db`
- **Gold Layer**: Not stored, exposed through the APIs

## API Endpoints

### Get Average Time Between Pull Requests


      GET /api/repository/{repo}/avg_pr_time


Calculates the average time between pull requests for the specified repository.

### Get Repositories with Multiple PRs


      GET /api/repositories/with_multiple_prs


Returns a list of repositories that had more than 1 Pull Request Event.

### Get Event Count by Type

      GET /api/events/count?offset={minutes}


Returns the count of events grouped by event type for the specified time offset (in minutes).

### Get Active Repositories


     GET /api/repositories/active?limit={limit}&offset={minutes}


Returns the most active repositories based on event count within the specified time offset.

## GitHub API Behavior

### How does the API work?
The GitHub Events API (`https://api.github.com/events`) returns public events that have occurred on GitHub. Each request returns a JSON array of event objects.

### How many rows does it return?
By default, it returns up to 30 events per page. You can't increase this limit beyond 100 per page.

### Do we need to look at multiple pages?
Yes, for comprehensive data collection, we paginate through results. GitHub provides Link headers for pagination. However, GitHub only keeps events for a limited time (a few hours), so there's a finite number of pages.

### Do we catch all events with one query per minute?
No, we won't catch all events, especially during high-activity periods. GitHub generates thousands of events per minute across all repositories. With a 15 second polling interval, we'll capture a subset of events.

To increase coverage, we:
- Paginate through multiple pages per collection (configurable)
- Store all events we encounter to build a more complete dataset over time
- Focus on specific event types in the Gold layer for business metrics

## Assumptions and Limitations

1. **GitHub API Rate Limits**: Without authentication, the GitHub API has strict rate limits (60 requests per hour). With a Personal Access Token, this increases to 5,000 requests per hour.

2. **Data Collection Frequency**: Events are collected every 15 seconds by default. This can be adjusted using the `COLLECTION_INTERVAL_SECONDS` variable in the config.py.

3. **Event Types**: All event types are collected in the Bronze and Silver layers. The Gold layer isexposed through the APIs.

4. **Time Calculations**: All timestamps are stored and processed in UTC.

## Development

### Code Formatting


- poetry run black .
- poetry run isort github_event_monitor/.


### Linting


- poetry run flake8 github_event_monitor/.


## Project Structure


      github_event_monitor/
      ├── __init__.py
      ├── api.py
      ├── config.py
      ├── database.py
      ├── models.py
      ├── pipeline.py
      ├── visualization.py
      └── medallion/
         ├── __init__.py
         ├── bronze.py
         ├── silver.py
         └── gold.py
      main.py
