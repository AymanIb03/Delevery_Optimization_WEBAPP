import os
import pandas as pd
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objs as go

# Obtenez le chemin absolu de la racine du projet
project_root = os.path.abspath(os.path.dirname(__file__))

# Charger les résultats des tournées optimales
tours_file = os.path.join(project_root, 'output', 'tours_optimaux_nearest_neighbor_complet.xlsx')
clusters_file = os.path.join(project_root, 'output', 'adjusted_clusters_final.xlsx')

# Vérifier si les fichiers existent
if not os.path.exists(tours_file):
    print(f"Le fichier {tours_file} n'existe pas.")
    exit()
if not os.path.exists(clusters_file):
    print(f"Le fichier {clusters_file} n'existe pas.")
    exit()

# Charger les données des fichiers Excel
tours_data = pd.read_excel(tours_file)
clusters_data = pd.read_excel(clusters_file)

# Coordonnées du dépôt
depot_coords = (32.471173818912625, -6.811046920662349)

# Créer l'application Dash avec des styles externes
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

# Layout de l'application
app.layout = html.Div([
    # Titre principal stylé (taille réduite)
    html.H1("Visualisation des Tournées Optimales par Cluster",
            style={'textAlign': 'center',
                   'color': '#2c3e50',
                   'fontFamily': 'Roboto, sans-serif',
                   'fontSize': '2.2em',  # Taille réduite
                   'fontWeight': 'bold',
                   'textShadow': '1px 1px 3px rgba(0,0,0,0.1)',
                   'marginBottom': '20px'}),  # Espacement réduit

    # Dropdown stylé avec une taille optimisée (hauteur ajustée)
    html.Div([
        dcc.Dropdown(
            id='cluster-dropdown',
            options=[{'label': f'Cluster {cluster_id}', 'value': cluster_id} for cluster_id in tours_data['Cluster'].unique()],
            value=0,  # Par défaut, afficher le cluster 0
            clearable=False,
            style={
                'width': '50%',  # Largeur inchangée
                'height': '38px',  # Hauteur ajustée
                'lineHeight': '38px',  # Alignement vertical du texte
                'margin': '0 auto',
                'padding': '0',  # Padding interne ajusté
                'fontSize': '1.1em'  # Taille de police inchangée

            }
        ),
    ], style={'display': 'flex', 'justifyContent': 'center', 'marginBottom': '20px'}),  # Espacement réduit

    # Graphique avec une carte OpenStreetMap (taille réduite)
    html.Div([
        dcc.Graph(id='tour-graph', config={'displayModeBar': False})
    ], style={'display': 'flex', 'justifyContent': 'center', 'width': '95%', 'margin': '0 auto', 'padding': '10px', 'borderRadius': '10px', 'boxShadow': '0px 2px 8px rgba(0, 0, 0, 0.1)', 'backgroundColor': '#fff'}),
], style={'backgroundColor': '#ecf0f1', 'padding': '20px', 'boxSizing': 'border-box'})  # Espacement global réduit


# Callback pour mettre à jour la visualisation en fonction du cluster sélectionné
@app.callback(
    Output('tour-graph', 'figure'),
    [Input('cluster-dropdown', 'value')]
)
def update_tour_graph(cluster_id):
    # Filtrer les données du cluster sélectionné
    cluster_tour = tours_data[tours_data['Cluster'] == cluster_id]

    # Extraire le tour sous forme de chaîne et le séparer
    tour_str = cluster_tour['Tour'].values[0]
    client_names = tour_str.split(' -> ')

    # Afficher la chaîne du tour pour vérifier qu'elle contient le dépôt au début et à la fin
    print(f"Tour pour le Cluster {cluster_id} : {tour_str}")

    # Extraire les coordonnées des clients (sauf le dépôt) pour tracer le trajet
    cluster_coords = clusters_data[clusters_data['AdjustedCluster'] == cluster_id][['Latitude', 'Longitude']].values

    # Créer la liste des coordonnées avec le dépôt au début et à la fin
    coords = [depot_coords] + cluster_coords.tolist() + [depot_coords]  # Ajouter le dépôt à la fin

    # Afficher les coordonnées pour débogage
    print(f"Coordonnées du cluster {cluster_id} : {coords}")

    # Créer le plot avec OpenStreetMap
    fig = go.Figure()

    # Tracer les points et les lignes avec OpenStreetMap
    fig.add_trace(go.Scattermapbox(
        lon=[coord[1] for coord in coords],  # Longitude
        lat=[coord[0] for coord in coords],  # Latitude
        mode='markers+lines',
        marker=dict(size=10, color='red', opacity=0.8),  # Taille du marqueur réduite
        line=dict(width=2, color='blue'),  # Taille de la ligne réduite
        text=client_names,  # Affichage des noms des clients
        hoverinfo='text',
        name=f'Cluster {cluster_id}'
    ))

    # Configurer le layout de la carte avec OpenStreetMap
    fig.update_layout(
        title=f'Tour Optimal pour le Cluster {cluster_id}',
        title_x=0.5,
        mapbox=dict(
            style="open-street-map",  # Utiliser OpenStreetMap
            center=dict(lon=depot_coords[1], lat=depot_coords[0]),
            zoom=9,  # Ajuster le zoom pour plus de détails sans trop agrandir la carte
        ),
        width=1000,  # Largeur légèrement réduite
        height=700,  # Hauteur réduite
        margin=dict(l=0, r=0, t=30, b=20),  # Marges réduites
    )

    return fig


# Lancer l'application Dash
if __name__ == '__main__':
    app.run_server(debug=True)
