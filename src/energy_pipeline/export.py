"""Export small, ready-to-plot tables for the Streamlit dashboard.

    python -m energy_pipeline.export

The dashboard reads these compressed CSVs instead of the DuckDB file, so it
deploys quickly on Streamlit Community Cloud without running dbt.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import duckdb

from . import config

QUERIES = {
    "daily": "select * from marts.fct_daily_electricity order by settlement_date",
    "half_hourly": """
        select settlement_date, settlement_period, period_start_local, local_hour, local_time_label,
               round(national_demand_mw) as national_demand_mw, round(underlying_demand_mw) as underlying_demand_mw,
               round(embedded_solar_mw) as embedded_solar_mw, round(embedded_wind_mw) as embedded_wind_mw,
               intensity_actual, round(wind_solar_pct, 1) as wind_solar_pct, round(zero_carbon_pct, 1) as zero_carbon_pct,
               round(gas_pct, 1) as gas_pct, round(nuclear_pct, 1) as nuclear_pct, round(imports_pct, 1) as imports_pct,
               round(wind_pct, 1) as wind_pct, round(solar_pct, 1) as solar_pct, round(temperature_c, 1) as temperature_c
        from marts.fct_electricity_half_hourly order by period_start_utc""",
    "profile_by_time": """
        select d.season, f.local_time_label,
               round(avg(f.national_demand_mw)) as national_demand_mw,
               round(avg(f.underlying_demand_mw)) as underlying_demand_mw,
               round(avg(f.embedded_solar_mw)) as embedded_solar_mw,
               round(avg(f.intensity_actual)) as avg_intensity
        from marts.fct_electricity_half_hourly f join marts.dim_date d on d.date_key = f.date_key
        group by 1, 2 order by 1, 2""",
    "regional_daily": """
        select f.local_date, r.region_id, r.region_name, r.region_type,
               round(avg(f.intensity_forecast), 1) as avg_intensity,
               round(avg(f.zero_carbon_pct), 1) as avg_zero_carbon_pct,
               round(avg(f.wind_pct), 1) as avg_wind_pct, round(avg(f.gas_pct), 1) as avg_gas_pct
        from marts.fct_regional_carbon_half_hourly f join marts.dim_region r using (region_id)
        group by all order by 1, 2""",
    "regional_hour_profile": """
        select r.region_name, hour(f.period_start_local) as local_hour, round(avg(f.intensity_forecast), 1) as avg_intensity
        from marts.fct_regional_carbon_half_hourly f join marts.dim_region r using (region_id)
        where r.region_type = 'DNO area' group by all order by 1, 2""",
    "clock_change_days": """
        select cast(d.date_day as varchar) as date, d.clock_change, d.expected_settlement_periods, x.periods_reported
        from marts.dim_date d left join marts.fct_daily_electricity x on x.settlement_date = d.date_day
        where d.is_clock_change_day order by 1""",
}


def dbt_test_summary(run_results: Path) -> dict:
    """Summarise dbt's run_results.json: how many tests passed, warned or failed."""
    if not run_results.exists():
        return {}
    data = json.loads(run_results.read_text())
    tests = [r for r in data.get("results", []) if r.get("unique_id", "").startswith("test.")]
    models = [r for r in data.get("results", []) if r.get("unique_id", "").startswith(("model.", "seed."))]
    summary = {"tests": len(tests), "models_and_seeds": len(models), "by_status": {}, "warnings": [], "failures": []}
    for r in tests:
        status = r.get("status")
        summary["by_status"][status] = summary["by_status"].get(status, 0) + 1
        if status in ("warn", "fail", "error"):
            entry = {"test": r["unique_id"].split(".")[2], "failing_rows": r.get("failures"), "message": r.get("message")}
            summary["warnings" if status == "warn" else "failures"].append(entry)
    summary["generated_at"] = data.get("metadata", {}).get("generated_at")
    return summary


def main() -> None:
    out = config.APP_DATA_DIR
    out.mkdir(exist_ok=True)
    con = duckdb.connect(str(config.WAREHOUSE), read_only=True)
    for name, sql in QUERIES.items():
        try:
            df = con.execute(sql).df()
        except duckdb.Error as exc:  # e.g. no regional data yet
            print(f"[export] {name} skipped: {exc}")
            continue
        df.to_csv(out / f"{name}.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})
        print(f"[export] {name}: {len(df):,} rows")
    con.close()

    for name in ("findings.json", "findings.md", "forecast_metrics.csv", "forecast_test_predictions.csv",
                 "forecast_summary.json", "load_report.json", "extract_report.json"):
        src = config.REPORTS_DIR / name
        if src.exists():
            shutil.copy(src, out / name)
    quality = dbt_test_summary(config.ROOT / "dbt" / "target" / "run_results.json")
    (out / "dbt_test_summary.json").write_text(json.dumps(quality, indent=2))
    (config.REPORTS_DIR / "dbt_test_summary.json").write_text(json.dumps(quality, indent=2))
    print(f"[export] dbt tests: {quality.get('by_status')}")


if __name__ == "__main__":
    main()
