import logging
import requests
import dash
from dash import html, dcc, Input, Output, State
import plotly.express as px
import plotly.graph_objs as go
import pandas as pd

# Set this to your API's base URL
API_BASE = "http://localhost:8000/api"

logger = logging.getLogger(__name__)
dash_app = dash.Dash(__name__)

dash_app.layout = html.Div([
    html.H1("GitHub Event Monitor Dashboard"),
    html.Button("Refresh", id="refresh-btn", n_clicks=0, style={"marginBottom": "16px"}),
    
    html.Div([
        html.Div([
            html.H2("Event Distribution by Type"),
            html.P("Shows the distribution of different event types over a time window."),
            html.Div([
                html.Label("Time window (minutes):", style={"marginRight": "8px"}),
                dcc.Input(
                    id="event-type-offset-input",
                    type="number",
                    value=1440,
                    min=1,
                    step=1,
                    style={"width": "80px", "marginRight": "16px"}
                ),
                html.Span("e.g. 60 for last hour, 1440 for last 24 hours"),
            ], style={"marginBottom": "8px"}),
            dcc.Graph(id="event-type-chart"),
        ], className="chart-container"),
        
        html.Div([
            html.H2("Most Active Repositories"),
            html.P("Top repositories by event count in selected time period"),
            dcc.Dropdown(
                id="time-period-dropdown",
                options=[
                    {"label": "Last Hour", "value": 60},
                    {"label": "Last 24 Hours", "value": 1440},
                ],
                value=60,
                clearable=False
            ),
            dcc.Graph(id="active-repos-chart")
        ], className="chart-container"),
    ], className="chart-row"),
])

@dash_app.callback(
    Output("event-type-chart", "figure"),
    Input("refresh-btn", "n_clicks"),
    State("event-type-offset-input", "value"),
)
def update_event_type_chart(n_clicks, offset):
    if offset is None or offset < 1:
        offset = 1440
    try:
        resp = requests.get(f"{API_BASE}/events/count", params={"offset": offset}, timeout=10)
        counts = resp.json()
        if not counts:
            return go.Figure().update_layout(
                title="No events found in the selected time window",
                template="plotly_white"
            )
        df = pd.DataFrame([{"type": k, "count": v} for k, v in counts.items()])
        fig = px.pie(
            df,
            values="count",
            names="type",
            title=f"Event Distribution by Type (Last {offset} minutes)",
            color_discrete_sequence=px.colors.qualitative.Plotly
        )
        fig.update_traces(textposition="inside", textinfo="percent+label")
        fig.update_layout(
            template="plotly_white",
            legend_title="Event Type",
            margin=dict(t=50, b=0, l=0, r=0)
        )
        return fig
    except Exception as e:
        logger.error(f"Error updating event type chart: {e}")
        return go.Figure().update_layout(title="Error loading data", template="plotly_white")

@dash_app.callback(
    Output("active-repos-chart", "figure"),
    Input("refresh-btn", "n_clicks"),
    State("time-period-dropdown", "value"),
)
def update_active_repos_chart(n_clicks, minutes):
    try:
        resp = requests.get(f"{API_BASE}/repositories/active", params={"limit": 10, "offset": minutes}, timeout=10)
        repos = resp.json()
        if not repos:
            return go.Figure().update_layout(
                title=f"No active repositories found in the selected time period",
                template="plotly_white"
            )
        df = pd.DataFrame(repos)
        fig = px.bar(
            df,
            y="repository",
            x="event_count",
            orientation="h",
            title=f"Top 10 Active Repositories (Last {minutes} minutes)",
            color="event_count",
            color_continuous_scale="Viridis"
        )
        fig.update_layout(
            template="plotly_white",
            yaxis_title="Repository",
            xaxis_title="Event Count",
            margin=dict(t=50, b=0, l=0, r=0)
        )
        return fig
    except Exception as e:
        logger.error(f"Error updating active repos chart: {e}")
        return go.Figure().update_layout(title="Error loading data", template="plotly_white")


if __name__ == "__main__":
    dash_app.run_server(debug=True)