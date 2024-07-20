import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.express as px
import pandas as pd

# Crea un'istanza dell'app Dash
app = dash.Dash(__name__)

# Carica i dati
df = pd.DataFrame({
    "Fruit": ["Apples", "Oranges", "Bananas", "Apples", "Oranges", "Bananas"],
    "Amount": [4, 1, 2, 2, 4, 5],
    "City": ["SF", "SF", "SF", "NYC", "NYC", "NYC"]
})

# Layout dell'app
app.layout = html.Div(children=[
    html.H1(children='Hello Dash'),

    html.Div(children='''
        Dash: A web application framework for Python.
    '''),

    dcc.Dropdown(
        id='city-dropdown',
        options=[
            {'label': 'San Francisco', 'value': 'SF'},
            {'label': 'New York City', 'value': 'NYC'}
        ],
        value='SF'
    ),

    dcc.Graph(
        id='example-graph'
    )
])

# Callback per aggiornare il grafico in base alla città selezionata
@app.callback(
    Output('example-graph', 'figure'),
    [Input('city-dropdown', 'value')]
)
def update_graph(selected_city):
    filtered_df = df[df['City'] == selected_city]
    fig = px.bar(filtered_df, x="Fruit", y="Amount", color="Fruit", barmode="group")
    return fig

# Esegui l'app
if __name__ == '__main__':
    app.run_server(debug=True)
