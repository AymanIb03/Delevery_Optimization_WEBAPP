import pandas as pd
import sys  # Pour récupérer les chemins des fichiers depuis Flask

# Chemin du fichier ajusté généré par le script clustering
adjusted_file_path = "scripts/output/adjusted_clusters_final.xlsx"

# Charger le fichier d'origine uploadé par l'utilisateur via Flask
original_file_path = sys.argv[1]  # Chemin du fichier original uploadé (data.xlsx)

# Charger les fichiers Excel
df_original = pd.read_excel(original_file_path)
df_adjusted = pd.read_excel(adjusted_file_path)

# Vérifier les différences entre les deux DataFrames pour identifier les clients manquants
merged_df = df_original.merge(df_adjusted, on='Partner ID', how='left', indicator=True)
missing_clients = merged_df[merged_df['_merge'] == 'left_only']

if not missing_clients.empty:
    print("Clients manquants :")
    print(missing_clients[['Partner ID', 'Latitude_x', 'Longitude_x', 'Weight (Kg)_x']])
else:
    print("Aucun client manquant trouvé.")

# Total des clients assignés dans le fichier ajusté
total_clients = df_adjusted['Partner ID'].nunique()
print(f"Total des clients assignés : {total_clients}")
