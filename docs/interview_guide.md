# Interview guide

How to explain this project in an interview, in plain words. Numbers come from
`reports/findings.md` and `reports/forecast_summary.json`.

## The 30-second version

"I built an automated data pipeline on public UK electricity data. Python pulls half-hourly demand
from NESO, carbon intensity from the Carbon Intensity API, weather from Open-Meteo and bank holidays
from GOV.UK. I load the raw files into DuckDB and use dbt to clean, test and model them into a star
schema, with tests on every table. The output feeds an analysis, a next-day peak demand forecast and a
Streamlit dashboard. GitHub Actions runs the tests on every change and refreshes the data every week,
and it only publishes new data if every test passes."

## Questions you should expect

**Why dbt?**
It turns SQL into a tested, documented project. Each model is one SELECT, dbt works out the order from
`ref()`, runs tests on every model, and generates a data catalogue with a lineage graph. That is how
data teams keep transformations reliable and understandable.

**Why DuckDB?**
It is a free, fast analytical database that runs as a file, so the whole warehouse runs on a laptop or
in GitHub Actions without a server. The same dbt models would work on Snowflake or BigQuery by changing
the adapter.

**Explain your layers.**
- *Raw*: exactly what the source sent, as text, plus the file it came from and when it was loaded.
- *Staging*: one model per source - cast types, unify formats, remove repeats. No business logic.
- *Intermediate*: the reusable logic - correct timestamps for each settlement period, joining intensity
  to the generation mix, one weather series for GB.
- *Marts*: a star schema for analysis - fact tables at a clear grain plus date and region dimensions.

**What is the grain of your main fact table?**
One row per GB settlement period (half hour), identified by settlement date + settlement period, or by
the UTC start time. Both are tested as unique.

**What was the hardest data problem?**
Clock changes. Settlement periods count from UK local midnight, so the day the clocks go forward has 46
half hours and the day they go back has 50. If you just multiply the period number by 30 minutes from a
UTC midnight, you get the wrong times and duplicate hours. I convert local midnight to UTC first and then
add the periods, and a dbt test checks every day has exactly 46, 48 or 50 periods depending on the clock.

**What other data quality issues did you handle?**
- NESO's yearly files use different date formats (`2024-01-31` and `31-JAN-2024`) - staging handles both
  and a test fails if any date cannot be parsed.
- Rows can appear in more than one file - staging keeps the newest file's row.
- The current year's file can contain forecasts - those are flagged and kept out of the actuals.
- The Carbon Intensity API only allows 14 days per request, and windows overlap at the edges - the
  extract works in windows and removes the repeats.
- Cross-source checks: a higher zero-carbon share should go with lower carbon intensity, and NESO's
  interconnector flows should move with the API's imports share.

**How do you make the refresh safe?**
Raw files are stored one per month, so the weekly job only re-downloads the newest months (idempotent:
running it twice gives the same result). The workflow runs `dbt build`, and if any test fails it stops
before committing, so broken data is never published. Freshness checks warn if a source stops updating.

**What are warnings vs failures?**
Failures block the pipeline (wrong grain, impossible values, missing periods). Warnings are things to
review that do not make the data wrong, such as a short gap in the public carbon API.

**How did you evaluate the forecast?**
By time: train before July 2025, choose the model on July-December 2025, test once on 2026. I compared
against simple baselines (yesterday, same day last week) because a model is only useful if it beats
them. I used a paired bootstrap on the test days to get a confidence interval for the improvement.

**What are the limitations?**
- The forecast uses observed temperature for the forecast day; a real system would use a weather
  forecast, so my weather models' error is a best case. I report a model without weather as well.
- Underlying demand is an estimate (NESO's embedded wind and solar figures are themselves modelled).
- Regional carbon values are forecasts; the API only publishes actuals nationally.
- GB temperature is a population-weighted average of nine cities, not a full national average.

**What would you do next?**
Move the warehouse to a cloud platform (BigQuery or Snowflake) with dbt Cloud or Airflow scheduling,
use weather forecasts for a true day-ahead model, add incremental dbt models, and add half-hourly
forecasting.
