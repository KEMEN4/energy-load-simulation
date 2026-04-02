from pathlib import Path
import pandas as pd
import numpy as np

# Base du projet
BASE_DIR = Path(__file__).resolve().parent.parent

# Fichiers
input_file = BASE_DIR / "results" / "ixelles_surface.csv"
output_csv = BASE_DIR / "results" / "ixelles_final.csv"

# Charger les données
df = pd.read_csv(input_file)

print("Number of buildings:", len(df))

# Type de bâtiment
df["building_type"] = "MFH"

# Qspec réaliste pour Bruxelles
def assign_qspec_brussels():
    r = np.random.rand()
    if r < 0.6:
        return 350
    elif r < 0.85:
        return 275
    else:
        return 150

df["Qspec_kWh_m2"] = [assign_qspec_brussels() for _ in range(len(df))]

# Calcul demande de chauffage
df["heating_kWh_year"] = df["area_total_m2"] * df["Qspec_kWh_m2"]

# Aperçu
print(df[["area_total_m2", "Qspec_kWh_m2", "heating_kWh_year"]].head())

# Total
total_MWh = df["heating_kWh_year"].sum() / 1000
print("Total heating demand (MWh/year):", total_MWh)

# Sauvegarde
output_csv.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(output_csv, index=False)

print("CSV saved at:", output_csv)
