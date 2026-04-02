import os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# =========================================================
# 1. FILE PATHS
# =========================================================
buildings_file = "results/ixelles_final.csv"
weather_file = "data/weather_2025.csv"
output_file = "results/profil_chaleur_refroidissement_ixelles.csv"

out_dir = "results"
os.makedirs(out_dir, exist_ok=True)

plot_annual_all = os.path.join(out_dir, "profil_annuel_complet_ixelles.png")
plot_daily_all = os.path.join(out_dir, "profil_journalier_complet_ixelles.png")
plot_monthly_all = os.path.join(out_dir, "profil_mensuel_complet_ixelles.png")

plot_annual_elec_total = os.path.join(out_dir, "profil_annuel_electricite_totale_ixelles.png")
plot_daily_elec_total = os.path.join(out_dir, "profil_journalier_electricite_totale_ixelles.png")
plot_monthly_elec_total = os.path.join(out_dir, "profil_mensuel_electricite_totale_ixelles.png")

plot_cop_eer = os.path.join(out_dir, "profil_COP_EER_ixelles.png")
plot_cop = os.path.join(out_dir, "profil_COP_ixelles.png")
plot_eer = os.path.join(out_dir, "profil_EER_ixelles.png")

# =========================================================
# 2. HEAT PUMP PARAMETERS
# =========================================================
dT_hex_heating = 5.0
dT_hex_cooling = 5.0
deltaT_min = 3.0

eta_heating = 0.45
eta_cooling = 0.35

cool_cutoff_temp = 22.0

COP_min = 1.5
COP_max = 7.0
EER_min = 1.5
EER_max = 8.0

# =========================================================
# 3. NON-HVAC PARAMETERS
# =========================================================
nonhvac_fraction = 0.80

# =========================================================
# 4. HEAT PUMP FUNCTIONS
# =========================================================
def to_kelvin(T_c):
    return np.asarray(T_c, dtype=float) + 273.15


def cop_carnot_heating(Tout_C, Tindoor_C):
    Tout_C = np.asarray(Tout_C, dtype=float)
    Tindoor_C = np.asarray(Tindoor_C, dtype=float)

    T_cond_K = to_kelvin(Tindoor_C + dT_hex_heating)
    T_evap_K = to_kelvin(Tout_C - dT_hex_heating)

    delta_T = np.maximum(T_cond_K - T_evap_K, deltaT_min)
    cop_real = eta_heating * (T_cond_K / delta_T)

    return np.clip(cop_real, COP_min, COP_max)


def eer_carnot_cooling(Tout_C, Tindoor_C):
    Tout_C = np.asarray(Tout_C, dtype=float)
    Tindoor_C = np.asarray(Tindoor_C, dtype=float)

    T_cond_K = to_kelvin(Tout_C + dT_hex_cooling)
    T_evap_K = to_kelvin(Tindoor_C - dT_hex_cooling)

    delta_T = np.maximum(T_cond_K - T_evap_K, deltaT_min)
    eer_real = eta_cooling * (T_evap_K / delta_T)

    return np.clip(eer_real, EER_min, EER_max)

# =========================================================
# 5. LOAD BUILDING DATA
# =========================================================
df = pd.read_csv(buildings_file)

print("Buildings:", len(df))
print("Building columns:", df.columns.tolist())

required_cols = ["area_total_m2", "Qspec_kWh_m2"]
for col in required_cols:
    if col not in df.columns:
        raise ValueError(f"Missing column: {col}")

# =========================================================
# 6. HEATING BASE
# =========================================================
df["heating_kWh_year"] = df["area_total_m2"] * df["Qspec_kWh_m2"]

# =========================================================
# 7. LOAD WEATHER DATA
# =========================================================
with open(weather_file, "r", encoding="utf-8") as f:
    lines = f.readlines()

header_line = None
for i, line in enumerate(lines):
    if line.startswith("YEAR,"):
        header_line = i
        break

if header_line is None:
    raise ValueError("Could not find the line starting with YEAR,... in the weather file.")

meteo = pd.read_csv(weather_file, skiprows=header_line)

print("Weather columns:", meteo.columns.tolist())
print("Number of weather rows:", len(meteo))

if "T2M" not in meteo.columns:
    raise ValueError("Column T2M is missing.")
if "ALLSKY_SFC_SW_DWN" not in meteo.columns:
    raise ValueError("Column ALLSKY_SFC_SW_DWN is missing.")

Tout = meteo["T2M"].astype(float).values
Irr = meteo["ALLSKY_SFC_SW_DWN"].astype(float).values

hours = pd.date_range("2025-01-01 00:00:00", periods=len(Tout), freq="h")

# =========================================================
# 8. THERMAL PARAMETERS
# =========================================================
dt = 1.0

df["Tin"] = 20.0
df["k"] = df["area_total_m2"] * 0.15
df["Qheat_max"] = df["area_total_m2"] * 0.10
df["Qcool_max"] = df["area_total_m2"] * 0.08

np.random.seed(42)
cooling_share = 0.80
df["has_cooling"] = (np.random.rand(len(df)) < cooling_share).astype(int)

window_ratio = 0.10
solar_factor = 0.6

# =========================================================
# 9. COMPUTE G
# =========================================================
Tset_ref = 20.0
delta_T_sum = np.sum(np.maximum(Tset_ref - Tout, 0))

if delta_T_sum <= 0:
    raise ValueError("delta_T_sum <= 0")

df["G"] = df["heating_kWh_year"] / delta_T_sum

print(df[["area_total_m2", "Qspec_kWh_m2", "heating_kWh_year", "G", "k"]].head())

# =========================================================
# 10. STORAGE LISTS
# =========================================================
Qheating_total = []
Qcooling_total = []
Qsolar_total = []
Qgain_total = []

Pheat_elec_total = []
Pcool_elec_total = []
Phvac_elec_total = []
Pnonhvac_total = []
Peltotal_total = []

COP_mean = []
EER_mean = []
COP_theoretical_mean = []
EER_theoretical_mean = []

Tin_mean = []
A_mean = []
Tset_heat_mean = []
Tset_cool_mean = []

Qheating_prev = np.zeros(len(df))
Qcooling_prev = np.zeros(len(df))

# =========================================================
# 11. HOURLY SIMULATION
# =========================================================
np.random.seed(123)

for t in range(len(Tout)):
    current_time = hours[t]
    hour = current_time.hour
    weekday = current_time.weekday()

    # 11.1 Occupancy
    if weekday < 5:
        if 6 <= hour <= 8 or 18 <= hour <= 22:
            p_active = 0.80
        elif 9 <= hour <= 16:
            p_active = 0.20
        else:
            p_active = 0.10
    else:
        if 8 <= hour <= 22:
            p_active = 0.75
        else:
            p_active = 0.15

    A_t = (np.random.rand(len(df)) < p_active).astype(int)

    # 11.2 Heating setpoint
    Tset_heat = np.where(
        A_t == 1,
        np.random.normal(21.0, 2.0, len(df)),
        np.random.normal(16.0, 2.0, len(df))
    )
    Tset_heat = np.clip(Tset_heat, 12.0, 24.0)

    # 11.3 Cooling setpoint
    Tset_cool = np.where(
        A_t == 1,
        np.random.normal(25.0, 1.0, len(df)),
        np.random.normal(27.0, 1.0, len(df))
    )
    Tset_cool = np.clip(Tset_cool, 23.0, 30.0)

    # 11.4 Internal gains
    qgain_density = np.where(
        A_t == 1,
        np.random.normal(0.006, 0.001, len(df)),
        np.random.normal(0.0015, 0.0005, len(df))
    )
    qgain_density = np.clip(qgain_density, 0.0005, 0.006)
    Qgain = qgain_density * df["area_total_m2"].values

    # 11.5 Non-HVAC electricity
    Pnonhvac = nonhvac_fraction * Qgain

    # 11.6 Solar gains
    Qsolar = Irr[t] * (df["area_total_m2"].values * window_ratio) * solar_factor / 1000.0

    # 11.7 Thermal losses
    Qloss = df["G"].values * (df["Tin"].values - Tout[t])

    # 11.8 Heating demand
    DeltaQ_heat = df["k"].values * (Tset_heat - df["Tin"].values)
    Qdemand_heat = Qloss + (DeltaQ_heat / dt)
    Qheating = np.clip(Qdemand_heat, 0, None)

    factor = np.clip((Tset_heat - Tout[t]) / 4.0, 0, 1)
    Qheating = Qheating * factor
    Qheating = np.minimum(Qheating, df["Qheat_max"].values)

    # Heating smoothing
    Qheating = 0.8 * Qheating + 0.2 * Qheating_prev
    Qheating_prev = Qheating.copy()

    # 11.9 Cooling demand
    DeltaQ_cool = df["k"].values * (df["Tin"].values - Tset_cool)
    Qdemand_cool = (-Qloss) + (DeltaQ_cool / dt) + Qgain + Qsolar
    Qcooling = np.clip(Qdemand_cool, 0, None)
    Qcooling = np.minimum(Qcooling, df["Qcool_max"].values)
    Qcooling = Qcooling * df["has_cooling"].values

    # Cooling smoothing
    Qcooling = 0.6 * Qcooling + 0.4 * Qcooling_prev
    Qcooling_prev = Qcooling.copy()

    # Avoid simultaneous heating and cooling
    cooling_mask = Qcooling > 0
    Qheating[cooling_mask] = 0.0

    # 11.10 COP / EER
    COP_t = cop_carnot_heating(Tout[t], Tset_heat)
    EER_t = eer_carnot_cooling(Tout[t], Tset_cool)

    heating_on = (Qheating > 0.0)
    cooling_on = (Qcooling > 0.0) & (Tout[t] >= cool_cutoff_temp) & (~heating_on)

    Qheating_served = np.where(heating_on, Qheating, 0.0)
    Qcooling_served = np.where(cooling_on, Qcooling, 0.0)

    # 11.11 Heat pump electricity
    P_heat_elec = np.where(heating_on, Qheating_served / COP_t, 0.0)
    P_cool_elec = np.where(cooling_on, Qcooling_served / EER_t, 0.0)
    P_hvac_elec = P_heat_elec + P_cool_elec

    # 11.12 Total electricity
    Peltotal = P_hvac_elec + Pnonhvac

    # 11.13 Update indoor temperature
    Tin_new = df["Tin"].values + dt * (
        Qheating_served + Qgain + Qsolar - Qloss - Qcooling_served
    ) / df["k"].values

    df["Tin"] = np.clip(Tin_new, 10.0, 35.0)

    # 11.14 Store results
    Qheating_total.append(Qheating_served.sum())
    Qcooling_total.append(Qcooling_served.sum())
    Qsolar_total.append(Qsolar.sum())
    Qgain_total.append(Qgain.sum())

    Pheat_elec_total.append(P_heat_elec.sum())
    Pcool_elec_total.append(P_cool_elec.sum())
    Phvac_elec_total.append(P_hvac_elec.sum())
    Pnonhvac_total.append(Pnonhvac.sum())
    Peltotal_total.append(Peltotal.sum())

    COP_mean.append(np.mean(COP_t[heating_on]) if np.any(heating_on) else np.nan)
    EER_mean.append(np.mean(EER_t[cooling_on]) if np.any(cooling_on) else np.nan)

    COP_theoretical_mean.append(np.mean(COP_t))
    EER_theoretical_mean.append(np.mean(EER_t))

    Tin_mean.append(df["Tin"].mean())
    A_mean.append(A_t.mean())
    Tset_heat_mean.append(Tset_heat.mean())
    Tset_cool_mean.append(Tset_cool.mean())

# =========================================================
# 12. SAVE CSV
# =========================================================
df_hourly = pd.DataFrame({
    "time": hours,
    "T_out_C": Tout,
    "A_mean": A_mean,
    "Tin_mean_C": Tin_mean,
    "Tset_heat_mean_C": Tset_heat_mean,
    "Tset_cool_mean_C": Tset_cool_mean,
    "Qgain_total_kW": Qgain_total,
    "Qsolar_total_kW": Qsolar_total,
    "Qheating_total_kW": Qheating_total,
    "Qcooling_total_kW": Qcooling_total,
    "Pheat_elec_total_kW": Pheat_elec_total,
    "Pcool_elec_total_kW": Pcool_elec_total,
    "Phvac_elec_total_kW": Phvac_elec_total,
    "Pnonhvac_total_kW": Pnonhvac_total,
    "Peltotal_total_kW": Peltotal_total,
    "COP_mean": COP_mean,
    "EER_mean": EER_mean,
    "COP_theoretical_mean": COP_theoretical_mean,
    "EER_theoretical_mean": EER_theoretical_mean,
})

df_hourly.to_csv(output_file, index=False)

print("CSV generated:", output_file)
print("Annual heating demand (MWh):", df_hourly["Qheating_total_kW"].sum() / 1000.0)
print("Annual cooling demand (MWh):", df_hourly["Qcooling_total_kW"].sum() / 1000.0)
print("Annual heat pump heating electricity (MWhe):", df_hourly["Pheat_elec_total_kW"].sum() / 1000.0)
print("Annual heat pump cooling electricity (MWhe):", df_hourly["Pcool_elec_total_kW"].sum() / 1000.0)
print("Annual total HVAC electricity (MWhe):", df_hourly["Phvac_elec_total_kW"].sum() / 1000.0)
print("Annual non-HVAC electricity (MWhe):", df_hourly["Pnonhvac_total_kW"].sum() / 1000.0)
print("Annual total electricity (MWhe):", df_hourly["Peltotal_total_kW"].sum() / 1000.0)
print("Heating peak (MW):", df_hourly["Qheating_total_kW"].max() / 1000.0)
print("Cooling peak (MW):", df_hourly["Qcooling_total_kW"].max() / 1000.0)
print("HVAC electric peak (MWe):", df_hourly["Phvac_elec_total_kW"].max() / 1000.0)
print("Total electric peak (MWe):", df_hourly["Peltotal_total_kW"].max() / 1000.0)

# =========================================================
# 13. RELOAD FOR PLOTS
# =========================================================
df_plot = pd.read_csv(output_file)
df_plot["time"] = pd.to_datetime(df_plot["time"])

df_daily = df_plot.resample("D", on="time").mean(numeric_only=True)
df_monthly = df_plot.resample("ME", on="time").mean(numeric_only=True)

# =========================================================
# 14. ANNUAL COMPLETE PROFILE
# =========================================================
plt.figure(figsize=(18, 7))
plt.plot(df_plot["time"], df_plot["Qheating_total_kW"], label="Thermal heating (kW)")
plt.plot(df_plot["time"], df_plot["Qcooling_total_kW"], label="Thermal cooling (kW)")
plt.plot(df_plot["time"], df_plot["Phvac_elec_total_kW"], label="HVAC electricity (kW)")
plt.plot(df_plot["time"], df_plot["Pnonhvac_total_kW"], label="Non-HVAC electricity (kW)")
plt.plot(df_plot["time"], df_plot["Peltotal_total_kW"], label="Total electricity (kW)")
plt.title("Annual complete profile - Ixelles (2025)")
plt.xlabel("Time")
plt.ylabel("Power (kW)")
plt.legend()
plt.tight_layout()
plt.savefig(plot_annual_all, dpi=200, bbox_inches="tight")
plt.close()

# =========================================================
# 15. DAILY COMPLETE PROFILE
# =========================================================
plt.figure(figsize=(18, 7))
plt.plot(df_daily.index, df_daily["Qheating_total_kW"], label="Average thermal heating (kW)")
plt.plot(df_daily.index, df_daily["Qcooling_total_kW"], label="Average thermal cooling (kW)")
plt.plot(df_daily.index, df_daily["Phvac_elec_total_kW"], label="Average HVAC electricity (kW)")
plt.plot(df_daily.index, df_daily["Pnonhvac_total_kW"], label="Average non-HVAC electricity (kW)")
plt.plot(df_daily.index, df_daily["Peltotal_total_kW"], label="Average total electricity (kW)")
plt.title("Daily complete profile - Ixelles (2025)")
plt.xlabel("Time")
plt.ylabel("Average power (kW)")
plt.legend()
plt.tight_layout()
plt.savefig(plot_daily_all, dpi=200, bbox_inches="tight")
plt.close()

# =========================================================
# 16. MONTHLY COMPLETE PROFILE
# =========================================================
plt.figure(figsize=(18, 7))
plt.plot(df_monthly.index, df_monthly["Qheating_total_kW"], label="Average thermal heating (kW)")
plt.plot(df_monthly.index, df_monthly["Qcooling_total_kW"], label="Average thermal cooling (kW)")
plt.plot(df_monthly.index, df_monthly["Phvac_elec_total_kW"], label="Average HVAC electricity (kW)")
plt.plot(df_monthly.index, df_monthly["Pnonhvac_total_kW"], label="Average non-HVAC electricity (kW)")
plt.plot(df_monthly.index, df_monthly["Peltotal_total_kW"], label="Average total electricity (kW)")
plt.title("Monthly complete profile - Ixelles (2025)")
plt.xlabel("Time")
plt.ylabel("Average power (kW)")
plt.legend()
plt.tight_layout()
plt.savefig(plot_monthly_all, dpi=200, bbox_inches="tight")
plt.close()

# =========================================================
# 17. TOTAL ELECTRICITY ONLY
# =========================================================
plt.figure(figsize=(16, 5))
plt.plot(df_plot["time"], df_plot["Peltotal_total_kW"])
plt.title("Annual total electricity profile - Ixelles (2025)")
plt.xlabel("Time")
plt.ylabel("Total electric power (kW)")
plt.tight_layout()
plt.savefig(plot_annual_elec_total, dpi=200, bbox_inches="tight")
plt.close()

plt.figure(figsize=(16, 5))
plt.plot(df_daily.index, df_daily["Peltotal_total_kW"])
plt.title("Daily total electricity profile - Ixelles (2025)")
plt.xlabel("Time")
plt.ylabel("Average total electric power (kW)")
plt.tight_layout()
plt.savefig(plot_daily_elec_total, dpi=200, bbox_inches="tight")
plt.close()

plt.figure(figsize=(16, 5))
plt.plot(df_monthly.index, df_monthly["Peltotal_total_kW"])
plt.title("Monthly total electricity profile - Ixelles (2025)")
plt.xlabel("Time")
plt.ylabel("Average total electric power (kW)")
plt.tight_layout()
plt.savefig(plot_monthly_elec_total, dpi=200, bbox_inches="tight")
plt.close()

# =========================================================
# 18. COP AND EER
# =========================================================
plt.figure(figsize=(16, 5))
plt.plot(df_plot["time"], df_plot["COP_mean"], label="COP used")
plt.plot(df_plot["time"], df_plot["EER_mean"], label="EER used")
plt.title("Hourly COP / EER profile - Ixelles (2025)")
plt.xlabel("Time")
plt.ylabel("Value")
plt.legend()
plt.tight_layout()
plt.savefig(plot_cop_eer, dpi=200, bbox_inches="tight")
plt.close()

# =========================================================
# 19. COP ONLY
# =========================================================
df_cop = df_plot.dropna(subset=["COP_mean"])
if len(df_cop) > 0:
    plt.figure(figsize=(16, 5))
    plt.plot(df_cop["time"], df_cop["COP_mean"])
    plt.title("Hourly heating COP profile - Ixelles (2025)")
    plt.xlabel("Time")
    plt.ylabel("COP")
    plt.tight_layout()
    plt.savefig(plot_cop, dpi=200, bbox_inches="tight")
    plt.close()

# =========================================================
# 20. EER ONLY
# =========================================================
df_eer = df_plot.dropna(subset=["EER_mean"])
if len(df_eer) > 0:
    plt.figure(figsize=(16, 5))
    plt.plot(df_eer["time"], df_eer["EER_mean"])
    plt.title("Hourly cooling EER profile - Ixelles (2025)")
    plt.xlabel("Time")
    plt.ylabel("EER")
    plt.tight_layout()
    plt.savefig(plot_eer, dpi=200, bbox_inches="tight")
    plt.close()

# =========================================================
# 21. SUMMARY
# =========================================================
print("Graphs created:")
print(" -", plot_annual_all)
print(" -", plot_daily_all)
print(" -", plot_monthly_all)
print(" -", plot_annual_elec_total)
print(" -", plot_daily_elec_total)
print(" -", plot_monthly_elec_total)
print(" -", plot_cop_eer)
if len(df_cop) > 0:
    print(" -", plot_cop)
if len(df_eer) > 0:
    print(" -", plot_eer)

nb_heures_chauffage = (df_hourly["Qheating_total_kW"] > 0).sum()
print("Number of heating hours:", nb_heures_chauffage)

print("Share of heating electricity (%):",
      100 * df_hourly["Pheat_elec_total_kW"].sum() / df_hourly["Peltotal_total_kW"].sum())

print("Share of cooling electricity (%):",
      100 * df_hourly["Pcool_elec_total_kW"].sum() / df_hourly["Peltotal_total_kW"].sum())

print("Share of non-HVAC electricity (%):",
      100 * df_hourly["Pnonhvac_total_kW"].sum() / df_hourly["Peltotal_total_kW"].sum())
