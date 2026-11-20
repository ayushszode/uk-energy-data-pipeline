# Common tasks. Run `make setup` once, then `make pipeline`.
PY ?= python

.PHONY: setup test extract refresh load dbt docs analysis forecast export pipeline app clean

setup:            ## install dependencies and this package
	$(PY) -m pip install -r requirements.txt
	$(PY) -m pip install -e .

test:             ## unit tests (no network or warehouse needed)
	$(PY) -m pytest -q

extract:          ## download any missing months of raw data
	$(PY) -m energy_pipeline.extract --end current

refresh:          ## re-download the last two months (used by the weekly workflow)
	$(PY) -m energy_pipeline.extract --end current --refresh-recent 2

load:             ## raw CSV files -> DuckDB raw schema
	$(PY) -m energy_pipeline.load

dbt:              ## build and test every dbt model
	dbt build --project-dir dbt --profiles-dir dbt

docs:             ## dbt docs (catalogue + lineage) at http://localhost:8080
	dbt docs generate --project-dir dbt --profiles-dir dbt
	dbt docs serve --project-dir dbt --profiles-dir dbt

analysis:
	$(PY) -m energy_pipeline.analysis

forecast:
	$(PY) -m energy_pipeline.forecast

export:
	$(PY) -m energy_pipeline.export

pipeline: load dbt analysis forecast export   ## everything after extraction

app:              ## run the dashboard locally
	streamlit run app/streamlit_app.py

clean:
	rm -rf warehouse dbt/target dbt/logs
