# Start here

1. **README.md** - what the project does and the results.
2. **docs/methodology.md** - how each layer works, definitions and tests.
3. **dbt/models/** - the SQL: `staging` → `intermediate` → `marts`. Read `fct_electricity_half_hourly.sql` first.
4. **dbt/tests/assert_settlement_periods_match_clock.sql** - the clock-change test (a good interview story).
5. **reports/findings.md** and **reports/forecast_summary.json** - every number in the README.
6. **docs/interview_guide.md** - how to explain the project, with likely questions.
7. **app/streamlit_app.py** - the dashboard.

To run it yourself: `make setup && make test && make extract && make pipeline && make app`.
