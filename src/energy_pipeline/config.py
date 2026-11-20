"""Project settings: date range, folders and data-source details.

Everything that a reader might want to change lives here, so the extract,
load and analysis code does not hide magic numbers.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
WAREHOUSE = ROOT / "warehouse" / "energy.duckdb"
REPORTS_DIR = ROOT / "reports"
APP_DATA_DIR = ROOT / "app_data"

# First month of data. Regional carbon data is larger, so it starts later.
START_MONTH = "2023-01"
REGIONAL_START_MONTH = "2025-01"

# Source endpoints (all free, no API key needed).
NESO_PACKAGE_URL = "https://api.neso.energy/api/3/action/package_show?id=historic-demand-data"
CARBON_API = "https://api.carbonintensity.org.uk"
OPEN_METEO_ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"
BANK_HOLIDAYS_URL = "https://www.gov.uk/bank-holidays.json"

# The Carbon Intensity API accepts at most 14 days per request.
CARBON_WINDOW_DAYS = 14

# Fuels reported in the Carbon Intensity API generation mix.
FUELS = ["biomass", "coal", "imports", "gas", "nuclear", "other", "hydro", "solar", "wind"]

# Columns kept from the NESO historic demand files. Files differ slightly by
# year, so missing columns are written as empty values rather than dropped.
NESO_COLUMNS = [
    "SETTLEMENT_DATE", "SETTLEMENT_PERIOD", "ND", "TSD", "ENGLAND_WALES_DEMAND",
    "EMBEDDED_WIND_GENERATION", "EMBEDDED_WIND_CAPACITY",
    "EMBEDDED_SOLAR_GENERATION", "EMBEDDED_SOLAR_CAPACITY",
    "NON_BM_STOR", "PUMP_STORAGE_PUMPING", "SCOTTISH_TRANSFER",
    "IFA_FLOW", "IFA2_FLOW", "BRITNED_FLOW", "MOYLE_FLOW", "EAST_WEST_FLOW",
    "NEMO_FLOW", "NSL_FLOW", "ELECLINK_FLOW", "VIKING_FLOW", "GREENLINK_FLOW",
    "FORECAST_ACTUAL_INDICATOR",
]

# Weather is taken for large GB cities and weighted by rough urban-area
# population (millions) to approximate the temperature that drives demand.
# This is a simple approximation, documented in docs/methodology.md.
CITIES = [
    # name, latitude, longitude, weight
    ("London", 51.5074, -0.1278, 9.8),
    ("Birmingham", 52.4862, -1.8904, 2.4),
    ("Manchester", 53.4808, -2.2426, 2.6),
    ("Leeds", 53.8008, -1.5491, 1.8),
    ("Glasgow", 55.8642, -4.2518, 1.0),
    ("Newcastle", 54.9783, -1.6178, 0.8),
    ("Bristol", 51.4545, -2.5879, 0.6),
    ("Cardiff", 51.4816, -3.1791, 0.45),
    ("Edinburgh", 55.9533, -3.1883, 0.5),
]
WEATHER_HOURLY = ["temperature_2m", "wind_speed_10m", "shortwave_radiation", "cloud_cover"]

HTTP_TIMEOUT = 60
USER_AGENT = "uk-energy-data-pipeline (github.com/ayushszode/uk-energy-data-pipeline)"
