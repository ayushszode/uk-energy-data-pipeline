# UK Electricity Demand & Carbon Data Pipeline

An end-to-end data pipeline on real, public UK energy data. Python extracts four sources, DuckDB stores
them, **dbt** cleans, tests and models them into a star schema, and the results feed an analysis, a
next-day peak demand forecast and a Streamlit dashboard. GitHub Actions tests every change and refreshes
the data every week.

**Live dashboard:** _link added after deployment_ · **Data catalogue & lineage (dbt docs):** _link added after deployment_

---

## In short

| | |
|---|---|
| **Question** | How much electricity does Great Britain use, how clean is it, and what drives both? |
| **Data** | NESO half-hourly demand, Carbon Intensity API (national + regional), Open-Meteo weather, GOV.UK bank holidays |
| **Stack** | Python, DuckDB, dbt (dbt-duckdb), SQL, scikit-learn, Streamlit, Plotly, GitHub Actions |
| **Tests** | dbt generic + custom tests on every model, singular data-quality tests, pytest unit tests, dashboard smoke test |
| **Automation** | CI on every push; weekly scheduled refresh that only publishes if every dbt test passes |

## Pipeline

```
NESO · Carbon Intensity API · Open-Meteo · GOV.UK
        │  extract.py  (monthly raw files, values kept as text)
        ▼
data/raw/<source>/YYYY-MM.csv.gz
        │  load.py  (+ _source_file, _loaded_at for lineage)
        ▼
DuckDB  raw schema
        │  dbt
        ├─ staging       types, two date formats unified, repeats removed, forecasts flagged
        ├─ intermediate  correct UTC/local time per settlement period (46/48/50 per day), GB weather series
        └─ marts         fct_electricity_half_hourly · fct_daily_electricity · fct_regional_carbon_half_hourly
                         dim_date · dim_region
        │
        ├─ analysis.py   findings (reports/findings.md)
        ├─ forecast.py   next-day peak demand vs baselines
        └─ export.py ──► Streamlit dashboard
```

## Results

_Filled in from `reports/findings.md` and `reports/forecast_summary.json` after the first full run._

## Data quality built in

- **Clock changes:** GB settlement periods count from UK midnight, so the day the clocks go forward has
  46 half hours and the day they go back has 50. A dbt test checks every day has the right number.
- **Changing formats:** NESO's yearly files use different date formats; staging accepts both and a test
  fails if any date cannot be parsed.
- **Repeats and forecasts:** repeated rows are removed (the newest file wins) and forecast rows are kept
  out of the actuals.
- **Grain and joins:** every model has a tested grain, and a test checks the fact table keeps every
  demand period after its joins.
- **Cross-source checks:** the generation mix should move against carbon intensity, and NESO's
  interconnector flows should move with the API's imports share. Both are tested.

## How to run

```bash
make setup      # install
make test       # unit tests
make extract    # download data (about 5-10 minutes the first time)
make pipeline   # load -> dbt build -> analysis -> forecast -> export
make app        # dashboard at http://localhost:8501
make docs       # dbt catalogue and lineage at http://localhost:8080
```

## Repository guide

| Path | What it holds |
|---|---|
| `src/energy_pipeline/` | extract, load, analysis, forecast and export code |
| `dbt/models/` | staging, intermediate and mart models with their tests and docs |
| `dbt/tests/` | custom generic tests and singular data-quality tests |
| `data/raw/` | raw monthly files (unchanged source values) |
| `app/` | Streamlit dashboard |
| `docs/` | methodology, data sources, case study, interview guide |
| `.github/workflows/` | CI, full extract and weekly refresh |

## Data sources

NESO Data Portal (NESO Open Data Licence), Carbon Intensity API (CC BY 4.0), Open-Meteo (CC BY 4.0),
GOV.UK bank holidays (OGL v3). See [docs/data_sources.md](docs/data_sources.md).

---

Ayush Zode · [LinkedIn](https://www.linkedin.com/in/ayushsanjayzode) · [Portfolio](https://ayushszode-portfolio-nm22.vercel.app)
