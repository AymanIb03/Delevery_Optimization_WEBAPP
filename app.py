from flask import Flask, render_template, request, send_file, redirect, url_for, jsonify
from flask_socketio import SocketIO, emit
import os
import subprocess
import pandas as pd
import plotly.graph_objs as go
import plotly.io as pio

app = Flask(__name__)
socketio = SocketIO(app)

# Dossiers de stockage des fichiers uploadés et des résultats générés
UPLOAD_FOLDER = 'upload/'
OUTPUT_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'scripts', 'output')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


# Route pour afficher la page d'accueil avec le formulaire d'upload
@app.route('/')
def index():
    return render_template('index.html')


# Route pour gérer l'upload des fichiers et démarrer les processus en arrière-plan
@app.route('/upload', methods=['POST'])
def upload_files():
    try:
        # Récupérer les fichiers téléchargés
        customer_data = request.files['customer_data']
        distance_data = request.files['distance_data']

        # Validation des fichiers
        if not customer_data or not distance_data:
            return "Veuillez télécharger les deux fichiers requis.", 400

        # Sauvegarder les fichiers dans le répertoire 'upload/'
        filepath_customer = os.path.join(app.config['UPLOAD_FOLDER'], 'data.xlsx')
        filepath_distances = os.path.join(app.config['UPLOAD_FOLDER'], 'distance.xlsx')
        customer_data.save(filepath_customer)
        distance_data.save(filepath_distances)

        # Lancer les scripts backend en arrière-plan
        socketio.start_background_task(target=run_processes, filepath_customer=filepath_customer,
                                       filepath_distances=filepath_distances)

        return "Fichiers uploadés avec succès", 200

    except Exception as e:
        return f"Erreur lors de l'upload des fichiers : {str(e)}", 400


# Fonction pour exécuter les scripts et envoyer des mises à jour via SocketIO
def run_processes(filepath_customer, filepath_distances):
    try:
        # Clustering
        emit_status("Clustering des clients en cours...", 25)
        clustering_output_file = os.path.join(OUTPUT_FOLDER, 'adjusted_clusters_final.xlsx')
        subprocess.run(['python', 'scripts/clustering.py', filepath_customer, clustering_output_file], check=True)

        # Vérification des clusters
        emit_status("Vérification des clusters...", 40)
        subprocess.run(['python', 'scripts/verify_clusters.py', clustering_output_file], check=True)

        # Calcul des plus courts chemins
        emit_status("Calcul des plus courts chemins...", 60)
        subprocess.run(['python', 'scripts/shortest_paths.py', clustering_output_file], check=True)

        # Optimisation des tournées
        emit_status("Optimisation des tournées...", 80)
        subprocess.run(['python', 'scripts/optimal_tours.py', filepath_distances], check=True)

        emit_status("Processus terminé avec succès !", 100)

    except subprocess.CalledProcessError as e:
        emit_status(f"Erreur lors du traitement : {str(e)}", 100)


# Fonction pour émettre des statuts de progression via SocketIO
def emit_status(message, progress):
    socketio.emit('progress_update', {'message': message, 'progress': progress})


# Route pour afficher les résultats (liste des fichiers générés)
@app.route('/results')
def results():
    try:
        files = os.listdir(OUTPUT_FOLDER)
        if not files:
            return "Aucun fichier généré pour le moment."
        return render_template('results.html', files=files)
    except Exception as e:
        return f"Erreur lors de l'affichage des résultats : {str(e)}"


# Route pour télécharger les fichiers générés
@app.route('/download/<filename>')
def download_file(filename):
    try:
        file_path = os.path.join(OUTPUT_FOLDER, filename)
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        else:
            return f"Fichier {filename} non trouvé."
    except Exception as e:
        return f"Erreur lors du téléchargement du fichier : {str(e)}"


# Route pour afficher la visualisation des tournées
@app.route('/visualisation')
def visualisation():
    # Charger les clusters à partir du fichier généré
    tours_file = os.path.join(OUTPUT_FOLDER, 'tours_optimaux_nearest_neighbor_complet.xlsx')
    if not os.path.exists(tours_file):
        return "Le fichier de tournées optimales n'existe pas."

    df = pd.read_excel(tours_file)

    # Ajouter 1 à chaque cluster pour l'affichage et trier les clusters par ordre croissant
    clusters = sorted([{'label': f'Cluster {cluster + 1}', 'value': cluster + 1} for cluster in df['Cluster'].unique()],
                      key=lambda x: x['value'])

    return render_template('Visualisation.html', clusters=clusters)


# Route pour mettre à jour le graphique en fonction du cluster sélectionné
@app.route('/update_graph', methods=['POST'])
def update_graph():
    try:
        # Récupérer les données de la requête
        data = request.json
        print("Données reçues:", data)

        cluster_id = int(data.get('cluster_id'))
        print(f"Cluster ID reçu : {cluster_id}")

        # Valider l'ID du cluster
        if not (1 <= cluster_id <= 25):
            print("Cluster ID non valide :", cluster_id)
            return jsonify({"error": "Cluster ID non valide"}), 400

        # Ajuster l'ID du cluster
        adjusted_cluster_id = cluster_id - 1
        print(f"Cluster ID ajusté : {adjusted_cluster_id}")

        # Charger les fichiers Excel
        tours_file = os.path.join(OUTPUT_FOLDER, 'tours_optimaux_nearest_neighbor_complet.xlsx')
        clusters_file = os.path.join(OUTPUT_FOLDER, 'adjusted_clusters_final.xlsx')
        print(f"Chemin du fichier des tours : {tours_file}")
        print(f"Chemin du fichier des clusters : {clusters_file}")

        # Vérifier si les fichiers existent
        if not os.path.exists(tours_file):
            print("Fichier des tours non trouvé")
            return jsonify({"error": "Fichier des tours introuvable"}), 400
        if not os.path.exists(clusters_file):
            print("Fichier des clusters non trouvé")
            return jsonify({"error": "Fichier des clusters introuvable"}), 400

        # Lire les fichiers Excel
        tours_data = pd.read_excel(tours_file)
        clusters_data = pd.read_excel(clusters_file)
        print("Fichiers Excel chargés avec succès")

        # Filtrer le tour pour le cluster sélectionné
        cluster_tour = tours_data[tours_data['Cluster'] == adjusted_cluster_id]
        print(f"Tour du cluster sélectionné : {cluster_tour}")

        if cluster_tour.empty:
            print(f"Aucun tour trouvé pour le cluster {cluster_id}")
            return jsonify({"error": "Aucun tour trouvé"}), 400

        # Extraire les informations du tour et les noms des clients
        tour_str = cluster_tour['Tour'].values[0]
        print(f"Tour string : {tour_str}")
        client_names = tour_str.split(' -> ')
        print(f"Noms des clients : {client_names}")

        # Obtenir les coordonnées des clients
        depot_coords = (32.471173818912625, -6.811046920662349)
        cluster_coords = clusters_data[clusters_data['AdjustedCluster'] == adjusted_cluster_id][['Latitude', 'Longitude']].values
        print(f"Coordonnées des clients : {cluster_coords}")

        # Créer la liste des coordonnées avec le dépôt au début et à la fin
        coords = [depot_coords] + cluster_coords.tolist() + [depot_coords]
        print(f"Coordonnées complètes avec le dépôt : {coords}")

        # Créer le graphique
        fig = go.Figure()

        # Lignes reliant les points
        fig.add_trace(go.Scattermapbox(
            lon=[coord[1] for coord in coords],
            lat=[coord[0] for coord in coords],
            mode='lines',
            line=dict(width=3, color='blue'),
            hoverinfo='skip'
        ))

        # Marqueurs pour les clients avec numéros à l'intérieur
        fig.add_trace(go.Scattermapbox(
            lon=[coord[1] for coord in coords],
            lat=[coord[0] for coord in coords],
            mode='markers+text',
            marker=dict(
                size=20,  # Taille du marqueur
                color='blue',  # Couleur bleue du cercle
                opacity=0.8,  # Opacité
                symbol='circle'  # Cercle
            ),
            text=[f"{i+1}: {name}" for i, name in enumerate(client_names)],  # Numéros et noms des clients
            textfont=dict(color='white', size=12),  # Texte blanc dans le cercle
            textposition="middle center",
            hovertext=[f"Client: {name}<br>Ordre de tour: {i}" for i, name in enumerate(client_names)],  # Texte au survol (nom du client + ordre de passage)
            hoverinfo='text'  # Activer le hover pour afficher les noms et l'ordre de tour
        ))

        # Marqueur spécial pour le dépôt
        fig.add_trace(go.Scattermapbox(
            lon=[depot_coords[1]],
            lat=[depot_coords[0]],
            mode='markers+text',
            marker=dict(size=25, color='red', opacity=1),
            text=['🏠'],
            textfont=dict(color='white', size=16),
            textposition="middle center",
            hovertext=['Dépot'],
            hoverinfo='text'
        ))

        # Configurer la carte avec le style  ("open-street-map")
        fig.update_layout(
            title=f'Tour Optimal pour le Cluster {cluster_id}',
            title_x=0.5,
            mapbox=dict(
                style="open-street-map",
                center=dict(lon=depot_coords[1], lat=depot_coords[0]),
                zoom=9,
            ),
            margin=dict(l=0, r=0, t=30, b=20),
        )

        # Convertir le graphique en JSON
        graph_json = pio.to_json(fig)
        print("Graphique JSON créé avec succès")
        return jsonify(graph_json)

    except Exception as e:
        # Capturer et afficher l'erreur exacte
        print(f"Erreur dans la fonction /update_graph : {str(e)}")
        return jsonify({"error": f"Erreur serveur : {str(e)}"}), 500



# Lancer l'application Flask avec SocketIO
if __name__ == '__main__':
    socketio.run(app, debug=True, port=5002)