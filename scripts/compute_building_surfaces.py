import geopandas as gpd
import pandas as pd

# Input/output paths (relative to project root)
input_file = "data/ixelles_clean.geojson"
output_file = "results/ixelles_surface.geojson"
output_csv = "results/ixelles_surface.csv"

# 1. Load GeoJSON file
gdf = gpd.read_file(input_file)

print("Number of buildings:", len(gdf))
print("CRS before:", gdf.crs)

# 2. Reproject to Belgian CRS (meters) if needed
if gdf.crs is None or gdf.crs.to_epsg() != 31370:
    gdf = gdf.to_crs(epsg=31370)

print("CRS after:", gdf.crs)

# 3. Compute ground area (m²)
gdf["area_ground_m2"] = gdf.geometry.area

# 4. Clean building levels column
if "building:levels" in gdf.columns:
    gdf["building:levels"] = pd.to_numeric(gdf["building:levels"], errors="coerce")
else:
    gdf["building:levels"] = None

# 5. Estimate missing levels (default = 3)
gdf["levels_est"] = gdf["building:levels"].fillna(3)

# 6. Compute total floor area (m²)
gdf["area_total_m2"] = gdf["area_ground_m2"] * gdf["levels_est"]

# 7. Save results
gdf.to_file(output_file, driver="GeoJSON")
gdf.drop(columns="geometry").to_csv(output_csv, index=False)

# 8. Display preview
cols = [c for c in ["@id", "building", "building:levels", "levels_est",
                   "area_ground_m2", "area_total_m2"] if c in gdf.columns]

print(gdf[cols].head())

print("Average ground area (m²):", gdf["area_ground_m2"].mean())
print("Estimated total area (m²):", gdf["area_total_m2"].mean())
print("GeoJSON saved:", output_file)
print("CSV saved:", output_csv)
