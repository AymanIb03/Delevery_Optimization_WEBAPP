import pandas as pd
import numpy as np
from math import radians, sin, cos, sqrt, atan2
import sys  # Pour récupérer les chemins des fichiers depuis Flask

# Charger les fichiers ajustés des clusters et les clients les plus proches du dépôt
clusters_file = 'scripts/output/adjusted_clusters_final.xlsx'
nearest_clients_file = 'scripts/output/nearest_clients_from_depot_bellman_ford.xlsx'
distance_file = sys.argv[1]  # Fichier 'distance.xlsx' uploadé par l'utilisateur

# Charger le fichier distance.xlsx et les données des clusters
clusters_data = pd.read_excel(clusters_file)
nearest_clients_data = pd.read_excel(nearest_clients_file)
distances_df = pd.read_excel(distance_file, index_col=0)  # Charger la matrice de distances entre les clients

# Vérification des IDs dans distances_df
distances_df.index = distances_df.index.astype(str)
distances_df.columns = distances_df.columns.astype(str)

# Coordonnées du dépôt
depot_coords = (32.471173818912625, -6.811046920662349)

# Fonction pour calculer la distance géodésique (Haversine) entre deux points GPS
def calculate_haversine_distance(coord1: tuple, coord2: tuple) -> float:
    R = 6371.0  # Rayon moyen de la Terre en km

    lat1, lon1 = radians(coord1[0]), radians(coord1[1])
    lat2, lon2 = radians(coord2[0]), radians(coord2[1])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return R * c

# Fonction pour récupérer la distance entre deux clients depuis la matrice
def get_distance_between_clients(client1_id, client2_id):
    client1_id = str(client1_id)  # Convertir les IDs en chaînes
    client2_id = str(client2_id)

    if client1_id in distances_df.index and client2_id in distances_df.columns:
        return distances_df.loc[client1_id, client2_id]
    else:
        print(f"Distance introuvable pour les clients : {client1_id} ou {client2_id}. Ignorée.")
        return None  # Renvoie None pour signaler une distance introuvable

# Calculer la matrice de distances pour un cluster (incluant le dépôt)
def calculate_distance_matrix_with_depot(cluster, depot_coords):
    points = cluster[['Latitude', 'Longitude']].values
    points_with_depot = np.vstack([depot_coords, points])  # Ajouter le dépôt aux coordonnées

    n = len(points_with_depot)
    distance_matrix = np.full((n, n), np.inf)  # Initialise une matrice avec des valeurs infinies

    for i in range(n):
        for j in range(n):
            if i == 0 and j > 0:  # Calculer la distance entre le dépôt et les clients avec Haversine
                distance_matrix[i, j] = calculate_haversine_distance(depot_coords, points[j - 1])
            elif i != j and i > 0 and j > 0:
                distance = get_distance_between_clients(cluster.iloc[i - 1]['Partner ID'], cluster.iloc[j - 1]['Partner ID'])
                if distance is not None:
                    distance_matrix[i, j] = distance

    return distance_matrix

# Algorithme Nearest Neighbor TSP en incluant le dépôt et en forçant le premier client le plus proche
def nearest_neighbor_tsp_with_depot(distance_matrix, start_index):
    n = len(distance_matrix)
    unvisited = list(range(1, n))  # Commencer après le dépôt (index 0)
    unvisited.remove(start_index)  # Retirer le client de départ de la liste des non-visités
    tour = [0, start_index]  # Commencer par le dépôt puis le client le plus proche du dépôt

    while unvisited:
        last = tour[-1]
        next_city = min(unvisited, key=lambda city: distance_matrix[last, city] if distance_matrix[last, city] != np.inf else float('inf'))
        if distance_matrix[last, next_city] == np.inf:  # Vérifie si la distance est infinie (donc introuvable)
            print(f"Pas de chemin trouvé entre {last} et {next_city}, tournée interrompue.")
            break
        tour.append(next_city)
        unvisited.remove(next_city)

    # Retourner au dépôt à la fin
    if tour[-1] != 0:
        tour.append(0)

    # Calcul du coût total de la tournée
    cost = sum(distance_matrix[tour[i], tour[i + 1]] for i in range(len(tour) - 1) if distance_matrix[tour[i], tour[i + 1]] != np.inf)

    return cost, tour

# Fonction pour calculer et sauvegarder les tournées dans un fichier Excel
def calculate_and_save_tours():
    all_tours = []

    # Parcourir tous les clusters et calculer le tour optimal
    for cluster_id in clusters_data['AdjustedCluster'].unique():
        cluster = clusters_data[clusters_data['AdjustedCluster'] == cluster_id]

        # Calculer la matrice de distances pour le cluster
        distance_matrix = calculate_distance_matrix_with_depot(cluster, depot_coords)

        # Trouver le client de départ pour ce cluster à partir du fichier nearest_clients_from_depot_bellman_ford.xlsx
        nearest_client_id = nearest_clients_data[nearest_clients_data['Cluster'] == cluster_id]['Nearest Client ID'].values[0]

        # Obtenir la position relative du client dans le cluster
        start_index = cluster[cluster['Partner ID'] == nearest_client_id].index[0]
        start_index = list(cluster.index).index(start_index)

        # Calculer la tournée optimale avec l'algorithme Nearest Neighbor
        optimal_cost, optimal_tour = nearest_neighbor_tsp_with_depot(distance_matrix, start_index)

        # Extraire les noms des clients et du dépôt
        client_names = ["Dépôt"] + cluster['Partner Name'].tolist()
        client_names = [str(name) for name in client_names]

        # Créer la tournée sous forme de chaîne de caractères
        tour_str = ' -> '.join([client_names[i] for i in optimal_tour])

        # Enregistrer les résultats pour chaque cluster
        all_tours.append([cluster_id, tour_str, optimal_cost])

    # Convertir la liste des tournées en DataFrame
    df = pd.DataFrame(all_tours, columns=['Cluster', 'Tour', 'Distance Totale (km)'])

    # Sauvegarder dans un fichier Excel unique
    output_file = "scripts/output/tours_optimaux_nearest_neighbor_complet.xlsx"
    df.to_excel(output_file, index=False)

    print(f"Le fichier Excel '{output_file}' a été généré avec succès.")

# Exécution du calcul et sauvegarde des tournées
if __name__ == '__main__':
    calculate_and_save_tours()
