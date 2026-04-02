from pathlib import Path
import geopandas as gpd
import pandas as pd

# Dossier racine du projet
BASE_DIR = Path(__file__).resolve().parent.parent

# Fichiers d'entrée et de sortie
input_file = BASE_DIR / "results" / "ixelles_residential.geojson"
output_file = BASE_DIR / "results" / "ixelles_clean.geojson"

# Créer le dossier results s'il n'existe pas
output_file.parent.mkdir(parents=True, exist_ok=True)

# Charger les données
gdf = gpd.read_file(input_file)

print("Initial number of buildings:", len(gdf))

# 1. Garder uniquement les géométries non nulles et valides
gdf = gdf[gdf.geometry.notnull()]
gdf = gdf[gdf.is_valid]

# 2. Reprojeter en coordonnées belges (mètres)
gdf = gdf.to_crs(epsg=31370)

# 3. Supprimer les très petites géométries
gdf = gdf[gdf.geometry.area > 1]

# 4. Garder seulement les colonnes utiles
cols_to_keep = ["@id", "building", "building:levels", "geometry"]
cols_existing = [col for col in cols_to_keep if col in gdf.columns]
gdf = gdf[cols_existing].copy()

# 5. Nettoyer la colonne building:levels
if "building:levels" in gdf.columns:
    gdf["building:levels"] = pd.to_numeric(gdf["building:levels"], errors="coerce")

# 6. Supprimer les doublons selon @id
if "@id" in gdf.columns:
    gdf = gdf.drop_duplicates(subset="@id")

print("After cleaning:", len(gdf))

# Sauvegarder le fichier nettoyé
gdf.to_file(output_file, driver="GeoJSON")

print("File saved at:", output_file)
