from pathlib import Path
import geopandas as gpd
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent

input_file = BASE_DIR / "data" / "export(1).geojson"
output_file = BASE_DIR / "results" / "ixelles_residential.geojson"

# Créer le dossier results s'il n'existe pas
output_file.parent.mkdir(parents=True, exist_ok=True)

# Charger le fichier GeoJSON
gdf = gpd.read_file(input_file)

# Types de bâtiments considérés comme résidentiels
residential_values = ["apartments", "house", "residential"]

# Vérifier que la colonne 'building' existe
if "building" not in gdf.columns:
    print("La colonne 'building' n'existe pas.")
    print("Colonnes disponibles :", gdf.columns.tolist())
else:
    # Filtrer les bâtiments résidentiels
    gdf_res = gdf[gdf["building"].isin(residential_values)].copy()

    # Sauvegarder le résultat
    gdf_res.to_file(output_file, driver="GeoJSON")

    # Afficher un résumé
    print("Total buildings:", len(gdf))
    print("Residential buildings:", len(gdf_res))
    print("File saved at:", output_file)
