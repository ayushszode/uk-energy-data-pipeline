# Findings

Data from **2023-01-01** to **2026-10-30**: 67,152 half hours over 1,399 days.

- **Season:** average daily peak demand is highest in Winter (39,139 MW) and lowest in Summer (26,952 MW).
- **Working days:** weekends and bank holidays use 11.9% less electricity than working days.
- **Trend:** average National Demand changed by 0.4% from 2023 (26,052 MW) to 2025 (26,158 MW).
- **Solar dip:** at 13:00 in June, local solar averages 9,280 MW, so National Demand (21,140 MW) sits well below underlying demand (32,264 MW).
- **Renewables:** when wind and solar supply under 20% of generation, carbon intensity averages 209 g/kWh; at 50% or more it averages 67 g/kWh.
- **Best time to use electricity:** Autumn: cleanest around 02:00, dirtiest around 18:00; Spring: cleanest around 13:00, dirtiest around 19:00; Summer: cleanest around 13:00, dirtiest around 20:00; Winter: cleanest around 03:00, dirtiest around 16:00.
- **Regions (2025-01-01 to 2026-11-20):** South Scotland has the cleanest electricity (13 g/kWh forecast) and South Wales the most carbon-intensive (256 g/kWh).
- **Weather:** on working days, daily demand and temperature have a correlation of -0.815 (colder days use more electricity).

## Data quality

- 0 repeated demand rows removed; 0 dates could not be parsed; 0 forecast rows excluded.
- Date formats seen in the NESO files: DD-MON-YYYY (17,568 rows), DD-Mon-YY (17,520 rows), YYYY-MM-DD (32,064 rows).
- 8 clock-change days found and handled (46 or 50 settlement periods).
- Half hours without carbon intensity: 127; without temperature: 0.
- Interconnector sign check: correlation between NESO net flow and the API imports share is 0.799.
