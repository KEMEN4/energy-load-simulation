import pandas as pd
import numpy as np

# ======================
# 1. LOAD BUILDING DATA
# ======================
buildings_file = "results/ixelles_final.csv"
df = pd.read_csv(buildings_file)

print("Buildings:", len(df))
print(df.columns)

# Minimal validation
required_cols = ["area_total_m2", "heating_kWh_year"]
for col in required_cols:
    if col not in df.columns:
        raise ValueError(f"Missing column in ixelles_final.csv: {col}")

# ======================
# 2. LOAD WEATHER DATA
# ======================
weather_file = "data/weather_2025.csv"

# NASA POWER files may contain text lines before the actual header
with open(weather_file, "r", encoding="utf-8") as f:
    lines = f.readlines()

header_line = None
for i, line in enumerate(lines):
    if line.startswith("YEAR,"):
        header_line = i
        break

if header_line is None:
    raise ValueError("Could not find the header line starting with 'YEAR,' in the weather file.")

meteo = pd.read_csv(weather_file, skiprows=header_line)

print("Weather columns:", meteo.columns.tolist())
print("Number of weather rows:", len(meteo))

# Check temperature column
if "T2M" not in meteo.columns:
    raise ValueError("Column 'T2M' does not exist in the weather file.")

temp = meteo["T2M"].astype(float)

# Check data size
if len(temp) != 8760:
    print("Warning: number of hours is not 8760. Found:", len(temp))

# ======================
# 3. BUILD TIME SERIES
# ======================
hours = pd.date_range("2025-01-01 00:00:00", "2025-12-31 23:00:00", freq="h")

if len(hours) != len(temp):
    raise ValueError(
        f"Mismatch between generated hours ({len(hours)}) and weather data ({len(temp)})."
    )

# ======================
# 4. PAPER STEP 4: COMPUTE G
# ======================
# Simplified indoor setpoint temperature
Tset = 20.0  # °C

# Temperature difference only when heating is needed
delta_T = np.maximum(0, Tset - temp)

# Annual sum of temperature differences
delta_T_sum = delta_T.sum()

if delta_T_sum <= 0:
    raise ValueError("delta_T_sum <= 0: cannot compute G.")

print("Sum of delta T:", delta_T_sum)

# AHD_i = heating_kWh_year
df["G_kW_per_K"] = df["heating_kWh_year"] / delta_T_sum

print(df[["heating_kWh_year", "G_kW_per_K"]].head())

# ======================
# 5. PAPER STEP 5: PHYSICAL HOURLY PROFILE
# ======================
hourly_total = np.zeros(len(temp))

for _, row in df.iterrows():
    G = row["G_kW_per_K"]
    q_t = G * np.maximum(0, Tset - temp)
    hourly_total += q_t

df_hourly = pd.DataFrame({
    "time": hours,
    "T_out_C": temp.values,
    "heat_demand_kWh": hourly_total
})

print(df_hourly.head())
print("Reconstructed annual demand (MWh):", df_hourly["heat_demand_kWh"].sum() / 1000)

# ======================
# 6. SAVE OUTPUTS
# ======================
output_hourly = "results/ixelles_hourly_real.csv"
output_buildings = "results/ixelles_with_G.csv"

df_hourly.to_csv(output_hourly, index=False)
df.to_csv(output_buildings, index=False)

print("Hourly file saved:", output_hourly)
print("Building file with G saved:", output_buildings)
