"""Load: copy the raw monthly CSV files into DuckDB tables in the `raw` schema.

    python -m energy_pipeline.load

Every column is loaded as text (all_varchar) so nothing is silently changed on
the way in. Each row keeps the file it came from (_source_file) and when it was
loaded (_loaded_at), which gives row-level lineage back to the raw files.
Type casting and cleaning happen in the dbt staging models.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import duckdb

from . import config

TABLES = {
    "neso_demand": "demand/*.csv.gz",
    "carbon_national": "carbon_national/*.csv.gz",
    "generation_mix": "generation_mix/*.csv.gz",
    "carbon_regional": "carbon_regional/*.csv.gz",
    "weather_hourly": "weather/*.csv.gz",
    "bank_holidays": "bank_holidays/*.csv.gz",
}


def load(database: str | None = None) -> dict[str, int]:
    db_path = database or str(config.WAREHOUSE)
    config.WAREHOUSE.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(db_path)
    con.execute("SET TimeZone = 'UTC'")
    con.execute("CREATE SCHEMA IF NOT EXISTS raw")
    loaded_at = datetime.now(timezone.utc).replace(tzinfo=None)
    counts: dict[str, int] = {}
    for table, pattern in TABLES.items():
        files = sorted((config.RAW_DIR).glob(pattern))
        if not files:
            print(f"[load] no files for {table} ({pattern}) - skipped")
            continue
        file_list = "[" + ", ".join("'" + str(f).replace("'", "''") + "'" for f in files) + "]"
        con.execute(
            f"""
            CREATE OR REPLACE TABLE raw.{table} AS
            SELECT * EXCLUDE (filename),
                   regexp_extract(filename, '[^/]+/[^/]+$') AS _source_file,
                   TIMESTAMP '{loaded_at:%Y-%m-%d %H:%M:%S}' AS _loaded_at
            FROM read_csv({file_list}, all_varchar = true, header = true, filename = true,
                          union_by_name = true, compression = 'gzip')
            """
        )
        counts[table] = con.execute(f"SELECT count(*) FROM raw.{table}").fetchone()[0]
        print(f"[load] raw.{table}: {counts[table]:,} rows from {len(files)} files")
    con.close()
    config.REPORTS_DIR.mkdir(exist_ok=True)
    (config.REPORTS_DIR / "load_report.json").write_text(json.dumps(
        {"loaded_at": loaded_at.isoformat(timespec="seconds"), "rows": counts}, indent=2))
    return counts


if __name__ == "__main__":
    load()
