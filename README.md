# UK Electricity Demand & Carbon Data Pipeline

An end-to-end data pipeline on real, public UK energy data. Python extracts four sources, DuckDB stores
them, **dbt** cleans, tests and models them into a star schema, and the results feed an analysis, a
next-day peak demand forecast and a Streamlit dashboard. GitHub Actions tests every change and refreshes
the data every week.

**Live dashboard:** [uk-energy-pipeline-ayushszode.streamlit.app](https://uk-energy-pipeline-ayushszode.streamlit.app) · **Data catalogue & lineage (dbt docs):** _published with GitHub Pages_

---

## In short

| | |
|---|---|
| **Question** | How much electricity does Great Britain use, how clean is it, and what drives both? |
| **Data** | NESO half-hourly demand, Carbon Intensity API (national + regional), Open-Meteo weather, GOV.UK bank holidays |
| **Stack** | Python, DuckDB, dbt (dbt-duckdb), SQL, scikit-learn, Streamlit, Plotly, GitHub Actions |
| **Tests** | 67 dbt tests (generic, custom generic and singular), 18 pytest unit tests, a smoke test of every dashboard page |
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

Data: **1 January 2023 to 30 October 2026** - 67,152 half hours over 1,399 days (regional data from January 2025).
All numbers below come from [`reports/findings.md`](reports/findings.md) and
[`reports/forecast_summary.json`](reports/forecast_summary.json).

**Demand**
- Average daily peak demand is **39,139 MW in winter** and **26,952 MW in summer**.
- Weekends and bank holidays use **11.9% less** electricity than working days.
- On working days, daily demand and temperature have a correlation of **-0.82**: colder days use more.
- **Solar dip:** at 13:00 in June, local solar averages 9,280 MW, so the grid supplies 21,140 MW
  against underlying demand of 32,264 MW. The lowest National Demand in the data was **12,626 MW at
  13:00 on 24 May 2026**, when local solar was about 15,400 MW.

**Carbon**
- Average carbon intensity fell from **152 g/kWh in 2023 to 121 g/kWh in 2026** as the wind and solar
  share rose from 34% to 41% and gas fell from 32% to about 25%.
- When wind and solar supply under 20% of generation, intensity averages **209 g/kWh**; at 50% or more
  it averages **67 g/kWh**. Zero-carbon share and intensity have a correlation of -0.92.
- **Best time to use power:** around 13:00 in spring and summer (solar), and overnight in autumn and
  winter. The dirtiest time is the early-evening peak (16:00-20:00 depending on the season).
- **Regions (2025-2026 forecasts):** South Scotland is cleanest (13 g/kWh); South Wales (256 g/kWh) and
  South West England (237 g/kWh) are the most carbon-intensive.

**Forecast: tomorrow's peak demand**

| Model | Validation MAE (Jul-Dec 2025) | Test MAE (Jan-Oct 2026) | Test error % |
|---|---|---|---|
| Same day last week | 1,614 MW | 1,748 MW | 5.4% |
| Yesterday | 1,466 MW | 1,520 MW | 4.9% |
| Gradient boosting, no weather | 988 MW | 976 MW | 3.1% |
| Gradient boosting | 899 MW | 913 MW | 2.9% |
| **Ridge regression (chosen)** | **854 MW** | **874 MW** | **2.8%** |

The model with the lowest validation error (ridge) was chosen before the test set was used. On 303 test
days it halves the error of "same day last week": **875 MW better (95% bootstrap interval 700 to 1,066 MW)**.
Weather features improve gradient boosting by about 60 MW. Caveat: the forecast day's temperature is the
observed value, standing in for a weather forecast, so the weather models' error is a best case.

**Data quality**
- **67 dbt tests: 66 pass, 1 warning.** The warning is real: the Carbon Intensity API has two outages
  (about 2 days in October 2023 and 15 hours in June 2024), which the gap test reports.
- All **8 clock-change days** have exactly 46 or 50 settlement periods.
- NESO's yearly files use **three different date formats** (`01-Jan-23`, `01-JAN-2024`, `2025-01-01`);
  all 67,152 rows parse.
- The Carbon Intensity API returned incomplete data for requests crossing 1 January and for some single
  days; the extract now splits requests at the new year and re-asks for any day with fewer than 48 half hours.
- Cross-source check: NESO's net interconnector flow and the API's imports share have a correlation of
  0.80, which confirms the flow sign convention.

## Data quality built in

- **Clock changes:** GB settlement periods count from UK midnight, so the day the clocks go forward has
  46 half hours and the day they go back has 50. A dbt test checks every day has the right number.
- **Changing formats:** NESO's yearly files use three different date formats; staging accepts all of
  them and a test fails if any date cannot be parsed.
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
