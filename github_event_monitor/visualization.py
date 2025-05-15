import pandas as pd
import requests
import logging

from dash import Dash, html, dcc, Input, Output, State
import plotly.express as px
import plotly.graph_objects as go

API_BASE = "http://localhost:8000/api"  # Change as needed
logger = logging.getLogger("visualization")

dash_app = Dash(__name__, requests_pathname_prefix="/dashboard/")

dash_app.layout = html.Div(
    [
        html.H1("GitHub Event Monitor Dashboard"),
        html.Button(
            "Refresh", id="refresh-btn", n_clicks=0, style={"marginBottom": "16px"}
        ),
        html.Div(
            [
                html.Div(
                    [
                        html.H2("Event Distribution by Type"),
                        html.P(
                            "Shows the distribution of different event types over a time window."
                        ),
                        html.Div(
                            [
                                html.Label(
                                    "Time window (minutes):",
                                    style={"marginRight": "8px"},
                                ),
                                dcc.Input(
                                    id="event-type-offset-input",
                                    type="number",
                                    value=1440,
                                    min=1,
                                    step=1,
                                    style={"width": "80px", "marginRight": "16px"},
                                ),
                                html.Span(
                                    "e.g. 60 for last hour, 1440 for last 24 hours"
                                ),
                            ],
                            style={"marginBottom": "8px"},
                        ),
                        dcc.Graph(id="event-type-chart"),
                    ],
                    className="chart-container",
                ),
                html.Div(
                    [
                        html.H2("Most Active Repositories"),
                        html.P(
                            "Top repositories by event count in selected time period"
                        ),
                        html.Div(
                            [
                                html.Label(
                                    "Time window (minutes):",
                                    style={"marginRight": "8px"},
                                ),
                                dcc.Input(
                                    id="active-repos-offset-input",
                                    type="number",
                                    value=60,
                                    min=1,
                                    step=1,
                                    style={"width": "80px", "marginRight": "16px"},
                                ),
                                html.Span(
                                    "e.g. 60 for last hour, 1440 for last 24 hours"
                                ),
                            ],
                            style={"marginBottom": "8px"},
                        ),
                        dcc.Graph(id="active-repos-chart"),
                    ],
                    className="chart-container",
                ),
            ],
            className="chart-row",
        ),
        html.Hr(),
        html.H2("Average Pull Request Interval (per repository)"),
        html.Div(
            [
                html.Label("Repository:", style={"marginRight": "8px"}),
                dcc.Dropdown(
                    id="repo-pr-dropdown",
                    options=[],  # Populated via callback
                    placeholder="Select a repository…",
                    style={
                        "width": "350px",
                        "display": "inline-block",
                        "marginRight": "16px",
                    },
                ),
                html.Button("Load", id="load-pr-avg-btn", n_clicks=0),
            ]
        ),
        html.Div(id="avg-pr-time-output", style={"marginTop": "16px"}),
    ]
)


# ---- Event type chart ----
@dash_app.callback(
    Output("event-type-chart", "figure"),
    Input("refresh-btn", "n_clicks"),
    State("event-type-offset-input", "value"),
)
def update_event_type_chart(n_clicks, offset):
    if offset is None or offset < 1:
        offset = 1440
    try:
        resp = requests.get(
            f"{API_BASE}/events/count", params={"offset": offset}, timeout=10
        )
        counts = resp.json()
        if not counts:
            return go.Figure().update_layout(
                title="No events found in the selected time window",
                template="plotly_white",
            )
        df = pd.DataFrame([{"type": k, "count": v} for k, v in counts.items()])
        fig = px.pie(
            df,
            values="count",
            names="type",
            title=f"Event Distribution by Type (Last {offset} minutes)",
            color_discrete_sequence=px.colors.qualitative.Plotly,
        )
        fig.update_traces(textposition="inside", textinfo="percent+label")
        fig.update_layout(
            template="plotly_white",
            legend_title="Event Type",
            margin=dict(t=50, b=0, l=0, r=0),
        )
        return fig
    except Exception as e:
        logger.error(f"Error updating event type chart: {e}")
        return go.Figure().update_layout(
            title="Error loading data", template="plotly_white"
        )


# ---- Active repos chart ----
@dash_app.callback(
    Output("active-repos-chart", "figure"),
    Input("refresh-btn", "n_clicks"),
    State("active-repos-offset-input", "value"),
)
def update_active_repos_chart(n_clicks, minutes):
    if minutes is None or minutes < 1:
        minutes = 60
    try:
        resp = requests.get(
            f"{API_BASE}/repositories/active",
            params={"limit": 10, "offset": minutes},
            timeout=10,
        )
        repos = resp.json()
        if not repos:
            return go.Figure().update_layout(
                title="No active repositories found in the selected time period",
                template="plotly_white",
            )
        df = pd.DataFrame(repos)
        fig = px.bar(
            df,
            y="repository",
            x="event_count",
            orientation="h",
            title=f"Top 10 Active Repositories (Last {minutes} minutes)",
            color="event_count",
            color_continuous_scale="Viridis",
        )
        fig.update_layout(
            template="plotly_white",
            yaxis_title="Repository",
            xaxis_title="Event Count",
            margin=dict(t=50, b=0, l=0, r=0),
        )
        return fig
    except Exception as e:
        logger.error(f"Error updating active repos chart: {e}")
        return go.Figure().update_layout(
            title="Error loading data", template="plotly_white"
        )


# ---- PR Average Interval Visual ----
@dash_app.callback(
    Output("repo-pr-dropdown", "options"),
    Input("refresh-btn", "n_clicks"),
)
def update_repo_pr_dropdown(_):
    try:
        resp = requests.get(f"{API_BASE}/repositories/with_multiple_prs")
        repos = resp.json()
        return [{"label": repo, "value": repo} for repo in repos]
    except Exception as e:
        logger.error(f"Error fetching repo list for PR avg: {e}")
        return []


@dash_app.callback(
    Output("avg-pr-time-output", "children"),
    Input("load-pr-avg-btn", "n_clicks"),
    State("repo-pr-dropdown", "value"),
    prevent_initial_call=True,
)
def display_avg_pr_time(n_clicks, repo_name):
    if not repo_name:
        return ""
    try:
        r = requests.get(f"{API_BASE}/repository/{repo_name}/avg_pr_time")
        data = r.json()
        if data.get("average_time_seconds") is None:
            return html.Div(
                f"{data.get('message', 'No data available')}", style={"color": "orange"}
            )
        else:
            return html.Div(
                [
                    html.Div(f"PR count: {data['pr_count']}"),
                    html.Div(
                        f"Average interval: {data['average_time_seconds']:.1f} seconds "
                        f"({data['average_time_minutes']:.2f} minutes, {data['average_time_hours']:.2f} hours)"
                    ),
                ]
            )
    except Exception as e:
        logger.error(f"Error fetching avg PR time: {str(e)}")
        return html.Div("Error retrieving data", style={"color": "red"})


if __name__ == "__main__":
    dash_app.run_server(debug=True)


def create_dash_app(fastapi_app):
    """
    Mounts the Dash app to the given FastAPI app at '/dashboard'.
    """
    from starlette.middleware.wsgi import WSGIMiddleware

    if not hasattr(fastapi_app, "mount"):
        raise ValueError("Argument must be a FastAPI app instance.")

    # Dash app is already constructed globally as `dash_app`
    fastapi_app.mount("/dashboard", WSGIMiddleware(dash_app.server))
