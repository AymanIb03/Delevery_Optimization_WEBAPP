import pandas as pd
from matplotlib import pyplot as plt
from sklearn.cluster import OPTICS
from sklearn.preprocessing import StandardScaler
import numpy as np
import sys  # Ajouté pour récupérer le chemin du fichier uploadé depuis Flask

# Récupérer le chemin du fichier uploadé via Flask
file_path = sys.argv[1]

# Charger les données et supprimer les lignes avec des valeurs NaN
df = pd.read_excel(file_path).dropna(subset=['Longitude', 'Latitude']).copy()

# Vérification et suppression des données anormales
def check_and_remove_anomalies(df_local):
    min_lat, max_lat = 21.0, 36.0  # Limites de latitude du Maroc
    min_lon, max_lon = -17.0, -1.0  # Limites de longitude du Maroc

    # Filtrer les clients qui sont dans les limites géographiques valides
    valid_data = df_local[(df_local['Latitude'] >= min_lat) & (df_local['Latitude'] <= max_lat) &
                          (df_local['Longitude'] >= min_lon) & (df_local['Longitude'] <= max_lon)]

    # Afficher les clients supprimés (hors des limites)
    removed_data = df_local[~df_local.index.isin(valid_data.index)]
    if not removed_data.empty:
        print("Les clients suivants ont été supprimés en raison de coordonnées anormales :")
        for _, row in removed_data.iterrows():
            print(f"Client: {row['Partner Name']}, Coordonnées: ({row['Latitude']}, {row['Longitude']})")

    return valid_data

# Supprimer les clients avec des coordonnées anormales
df = check_and_remove_anomalies(df)

# Normaliser les coordonnées GPS
X = df[['Longitude', 'Latitude']].values
X_scaled = StandardScaler().fit_transform(X)
df['Longitude_Normalized'], df['Latitude_Normalized'] = X_scaled[:, 0], X_scaled[:, 1]

# Appliquer l'algorithme OPTICS
optics_model = OPTICS(min_samples=10, xi=0.05, min_cluster_size=0.1)
df['Cluster'] = optics_model.fit_predict(X_scaled)
num_clusters = len(set(df['Cluster'])) - (1 if -1 in df['Cluster'] else 0)
print(f"Nombre de clusters initiaux : {num_clusters}")

# Vérification de la capacité des clusters
truck_capacities = [5000] * 10 + [3000] * 15
cluster_capacities = df.groupby('Cluster')['Weight (Kg)'].sum()

def adjust_clusters(df_local, cluster_capacities_local, truck_capacities_local):
    """Ajuster les clusters pour les affecter aux camions."""
    cluster_to_truck_local = {}
    remaining_truck_capacities_local = truck_capacities_local.copy()

    for cluster_local, capacity in cluster_capacities_local.items():
        if capacity <= 0:
            continue
        for i, truck_capacity in enumerate(remaining_truck_capacities_local):
            if capacity <= truck_capacity:
                cluster_to_truck_local[cluster_local] = truck_capacity
                remaining_truck_capacities_local.pop(i)
                break
        else:
            print(f"Le cluster {cluster_local + 2} doit être ajusté. Capacité : {capacity} kg")
            clients = df_local[df_local['Cluster'] == cluster_local].sort_values(by='Weight (Kg)', ascending=False)
            for index, client in clients.iterrows():
                for j, truck_capacity in enumerate(remaining_truck_capacities_local):
                    if client['Weight (Kg)'] <= truck_capacity:
                        remaining_truck_capacities_local[j] -= client['Weight (Kg)']
                        df_local.at[index, 'AdjustedCluster'] = j
                        break

    return df_local, cluster_to_truck_local

df['AdjustedCluster'] = df['Cluster']
df, cluster_to_truck = adjust_clusters(df, cluster_capacities, truck_capacities)
unique_adjusted_clusters = df['AdjustedCluster'].nunique()

# Ajustement supplémentaire pour s'assurer d'avoir 25 clusters
if unique_adjusted_clusters < 25:
    additional_clusters_needed = 25 - unique_adjusted_clusters
    for _ in range(additional_clusters_needed):
        largest_cluster = df['AdjustedCluster'].value_counts().idxmax()
        largest_cluster_data = df[df['AdjustedCluster'] == largest_cluster]
        half_index = len(largest_cluster_data) // 2
        df.loc[largest_cluster_data.index[half_index:], 'AdjustedCluster'] = unique_adjusted_clusters
        unique_adjusted_clusters += 1

unique_adjusted_clusters = df['AdjustedCluster'].nunique()
print(f"Nombre de clusters ajustés : {unique_adjusted_clusters}")

cluster_summary = df.groupby('AdjustedCluster').agg({
    'Weight (Kg)': 'sum',
    'Longitude': 'mean',
    'Latitude': 'mean'
}).rename(columns={'Weight (Kg)': 'Total Weight (Kg)', 'Longitude': 'Mean Longitude', 'Latitude': 'Mean Latitude'})

print(cluster_summary)

for cluster, data in cluster_summary.iterrows():
    print(f"Cluster {cluster}:")
    print(f"  Poids total (Kg) : {data['Total Weight (Kg)']}")
    print(f"  Longitude moyenne : {data['Mean Longitude']}")
    print(f"  Latitude moyenne : {data['Mean Latitude']}")
    print()

# Sauvegarder le fichier Excel ajusté et le graphique
output_path = "scripts/output/adjusted_clusters_final.xlsx"
df.to_excel(output_path, index=False)
print(f"Fichier Excel enregistré à: {output_path}")

# Génération du graphique des clusters
unique_labels = set(df['AdjustedCluster'])
colors = [plt.get_cmap('Spectral')(each) for each in np.linspace(0, 1, len(unique_labels))]

plt.figure(figsize=(10, 7))
for k, col in zip(unique_labels, colors):
    class_member_mask = (df['AdjustedCluster'] == k)
    xy = X_scaled[class_member_mask]
    plt.plot(xy[:, 0], xy[:, 1], 'o', markerfacecolor=tuple(col), markeredgecolor='k', markersize=6)
plt.title('Clusters ajustés identifiés par OPTICS')
plt.xlabel('Longitude normalisée')
plt.ylabel('Latitude normalisée')
plt.xlim(-2, 2)
plt.ylim(-1, 1)
plt.savefig('scripts/output/plot.png')
print("Plot enregistré sous : scripts/output/plot.png")
