import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from math import radians, sin, cos, sqrt, atan2
from collections import defaultdict
import sys  # Pour récupérer les chemins des fichiers depuis Flask

# Charger le fichier ajusté des clusters après clustering
adjusted_clusters_file = sys.argv[1]  # Fichier 'adjusted_clusters_final.xlsx' généré par le clustering

# Coordonnées du dépôt
depot_coords = (32.471173818912625, -6.811046920662349)

# Charger les données ajustées après clustering
df = pd.read_excel(adjusted_clusters_file)

# Fonction pour calculer la distance géodésique avec la formule de Haversine
def calculate_distance(coord1: tuple, coord2: tuple) -> float:
    R = 6371.0  # Rayon moyen de la Terre en km

    lat1, lon1 = radians(coord1[0]), radians(coord1[1])
    lat2, lon2 = radians(coord2[0]), radians(coord2[1])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    distance = R * c
    return distance

# Fonction pour générer le graphe des distances entre le dépôt et chaque client
def build_graph(df: pd.DataFrame, depot_coords: tuple) -> defaultdict:
    graph = defaultdict(list)

    for _, row in df.iterrows():
        client_id = row['Partner ID']
        client_coords = (row['Latitude'], row['Longitude'])
        distance = calculate_distance(depot_coords, client_coords)

        # Afficher la distance calculée pour chaque client
        print(f"Distance du dépôt vers {row['Partner Name']} ({client_id}): {distance:.2f} km")

        # Ajouter chaque client dans le graphe avec la distance du dépôt
        graph['Depot'].append((client_id, distance))
        graph[client_id] = []  # Initialiser la liste vide pour chaque client

    return graph

# Implémentation de Bellman-Ford pour trouver les distances minimales
def bellman_ford(graph: defaultdict, source: str) -> dict:
    dist = {node: float('inf') for node in graph}
    dist[source] = 0

    for _ in range(len(graph) - 1):
        for u in graph:
            for v, weight in graph[u]:
                if dist[u] + weight < dist[v]:
                    dist[v] = dist[u] + weight

    return dist

# Trouver le client le plus proche du dépôt pour chaque cluster
def find_nearest_clients(df: pd.DataFrame, depot_coords: tuple) -> pd.DataFrame:
    graph = build_graph(df, depot_coords)
    distances = bellman_ford(graph, 'Depot')

    results = []
    for cluster_id in df['AdjustedCluster'].unique():
        cluster_df = df[df['AdjustedCluster'] == cluster_id]
        nearest_client = None
        min_distance = float('inf')

        for _, row in cluster_df.iterrows():
            client_id = row['Partner ID']
            if client_id in distances and distances[client_id] < min_distance:
                min_distance = distances[client_id]
                nearest_client = client_id

        results.append({
            'Cluster': cluster_id,
            'Nearest Client ID': nearest_client,
            'Distance from Depot (km)': min_distance
        })

    return pd.DataFrame(results)

# Exécuter la fonction pour obtenir les clients les plus proches
nearest_clients_df = find_nearest_clients(df, depot_coords)

# Affichage des résultats
print(nearest_clients_df)

# Sauvegarder les résultats dans un fichier Excel
nearest_clients_excel_path = "scripts/output/nearest_clients_from_depot_bellman_ford.xlsx"
nearest_clients_df.to_excel(nearest_clients_excel_path, index=False)
print(f"Fichier Excel enregistré : {nearest_clients_excel_path}")

# Visualisation des résultats et sauvegarde de la carte
plt.figure(figsize=(10, 6))

# Tracer le dépôt
plt.scatter(depot_coords[1], depot_coords[0], c='red', marker='x', s=100, label='Dépôt')

# Extraire les coordonnées des clients les plus proches
nearest_clients = df[df['Partner ID'].isin(nearest_clients_df['Nearest Client ID'])]

# Tracer les clients les plus proches du dépôt dans chaque cluster
for _, row in nearest_clients.iterrows():
    plt.scatter(row['Longitude'], row['Latitude'], label=f"Cluster {row['AdjustedCluster']}", s=50)
    plt.plot([depot_coords[1], row['Longitude']], [depot_coords[0], row['Latitude']], 'gray')

# Ajouter des étiquettes et une légende
plt.title("Clients les plus proches du dépôt pour chaque cluster")
plt.xlabel("Longitude")
plt.ylabel("Latitude")
plt.legend()
plt.grid(True)

# Sauvegarder la carte dans le dossier output
output_plot_path = "scripts/output/nearest_clients_visualization.png"
plt.savefig(output_plot_path)
print(f"Carte enregistrée sous : {output_plot_path}")

# Afficher la carte
plt.show()
