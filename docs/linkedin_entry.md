# LinkedIn project entry

**Title:** UK Electricity Demand & Carbon Data Pipeline

**Description (about 1,000 characters):**
An automated data pipeline on public UK energy data. Python extracts half-hourly NESO demand, carbon
intensity from the Carbon Intensity API, weather from Open-Meteo and GOV.UK bank holidays. DuckDB stores
the raw data and dbt cleans, tests and models it into a star schema, with 67 tests covering grain, valid
ranges, relationships and cross-source checks. The tricky parts were real-world data issues: days with 46
or 50 half hours when the clocks change, three different date formats across NESO's yearly files, and API
gaps. Results: carbon intensity fell from 152 to 121 g/kWh between 2023 and 2026; half hours with 50%+
wind and solar averaged 67 g/kWh against 209 below 20%; and a next-day peak demand forecast reached 2.8%
error, half that of a simple baseline. GitHub Actions runs the tests on every change and refreshes the
data weekly.

**Skills:** dbt · SQL · Python · Data Engineering · Data Quality · DuckDB · GitHub Actions · Forecasting
