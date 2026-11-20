# Case study: UK Electricity Demand & Carbon Data Pipeline

## The problem

Great Britain's electricity data is public but spread across several sources, each with its own format,
time convention and quirks. To answer simple questions - when is electricity cleanest, how much does
the weather drive demand, how well can tomorrow's peak be predicted - the data first has to be brought
together reliably, kept up to date, and trusted.

## What I built

An automated pipeline that a data team could run in production:

1. **Extract** - Python downloads NESO half-hourly demand, Carbon Intensity API national and regional
   data, Open-Meteo weather for nine cities and GOV.UK bank holidays. Raw values are stored unchanged,
   one file per source per month, so the weekly refresh only re-downloads recent months.
2. **Load** - DuckDB stores the raw files as text with the source file and load time on every row.
3. **Transform and test with dbt** - staging (types, formats, repeats), intermediate (correct timestamps,
   joins), and marts (a star schema at half-hourly, daily and regional grain). 67 tests cover grain,
   ranges, relationships and cross-source consistency.
4. **Use** - an analysis report, a next-day peak demand forecast, and a Streamlit dashboard.
5. **Automate** - GitHub Actions runs everything on each change and refreshes the data weekly, publishing
   only if every test passes. dbt docs give a searchable data catalogue with lineage.

## Problems I had to solve

- **Clock changes.** Settlement periods count from UK midnight, so days have 46, 48 or 50 half hours. I
  convert local midnight to UTC first and then add periods, and test every day's count against the clock.
- **Three date formats.** NESO's 2023 file uses `01-Jan-23`, 2024 uses `01-JAN-2024` and 2025-2026 use
  `2025-01-01`. The first run silently skipped all of 2023 until the extract report showed 17,520
  unparsed rows; I added the third format to both the extract and the dbt staging model, with a unit test.
- **API quirks.** The Carbon Intensity API limits requests to 14 days, and its generation-mix and regional
  endpoints returned incomplete data for requests crossing 1 January. I split requests at the new year
  and added a check that re-asks, day by day, for any day with fewer than 48 half hours.
- **Values like "72.0".** Carbon intensity arrived as decimals stored as text, so a direct cast to integer
  gave nulls; staging casts to a number first and then rounds.
- **Telling real gaps from bugs.** After the fixes, two gaps remain (about 2 days in October 2023 and 15
  hours in June 2024). They are outages at the source, so the test reports them as a warning rather than
  failing the pipeline.

## Results

- 67,152 half hours (January 2023 to October 2026); 66 of 67 dbt tests pass, 1 warning (the outages).
- Carbon intensity fell from 152 g/kWh (2023) to 121 g/kWh (2026). Half hours with at least 50% wind and
  solar average 67 g/kWh, against 209 g/kWh below 20%.
- Solar cuts the grid's midday demand: at 13:00 in June the grid supplies about 21 GW against 32 GW of
  underlying demand. The lowest National Demand was 12.6 GW at 13:00 on 24 May 2026.
- The next-day peak forecast (ridge regression, chosen on validation) has a test error of 874 MW (2.8%),
  half the error of "same day last week" (1,748 MW); the improvement's 95% interval is 700-1,066 MW.

## What I would do next

Move the warehouse to BigQuery or Snowflake with scheduled dbt runs, use weather forecasts for a true
day-ahead model, make the large models incremental, and add half-hourly demand forecasting.
