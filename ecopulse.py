import dash
from dash import dcc, html, Input, Output
import plotly.graph_objs as go
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Initialize the Dash app
app = dash.Dash(__name__, external_stylesheets=['https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css'])
app.title = "EcoPulse | Real-time Economic Dashboard"

# Mock data generation for demonstration
def generate_mock_data():
    dates = pd.date_range(start='2023-01-01', end=datetime.now(), freq='M')
    data = {
        'Date': dates,
        'GDP_Growth': np.random.normal(2.5, 0.5, len(dates)),
        'Inflation': np.random.normal(3.0, 1.2, len(dates)),
        'Unemployment': np.random.normal(4.5, 0.3, len(dates)),
        'Consumer_Sentiment': np.random.normal(70, 5, len(dates))
    }
    return pd.DataFrame(data)

df = generate_mock_data()

# Layout
app.layout = html.Div([
    # Header
    html.Div([
        html.H1("EcoPulse Dashboard", className="display-4 text-center mt-4"),
        html.P("Real-time monitoring of global economic indicators", className="lead text-center text-muted mb-5"),
    ], className="container"),

    # Main Content
    html.Div([
        html.Div([
            # Sidebar / Controls
            html.Div([
                html.H5("Dashboard Controls", className="card-title"),
                html.Hr(),
                html.Label("Select Indicator:"),
                dcc.Dropdown(
                    id='indicator-dropdown',
                    options=[
                        {'label': 'GDP Growth (%)', 'value': 'GDP_Growth'},
                        {'label': 'Inflation Rate (%)', 'value': 'Inflation'},
                        {'label': 'Unemployment Rate (%)', 'value': 'Unemployment'},
                        {'label': 'Consumer Sentiment', 'value': 'Consumer_Sentiment'}
                    ],
                    value='GDP_Growth',
                    className="mb-3"
                ),
                html.Label("Time Range:"),
                dcc.RangeSlider(
                    id='time-slider',
                    min=0,
                    max=len(df)-1,
                    value=[0, len(df)-1],
                    marks={i: df['Date'].dt.year.iloc[i] for i in range(0, len(df), 6)},
                    step=1
                ),
            ], className="card p-4 shadow-sm mb-4"),
            
            # Key Stats
            html.Div([
                html.Div([
                    html.Div([
                        html.H6("Current GDP Growth", className="text-muted"),
                        html.H3(f"{df['GDP_Growth'].iloc[-1]:.2f}%", className="text-primary")
                    ], className="col-6 border-end text-center"),
                    html.Div([
                        html.H6("Current Inflation", className="text-muted"),
                        html.H3(f"{df['Inflation'].iloc[-1]:.2f}%", className="text-danger")
                    ], className="col-6 text-center"),
                ], className="row p-3")
            ], className="card shadow-sm mb-4")
        ], className="col-md-3"),

        # Main Charts
        html.Div([
            html.Div([
                dcc.Graph(id='main-indicator-chart')
            ], className="card shadow-sm p-3 mb-4"),
            
            html.Div([
                html.Div([
                    html.Div([dcc.Graph(id='mini-chart-1')], className="col-md-6"),
                    html.Div([dcc.Graph(id='mini-chart-2')], className="col-md-6"),
                ], className="row")
            ])
        ], className="col-md-9")
    ], className="row container-fluid px-5")
], className="bg-light min-vh-100")

# Callbacks
@app.callback(
    Output('main-indicator-chart', 'figure'),
    [Input('indicator-dropdown', 'value'),
     Input('time-slider', 'value')]
)
def update_main_chart(selected_indicator, time_range):
    filtered_df = df.iloc[time_range[0]:time_range[1]+1]
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=filtered_df['Date'],
        y=filtered_df[selected_indicator],
        mode='lines+markers',
        name=selected_indicator,
        line=dict(color='#0d6efd', width=3),
        fill='tozeroy'
    ))
    
    fig.update_layout(
        title=f"Trend Analysis: {selected_indicator.replace('_', ' ')}",
        xaxis_title="Date",
        yaxis_title="Value",
        template="plotly_white",
        margin=dict(l=40, r=40, t=60, b=40)
    )
    return fig

@app.callback(
    [Output('mini-chart-1', 'figure'),
     Output('mini-chart-2', 'figure')],
    [Input('time-slider', 'value')]
)
def update_mini_charts(time_range):
    filtered_df = df.iloc[time_range[0]:time_range[1]+1]
    
    fig1 = go.Figure(data=[go.Bar(x=filtered_df['Date'], y=filtered_df['Unemployment'], marker_color='#6c757d')])
    fig1.update_layout(title="Unemployment Rate", template="plotly_white", height=300, margin=dict(l=20, r=20, t=40, b=20))
    
    fig2 = go.Figure(data=[go.Scatter(x=filtered_df['Date'], y=filtered_df['Consumer_Sentiment'], line=dict(color='#ffc107'))])
    fig2.update_layout(title="Consumer Sentiment Index", template="plotly_white", height=300, margin=dict(l=20, r=20, t=40, b=20))
    
    return fig1, fig2

if __name__ == '__main__':
    # For production use: app.run_server(debug=False)
    app.run_server(debug=True, port=8050)
