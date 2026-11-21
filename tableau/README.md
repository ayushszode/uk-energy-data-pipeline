# Tableau data

Clean CSV exports of the dbt marts, ready for a Tableau Public dashboard.
Built from `app_data/` (see `docs/` for definitions). Add each file as its own data source; do not join them.

| File | Grain | Rows |
|---|---|---|
| 1_daily.csv | one complete day | 1,399 |
| 2_half_hourly.csv | one half hour | 67,152 |
| 3_regions_daily.csv | one region per day (14 DNO areas, from Jan 2025; latitude/longitude are approximate region centres) | 9,646 |
| 4_forecast_test.csv | one day and one series (actual or model), 2026 test period | 1,818 |
| 5_yearly_kpis.csv | one year (2026 = January to October) | 4 |

Rates and percentages should be averaged, not summed.
