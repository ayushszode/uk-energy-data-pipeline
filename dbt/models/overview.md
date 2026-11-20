{% docs __overview__ %}
# UK Electricity Demand & Carbon Data Pipeline

This dbt project turns raw public data into tested, documented tables:

* **Sources** - NESO Historic Demand Data, the Carbon Intensity API (national and regional),
  Open-Meteo historical weather and GOV.UK bank holidays.
* **Staging** - one model per source: types cast, formats unified, repeats removed.
* **Intermediate** - correct UTC and UK local times for each settlement period
  (46/48/50 periods per day), grouped generation shares, a GB weather series.
* **Marts** - a star schema: `fct_electricity_half_hourly`, `fct_daily_electricity`,
  `fct_regional_carbon_half_hourly`, `dim_date`, `dim_region`.

Every model has tests (unique grain, not null, valid ranges, relationships), plus
singular tests for clock-change days and gaps in the half-hourly series.
Use the lineage graph (bottom right) to follow any column back to its raw file.
{% enddocs %}
