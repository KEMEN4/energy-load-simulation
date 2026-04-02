from pathlib import Path
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# ============================================
# 1. FILE PATHS
# ============================================
BASE_DIR = Path(__file__).resolve().parent.parent

buildings_file = BASE_DIR / "results" / "ixelles_final.csv"
weather_file = BASE_DIR / "data" / "POWER_Point_Hourly_20250101_20251231_050d85N_004d35E_UTC(1).csv"

output_hourly = BASE_DIR / "results" / "profil_chaleur_ixelles_complet.csv"
output_buildings = BASE_DIR / "results" / "ixelles_buildings_enrichi.csv"
output_plot_full = BASE_DIR / "results" / "profil_chauffage_annuel_lisse.png"
output_plot_week = BASE_DIR / "results" / "profil_chauffage_premiere_semaine_lisse.png"
output_plot_temp = BASE_DIR / "results" / "profil_chauffage_et_temperature_lisse.png"

os.makedirs(BASE_DIR / "results", exist_ok=True)

# ============================================
# 2. LOAD BUILDING DATA
# ============================================
df = pd.read_csv(buildings_file)

print("Number of buildings:", len(df))

required_cols = ["area_total_m2", "heating_kWh_year"]
for col in required_cols:
    if col not in df.columns:
        raise ValueError(f"Missing column in building file: {col}")

# ============================================
# 3. LOAD WEATHER DATA
# ============================================
with open(weather_file, "r", encoding="utf-8") as f:
    lines = f.readlines()

header_line = None
for i, line in enumerate(lines):
    if line.startswith("YEAR,"):
        header_line = i
        break

if header_line is None:
    raise ValueError("Could not find the weather header line starting with 'YEAR,'.")

meteo = pd.read_csv(weather_file, skiprows=header_line)

print("Weather columns:", meteo.columns.tolist())
print("Number of weather rows:", len(meteo))

if "T2M" not in meteo.columns:
    raise ValueError("Column 'T2M' is missing in the weather file.")

Tout = meteo["T2M"].astype(float).values

# ============================================
# 4. BUILD TIME SERIES
# ============================================
hours = pd.date_range("2025-01-01 00:00:00", periods=len(Tout), freq="h")

if len(hours) != len(Tout):
    raise ValueError("Mismatch between generated hours and weather data length.")

# ============================================
# 5. THERMAL PARAMETERS
# ============================================
dt = 1.0  # hour

df["Tin"] = 20.0
df["k"] = df["area_total_m2"] * 0.1
df["Qmax"] = df["area_total_m2"] * 0.1
df["Qgain"] = df["area_total_m2"] * 0.005
df["Qsolar"] = 0.0

Tset_ref = 20.0
delta_T_sum = np.sum(np.maximum(Tset_ref - Tout, 0))

if delta_T_sum <= 0:
    raise ValueError("delta_T_sum <= 0, cannot compute G.")

df["G"] = df["heating_kWh_year"] / delta_T_sum

print(df[["heating_kWh_year", "G", "k", "Qmax", "Qgain"]].head())

# ============================================
# 6. HOURLY DYNAMIC SIMULATION
# ============================================
Qloss_total_list = []
Qneeded_total_list = []
Qdemand_total_list = []
Qheating_total_list = []
Tin_mean_list = []
Tset_list = []

for t in range(len(Tout)):
    hour = hours[t].hour
    weekday = hours[t].weekday()

    if weekday < 5:
        if 6 <= hour <= 22:
            Tset_t = 21.0
        else:
            Tset_t = 16.0
    else:
        if 8 <= hour <= 23:
            Tset_t = 21.0
        else:
            Tset_t = 16.0

    Qloss = df["G"] * (df["Tin"] - Tout[t])
    delta_Q = df["k"] * (Tset_t - df["Tin"])
    Qdemand = Qloss + (delta_Q / dt)

    Qheating = Qdemand.clip(lower=0)
    Qheating = np.minimum(Qheating, df["Qmax"])

    df["Tin"] = df["Tin"] + dt * (
        Qheating + df["Qgain"] + df["Qsolar"] - Qloss
    ) / df["k"]

    Qloss_total_list.append(Qloss.sum())
    Qneeded_total_list.append(delta_Q.sum())
    Qdemand_total_list.append(Qdemand.sum())
    Qheating_total_list.append(Qheating.sum())
    Tin_mean_list.append(df["Tin"].mean())
    Tset_list.append(Tset_t)

# ============================================
# 7. BUILD OUTPUT DATAFRAME
# ============================================
df_hourly = pd.DataFrame({
    "time": hours,
    "T_out_C": Tout,
    "T_set_C": Tset_list,
    "Tin_mean_C": Tin_mean_list,
    "Qloss_total_kW": Qloss_total_list,
    "DeltaQ_total_kWh": Qneeded_total_list,
    "Qdemand_total_kW": Qdemand_total_list,
    "Qheating_total_kW": Qheating_total_list
})

df_hourly["Qheating_smooth_kW"] = (
    df_hourly["Qheating_total_kW"]
    .rolling(window=24 * 7, center=True, min_periods=1)
    .mean()
)

# ============================================
# 8. SAVE CSV FILES
# ============================================
df_hourly.to_csv(output_hourly, index=False)
df.to_csv(output_buildings, index=False)

annual_simulated_MWh = df_hourly["Qheating_total_kW"].sum() / 1000

print("Hourly CSV saved:", output_hourly)
print("Buildings CSV saved:", output_buildings)
print("Simulated annual heating demand (MWh):", annual_simulated_MWh)

# ============================================
# 9. SAVE SMOOTHED PLOTS
# ============================================
plt.figure(figsize=(12, 5))
plt.plot(df_hourly["time"], df_hourly["Qheating_smooth_kW"])
plt.xlabel("Time")
plt.ylabel("Heating demand (kW)")
plt.title("Smoothed hourly heating profile - Ixelles (2025)")
plt.tight_layout()
plt.savefig(output_plot_full, dpi=300)
plt.close()

subset = df_hourly.iloc[:24 * 7].copy()
subset["Qheating_smooth_kW"] = (
    subset["Qheating_total_kW"]
    .rolling(window=24, center=True, min_periods=1)
    .mean()
)

plt.figure(figsize=(12, 5))
plt.plot(subset["time"], subset["Qheating_smooth_kW"])
plt.xlabel("Time")
plt.ylabel("Heating demand (kW)")
plt.title("Smoothed heating profile - First week of 2025")
plt.tight_layout()
plt.savefig(output_plot_week, dpi=300)
plt.close()

fig, ax1 = plt.subplots(figsize=(12, 5))
ax1.plot(subset["time"], subset["Qheating_smooth_kW"])
ax1.set_xlabel("Time")
ax1.set_ylabel("Heating demand (kW)")

ax2 = ax1.twinx()
ax2.plot(subset["time"], subset["T_out_C"])
ax2.set_ylabel("Outdoor temperature (°C)")

plt.title("Smoothed heating demand and outdoor temperature - First week")
plt.tight_layout()
plt.savefig(output_plot_temp, dpi=300)
plt.close()

print("Smoothed annual profile saved:", output_plot_full)
print("Smoothed first-week profile saved:", output_plot_week)
print("Smoothed combined plot saved:", output_plot_temp)
