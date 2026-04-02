from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

input_file = BASE_DIR / "data" / "export(1).geojson"
output_file = BASE_DIR / "results" / "ixelles_residential.geojson"

# Load the GeoJSON file into a GeoDataFrame
gdf = gpd.read_file(input_file)

# List of building types considered as residential
residential_values = ["apartments", "house", "residential"]

# Check if the 'building' column exists in the dataset
if "building" not in gdf.columns:
    print("The 'building' column does not exist.")
    print("Available columns:", gdf.columns.tolist())
else:
    # Filter only residential buildings
    gdf_res = gdf[gdf["building"].isin(residential_values)].copy()

    # Save the filtered data to a new GeoJSON file
    gdf_res.to_file(output_file, driver="GeoJSON")

    # Print summary information
    print("Total buildings:", len(gdf))
    print("Residential buildings:", len(gdf_res))
    print("File saved at:", output_file)
