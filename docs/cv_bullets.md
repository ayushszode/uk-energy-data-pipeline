# CV bullets

**UK Electricity Demand & Carbon Data Pipeline** *(Python, SQL, dbt, DuckDB, GitHub Actions, scikit-learn, Streamlit)*
- Built an automated pipeline that extracts half-hourly NESO demand, Carbon Intensity API, weather and
  bank-holiday data into DuckDB and models it with dbt into a tested star schema (67,152 half hours, 2023-2026).
- Wrote 67 dbt tests (grain, ranges, relationships, cross-source checks) and handled clock-change days
  (46/50 periods), three source date formats and API gaps; a weekly GitHub Actions refresh publishes only
  when every test passes.
- Forecast next-day peak demand with 2.8% error (874 MW), halving the error of a same-day-last-week
  baseline (95% CI for the improvement 700-1,066 MW), and built a Streamlit dashboard with dbt docs lineage.

Short version (one line):
- Built a dbt + DuckDB pipeline on UK electricity and carbon data with 67 data-quality tests, weekly
  automated refresh, a 2.8%-error peak demand forecast and a Streamlit dashboard.
