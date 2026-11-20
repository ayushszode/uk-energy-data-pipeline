import csv
from pathlib import Path

from energy_pipeline import config

SEEDS = Path(__file__).resolve().parents[1] / "dbt" / "seeds"


def test_city_seed_matches_extract_config():
    with open(SEEDS / "cities.csv") as fh:
        seed = {(r["city"], float(r["latitude"]), float(r["longitude"]), float(r["population_weight_m"]))
                for r in csv.DictReader(fh)}
    assert seed == {(n, lat, lon, w) for n, lat, lon, w in config.CITIES}


def test_region_seed_has_api_ids_1_to_18():
    with open(SEEDS / "regions.csv") as fh:
        ids = [int(r["region_id"]) for r in csv.DictReader(fh)]
    assert ids == list(range(1, 19))
