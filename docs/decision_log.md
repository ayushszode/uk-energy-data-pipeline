# Decision log

| # | Decision | Why |
|---|---|---|
| 1 | DuckDB as the warehouse | Free, fast, file-based: runs the same on a laptop and in GitHub Actions. dbt models would move to BigQuery/Snowflake by changing the adapter. |
| 2 | Raw files kept as text, one per source per month | The raw layer shows exactly what the source sent; monthly files make refreshes small and repeatable. |
| 3 | All cleaning in dbt staging, not in Python | One place for transformation logic, tested and documented with lineage. |
| 4 | Timestamps stored as UTC; local time derived | UTC has no gaps or repeats; UK local time is calculated from it for reporting. |
| 5 | Settlement period start = local midnight converted to UTC + (period - 1) x 30 min | The only correct method on 46- and 50-period days. |
| 6 | Custom generic tests (`value_between`, `unique_combination`, `percentages_sum_to`) | No external packages needed, and they show how dbt tests work. |
| 7 | Gaps in the carbon series are a warning, not a failure | They are outages at the source; failing would block every refresh without making the data wrong. |
| 8 | Split carbon requests at 1 January and re-fetch short days | The first run found missing January data from the generation and regional endpoints. |
| 9 | Accept three NESO date formats | The 2023 file (`01-Jan-23`) was silently skipped in the first run; the extract report exposed it. |
| 10 | Forecast target = next-day peak National Demand | Peaks drive grid planning; daily peaks keep the model simple and explainable. |
| 11 | Model chosen by validation MAE before testing | Avoids picking the model that happens to do best on the test set. |
| 12 | Report a model without weather features | Observed temperature stands in for a forecast, so this shows how much weather really adds. |
| 13 | Streamlit dashboard instead of Power BI | Runs on any OS and deploys free; Power BI Desktop is Windows-only. |
| 14 | Weekly refresh commits only after `dbt build` passes | Broken data is never published. |
