from dash import Dash, dcc, html, Input, Output, State
import plotly.express as px

import pandas as pd
from django_plotly_dash import DjangoDash

app = DjangoDash('Convergence')   # replaces dash.Dash

app.layout = html.Div([
    dcc.Dropdown(
        id='dropdown',
        options=[],
        value=None
    ),
    html.Button('Update Options', id='button', n_clicks=0)
])


@app.callback(
    Output('dropdown', 'options'),
    [Input('button', 'n_clicks')]
)
def update_options(n_clicks):
    option_name = 'Option {}'.format(n_clicks)
    try:
        existing_options = [{'label': option_name, 'value': option_name}]
    except:
        existing_options = []
    return existing_options
