# Data sources and licences

| Source | What is used | Licence | Notes |
|---|---|---|---|
| [NESO Data Portal - Historic Demand Data](https://www.neso.energy/data-portal/historic-demand-data) | Half-hourly National Demand, transmission demand, embedded wind and solar estimates, interconnector flows | NESO Open Data Licence | One CSV per year; the current year's file is updated regularly. Date formats differ between years. |
| [Carbon Intensity API](https://carbonintensity.org.uk) (NESO with the University of Oxford and Environmental Defense Fund Europe) | National intensity (forecast + actual), national generation mix, regional intensity forecasts and mix | CC BY 4.0 | Requests are limited to 14 days, so the extract works in 14-day windows. Regional values are forecasts only. |
| [Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api) | Hourly temperature, wind speed, solar radiation and cloud cover for nine GB cities | CC BY 4.0 | Reanalysis data, available with a delay of a few days. |
| [GOV.UK bank holidays](https://www.gov.uk/bank-holidays.json) | Bank holiday dates for England and Wales, Scotland and Northern Ireland | Open Government Licence v3.0 | |

All four sources are free and need no API key. Raw files are stored unchanged
(as text) in `data/raw/<source>/YYYY-MM.csv.gz`.
