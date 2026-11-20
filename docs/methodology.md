# Methodology

## Pipeline layers

1. **Extract** (`src/energy_pipeline/extract.py`) - downloads each source and writes one raw CSV per
   source per month. Values are kept exactly as received (text). A refresh only re-downloads the newest months.
2. **Load** (`load.py`) - copies the raw files into DuckDB's `raw` schema, all columns as text, adding
   `_source_file` and `_loaded_at` to every row for lineage.
3. **Staging** (dbt) - one view per source: cast types, unify the two NESO date formats, flag forecast
   rows, and remove repeated rows (the newest file wins).
4. **Intermediate** (dbt) - work out the correct UTC and UK local start time for every settlement period,
   join intensity to generation mix, and build one GB weather series.
5. **Marts** (dbt) - a star schema:
   - `fct_electricity_half_hourly` - grain: one settlement period
   - `fct_daily_electricity` - grain: one day
   - `fct_regional_carbon_half_hourly` - grain: one region and half hour
   - `dim_date`, `dim_region`

## Settlement periods and clock changes

GB electricity is settled in half hours counted from UK local midnight. Most days have 48 periods.
On the last Sunday of March the clocks go forward, so the day has 46; on the last Sunday of October
they go back, so it has 50. The period start time is calculated as:

    UTC start = (local midnight of the settlement date, converted to UTC) + (period - 1) x 30 minutes

The singular test `assert_settlement_periods_match_clock` checks that every complete day has exactly
the number of periods the clock implies, using DuckDB's time-zone functions.

## Definitions

- **National Demand (ND)** - NESO's transmission-level demand. It does not include electricity from wind
  and solar connected to local networks.
- **Underlying demand** - ND plus NESO's embedded wind and solar estimates. An approximation of total demand.
- **Wind + solar share / zero-carbon share** - from the Carbon Intensity API generation mix. Zero-carbon =
  wind + solar + nuclear + hydro.
- **GB temperature** - population-weighted average of nine large cities (weights are rough urban-area
  populations in millions). Hourly values are used for both half hours in the hour.
- **Heating degree days** - max(15.5 C - daily average temperature, 0).

## Tests

- Generic tests on every model: unique grain, not null, valid ranges (`value_between`), accepted values,
  relationships between facts and dimensions, and generation-mix percentages adding up to 100.
- Singular tests: settlement periods per day, the fact table keeping every demand period, gaps in the
  carbon series (warning), weather coverage (warning), and two cross-source checks (warnings):
  zero-carbon share vs intensity, and NESO interconnector flows vs the API imports share.

## Forecast

Target: tomorrow's peak half-hourly National Demand. Features known the evening before: yesterday's peak,
the peak a week ago, the 7-day average, day of week, bank holiday, time of year, trend and temperature.
Time-based split: train before July 2025, validation July-December 2025, test from January 2026.
The model with the lowest validation MAE is chosen before the test set is used. A paired bootstrap gives a
95% interval for the improvement over "same day last week". Observed temperature stands in for a weather
forecast, so the weather models' test error is a best case; a model without weather is reported alongside.
