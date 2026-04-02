# energy-load-simulation
Generation of historical electricity, heating, and cooling load profiles using physics-based modeling approaches.

Urban Energy Load Simulation – Ixelles (Brussels)


This project generates hourly heating, cooling, and electricity load profiles for residential buildings in Ixelles (Brussels), using a physics-based modeling approach.

The methodology combines:

Geospatial data (OpenStreetMap / GeoJSON)
Building energy assumptions
Weather data (NASA POWER)
Thermodynamic modeling (heat balance + heat pumps)

Methodology
1. Data Extraction
Extract buildings from GeoJSON
Filter residential buildings (apartments, house, residential)
2. Data Cleaning
Remove invalid geometries
Reproject to metric CRS (EPSG:31370)
Remove small or duplicate buildings
3. Surface Estimation
Compute ground surface area
Estimate number of floors
Compute total building area

4. Annual Heating Demand
Assign specific heat demand (Qspec)
Compute annual heating energy:

Heating = Area × Qspec

5. Thermal Model

The model is based on a dynamic heat balance:

Heat losses:
Q_loss = G × (T_indoor - T_outdoor)
Indoor temperature evolution:
Tin(t+1) = Tin(t) + (Qheating + Qgain + Qsolar - Qloss - Qcooling) / k

Where:

G = heat loss coefficient
k = thermal capacity
Qmax = maximum heating/cooling power

6. Heating & Cooling Simulation

For each hour:

Occupancy is simulated
Setpoint temperatures vary
Internal and solar gains are computed
Heating and cooling demands are calculated

Constraints:

Heating limited by Qmax
No simultaneous heating and cooling
7. Heat Pump Modeling

Performance is based on Carnot efficiency:

Heating:
COP ≈ η × (T_hot / ΔT)
Cooling:
EER ≈ η × (T_cold / ΔT)

8. Electricity Demand

Total electricity is computed as:

P_total = P_HVAC + P_nonHVAC

Where:

HVAC includes heating and cooling electricity
Non-HVAC is estimated from internal gains
