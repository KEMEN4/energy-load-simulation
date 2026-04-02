import pandas as pd
import numpy as np

# Input/output paths (relative to project root)
input_file = "results/ixelles_surface.csv"
output_csv = "results/ixelles_final.csv"

# 1. Load CSV file
df = pd.read_csv(input_file)

print("Number of buildings:", len(df))

# 2. Assign building type (Multi-Family Housing)
df["building_type"] = "MFH"

# 3. Assign realistic Qspec values for Brussels (kWh/m²/year)
def assign_qspec_brussels():
    r = np.random.rand()

    if r < 0.6:
        return 350   # old buildings (typical Ixelles)
    elif r < 0.85:
        return 275   # partially renovated
    else:
        return 150   # renovated buildings

df["Qspec_kWh_m2"] = [assign_qspec_brussels() for _ in range(len(df))]

# 4. Compute annual heating demand (kWh/year)
df["heating_kWh_year"] = df["area_total_m2"] * df["Qspec_kWh_m2"]

# 5. Preview results
print(df[["area_total_m2", "Qspec_kWh_m2", "heating_kWh_year"]].head())

# 6. Total demand (MWh/year)
total_MWh = df["heating_kWh_year"].sum() / 1000
print("Total heating demand (MWh/year):", total_MWh)

# 7. Save results
df.to_csv(output_csv, index=False)

print("CSV saved at:", output_csv)
