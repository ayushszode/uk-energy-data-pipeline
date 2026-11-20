"""Analysis: answer the project's questions from the dbt mart tables.

    python -m energy_pipeline.analysis

Writes reports/findings.json (numbers) and reports/findings.md (plain English).
Every number in the README and case study comes from this file.
"""
from __future__ import annotations

import json

import duckdb

from . import config


def _one(con, sql: str):
    return con.execute(sql).fetchone()


def _rows(con, sql: str) -> list[dict]:
    cur = con.execute(sql)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def compute(con: duckdb.DuckDBPyConnection) -> dict:
    f: dict = {}
    hh = "marts.fct_electricity_half_hourly"
    daily = "marts.fct_daily_electricity"

    first, last, n_hh = _one(con, f"select min(settlement_date), max(settlement_date), count(*) from {hh}")
    f["coverage"] = {"first_date": str(first), "last_date": str(last), "half_hours": n_hh,
                     "days": _one(con, f"select count(*) from {daily}")[0]}
    f["clock_change_days"] = _rows(con, f"""
        select cast(d.settlement_date as varchar) as date, d.clock_change, x.periods_reported
        from marts.dim_date d join {daily} x on x.settlement_date = d.date_day
        where d.is_clock_change_day order by 1""")
    full_years = [r["year"] for r in _rows(con, f"""
        select year from {daily} group by year having count(*) >= 365 order by year""")]
    f["full_years"] = full_years

    # 1. Demand patterns
    f["peak_by_year"] = _rows(con, f"""
        select year, round(avg(peak_demand_mw)) as avg_daily_peak_mw, round(max(peak_demand_mw)) as max_peak_mw,
               round(sum(demand_gwh) / 1000, 1) as demand_twh
        from {daily} where is_complete_day group by year order by year""")
    f["season_peak"] = _rows(con, f"""
        select season, round(avg(peak_demand_mw)) as avg_daily_peak_mw
        from {daily} where is_complete_day group by season order by avg_daily_peak_mw desc""")
    wk = _rows(con, f"""
        select is_weekend or is_bank_holiday_ew as non_working_day, round(avg(demand_gwh), 1) as avg_gwh
        from {daily} where is_complete_day group by 1 order by 1""")
    f["weekday_vs_weekend"] = wk
    if len(wk) == 2 and wk[0]["avg_gwh"]:
        f["weekend_drop_pct"] = round(100 * (wk[0]["avg_gwh"] - wk[1]["avg_gwh"]) / wk[0]["avg_gwh"], 1)
    if len(full_years) >= 2:
        y0, y1 = full_years[0], full_years[-1]
        a = _one(con, f"select avg(national_demand_mw) from {hh} where year(settlement_date) = {y0}")[0]
        b = _one(con, f"select avg(national_demand_mw) from {hh} where year(settlement_date) = {y1}")[0]
        f["demand_change"] = {"from_year": y0, "to_year": y1, "avg_nd_from": round(a), "avg_nd_to": round(b),
                              "change_pct": round(100 * (b - a) / a, 1)}

    # 2. Solar and the midday dip (National Demand vs underlying demand)
    f["june_midday"] = _rows(con, f"""
        select local_time_label, round(avg(national_demand_mw)) as national_demand_mw,
               round(avg(underlying_demand_mw)) as underlying_demand_mw, round(avg(embedded_solar_mw)) as solar_mw
        from {hh} where month(settlement_date) = 6 and local_time_label in ('07:00', '13:00', '18:00')
        group by 1 order by 1""")
    f["min_demand_record"] = _rows(con, f"""
        select cast(settlement_date as varchar) as date, local_time_label, round(national_demand_mw) as national_demand_mw,
               round(embedded_solar_mw) as solar_mw
        from {hh} order by national_demand_mw asc limit 1""")

    # 3. Carbon intensity and renewables
    f["intensity_by_year"] = _rows(con, f"""
        select year(settlement_date) as year, round(avg(intensity_actual)) as avg_intensity,
               round(avg(wind_solar_pct), 1) as avg_wind_solar_pct, round(avg(gas_pct), 1) as avg_gas_pct
        from {hh} where intensity_actual is not null group by 1 order by 1""")
    f["intensity_by_wind_solar_band"] = _rows(con, f"""
        select case when wind_solar_pct < 20 then '<20%' when wind_solar_pct < 50 then '20-50%' else '50%+' end as wind_solar_band,
               count(*) as half_hours, round(avg(intensity_actual)) as avg_intensity
        from {hh} where intensity_actual is not null and wind_solar_pct is not null
        group by 1 order by min(wind_solar_pct)""")
    f["corr_zero_carbon_intensity"] = round(_one(con, f"select corr(zero_carbon_pct, intensity_actual) from {hh}")[0], 3)

    # 4. Best and worst times to use electricity
    by_hour = _rows(con, f"""
        select season, local_hour, round(avg(intensity_actual)) as avg_intensity
        from {hh} where intensity_actual is not null group by 1, 2 order by 1, 2""")
    f["intensity_by_season_hour"] = by_hour
    best = {}
    for season in sorted({r["season"] for r in by_hour} if by_hour and "season" in by_hour[0] else []):
        rows = [r for r in by_hour if r["season"] == season]
        lo = min(rows, key=lambda r: r["avg_intensity"])
        hi = max(rows, key=lambda r: r["avg_intensity"])
        best[season] = {"cleanest_hour": lo["local_hour"], "cleanest": lo["avg_intensity"],
                        "dirtiest_hour": hi["local_hour"], "dirtiest": hi["avg_intensity"]}
    f["best_hours_by_season"] = best

    # 5. Regions (DNO areas only)
    if _one(con, "select count(*) from information_schema.tables where table_schema='marts' and table_name='fct_regional_carbon_half_hourly'")[0]:
        f["regions"] = _rows(con, """
            select r.region_name, round(avg(f.intensity_forecast)) as avg_intensity,
                   round(avg(f.zero_carbon_pct), 1) as avg_zero_carbon_pct, round(avg(f.wind_pct), 1) as avg_wind_pct
            from marts.fct_regional_carbon_half_hourly f join marts.dim_region r using (region_id)
            where r.region_type = 'DNO area'
            group by 1 order by avg_intensity""")
        f["regional_period"] = [str(x) for x in _one(con, """
            select min(local_date), max(local_date) from marts.fct_regional_carbon_half_hourly""")]

    # 6. Weather and demand
    f["corr_daily_demand_temperature"] = round(_one(con, f"""
        select corr(demand_gwh, avg_temperature_c) from {daily} where is_complete_day and not is_weekend""")[0], 3)
    f["corr_interconnector_imports"] = round(_one(con, f"select corr(net_interconnector_flow_mw, imports_pct) from {hh}")[0], 3)

    # 7. Data quality notes from raw -> staging
    raw_rows = _one(con, "select count(*) from raw.neso_demand")[0]
    stg_rows = _one(con, "select count(*) from staging.stg_neso__demand")[0]
    f["data_quality"] = {
        "raw_demand_rows": raw_rows,
        "staged_demand_rows": stg_rows,
        "repeated_rows_removed": raw_rows - stg_rows,
        "unparsed_dates": _one(con, "select count(*) from staging.stg_neso__demand where settlement_date is null")[0],
        "forecast_rows_excluded": _one(con, "select count(*) from staging.stg_neso__demand where is_forecast")[0],
        "date_formats": _rows(con, """
            select case when regexp_matches(settlement_date_raw, '^\\d{4}-') then 'YYYY-MM-DD'
                        when regexp_matches(settlement_date_raw, '^\\d{1,2}-[A-Za-z]{3}-') then 'DD-MON-YYYY'
                        else 'other' end as format, count(*) as rows
            from staging.stg_neso__demand group by 1 order by 1"""),
        "half_hours_missing_intensity": _one(con, f"select count(*) from {hh} where intensity_actual is null")[0],
        "half_hours_missing_temperature": _one(con, f"select count(*) from {hh} where temperature_c is null")[0],
    }
    return f


def to_markdown(f: dict) -> str:
    c = f["coverage"]
    lines = ["# Findings", "", f"Data from **{c['first_date']}** to **{c['last_date']}**: "
             f"{c['half_hours']:,} half hours over {c['days']:,} days.", ""]
    if f.get("season_peak"):
        top, low = f["season_peak"][0], f["season_peak"][-1]
        lines.append(f"- **Season:** average daily peak demand is highest in {top['season']} "
                     f"({top['avg_daily_peak_mw']:,.0f} MW) and lowest in {low['season']} ({low['avg_daily_peak_mw']:,.0f} MW).")
    if "weekend_drop_pct" in f:
        lines.append(f"- **Working days:** weekends and bank holidays use {f['weekend_drop_pct']}% less electricity than working days.")
    if "demand_change" in f:
        d = f["demand_change"]
        lines.append(f"- **Trend:** average National Demand changed by {d['change_pct']}% from {d['from_year']} "
                     f"({d['avg_nd_from']:,} MW) to {d['to_year']} ({d['avg_nd_to']:,} MW).")
    jm = {r["local_time_label"]: r for r in f.get("june_midday", [])}
    if "13:00" in jm:
        r = jm["13:00"]
        lines.append(f"- **Solar dip:** at 13:00 in June, local solar averages {r['solar_mw']:,.0f} MW, so National Demand "
                     f"({r['national_demand_mw']:,.0f} MW) sits well below underlying demand ({r['underlying_demand_mw']:,.0f} MW).")
    bands = {r["wind_solar_band"]: r for r in f.get("intensity_by_wind_solar_band", [])}
    if "<20%" in bands and "50%+" in bands:
        lines.append(f"- **Renewables:** when wind and solar supply under 20% of generation, carbon intensity averages "
                     f"{bands['<20%']['avg_intensity']:.0f} g/kWh; at 50% or more it averages {bands['50%+']['avg_intensity']:.0f} g/kWh.")
    if f.get("best_hours_by_season"):
        parts = [f"{s}: cleanest around {v['cleanest_hour']:02d}:00, dirtiest around {v['dirtiest_hour']:02d}:00"
                 for s, v in f["best_hours_by_season"].items()]
        lines.append("- **Best time to use electricity:** " + "; ".join(parts) + ".")
    if f.get("regions"):
        lo, hi = f["regions"][0], f["regions"][-1]
        lines.append(f"- **Regions ({f['regional_period'][0]} to {f['regional_period'][1]}):** {lo['region_name']} has the cleanest "
                     f"electricity ({lo['avg_intensity']:.0f} g/kWh forecast) and {hi['region_name']} the most carbon-intensive "
                     f"({hi['avg_intensity']:.0f} g/kWh).")
    lines.append(f"- **Weather:** on working days, daily demand and temperature have a correlation of "
                 f"{f['corr_daily_demand_temperature']} (colder days use more electricity).")
    dq = f["data_quality"]
    lines += ["", "## Data quality", "",
              f"- {dq['repeated_rows_removed']:,} repeated demand rows removed; {dq['unparsed_dates']:,} dates could not be parsed; "
              f"{dq['forecast_rows_excluded']:,} forecast rows excluded.",
              f"- Date formats seen in the NESO files: " + ", ".join(f"{r['format']} ({r['rows']:,} rows)" for r in dq["date_formats"]) + ".",
              f"- {len(f['clock_change_days'])} clock-change days found and handled (46 or 50 settlement periods).",
              f"- Half hours without carbon intensity: {dq['half_hours_missing_intensity']:,}; without temperature: "
              f"{dq['half_hours_missing_temperature']:,}.",
              f"- Interconnector sign check: correlation between NESO net flow and the API imports share is "
              f"{f['corr_interconnector_imports']}."]
    return "\n".join(lines) + "\n"


def main() -> None:
    con = duckdb.connect(str(config.WAREHOUSE), read_only=True)
    findings = compute(con)
    con.close()
    config.REPORTS_DIR.mkdir(exist_ok=True)
    (config.REPORTS_DIR / "findings.json").write_text(json.dumps(findings, indent=2, default=str))
    (config.REPORTS_DIR / "findings.md").write_text(to_markdown(findings))
    print(to_markdown(findings))


if __name__ == "__main__":
    main()
