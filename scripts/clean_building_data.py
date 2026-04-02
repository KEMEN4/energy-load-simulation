import geopandas as gpd
import pandas as pd

# Input/output paths (relative)
input_file = "data/ixelles_residential.geojson"
output_file = "results/ixelles_clean.geojson"

# Load data
gdf = gpd.read_file(input_file)

print("Initial number of buildings:", len(gdf))

# 1. Keep valid geometries
gdf = gdf[gdf.geometry.notnull()]
gdf = gdf[gdf.is_valid]

# 2. Reproject to Belgian CRS (meters)
gdf = gdf.to_crs(epsg=31370)

# 3. Remove very small geometries
gdf = gdf[gdf.geometry.area > 1]

# 4. Keep only useful columns
cols_to_keep = ["@id", "building", "building:levels", "geometry"]
cols_existing = [c for c in cols_to_keep if c in gdf.columns]
gdf = gdf[cols_existing].copy()

# 5. Clean building levels column
if "building:levels" in gdf.columns:
    gdf["building:levels"] = pd.to_numeric(gdf["building:levels"], errors="coerce")

# 6. Remove duplicates
if "@id" in gdf.columns:
    gdf = gdf.drop_duplicates(subset="@id")

print("After cleaning:", len(gdf))

# Save cleaned data
gdf.to_file(output_file, driver="GeoJSON")

print("File saved at:", output_file)
