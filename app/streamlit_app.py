"""UK Electricity Dashboard - built from the dbt mart tables exported to app_data/."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

DATA = Path(__file__).resolve().parents[1] / "app_data"
TEAL, AMBER, SLATE, RED = "#0F766E", "#D97706", "#334155", "#B91C1C"
SEASONS = ["Winter", "Spring", "Summer", "Autumn"]
PAGES = ["Overview", "Daily patterns", "Carbon & renewables", "Best time to use power",
         "Regions", "Forecast", "Data quality", "About"]

st.set_page_config(page_title="UK Electricity Dashboard", page_icon="⚡", layout="wide")


@st.cache_data
def csv(name: str, parse: tuple[str, ...] = ()) -> pd.DataFrame:
    path = DATA / f"{name}.csv.gz"
    if not path.exists():
        path = DATA / f"{name}.csv"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path)
    for col in parse:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col])
    return df


@st.cache_data
def js(name: str) -> dict:
    path = DATA / name
    return json.loads(path.read_text()) if path.exists() else {}


def kpi(col, label: str, value: str, note: str = "") -> None:
    col.metric(label, value, help=note or None)


def chart(fig: go.Figure, height: int = 380) -> None:
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=40, b=10), legend_title_text="",
                      plot_bgcolor="white", paper_bgcolor="white")
    st.plotly_chart(fig, use_container_width=True)


daily = csv("daily", ("settlement_date",))
findings = js("findings.json")

st.sidebar.title("⚡ UK Electricity")
st.sidebar.caption("Demand, carbon and weather - a tested dbt pipeline on public data.")
page = st.sidebar.radio("Page", PAGES, key="page")
if not daily.empty:
    st.sidebar.caption(f"Data: {daily['settlement_date'].min():%d %b %Y} to {daily['settlement_date'].max():%d %b %Y}")

if daily.empty and page != "About":
    st.warning("No exported data found in app_data/. Run `make pipeline` first.")
    st.stop()

# ---------------------------------------------------------------------------
if page == "Overview":
    st.title("UK electricity at a glance")
    st.write("How much electricity Great Britain uses, how clean it is, and how both change with the "
             "season, the weather and the time of day.")
    complete = daily[daily["is_complete_day"]]
    last_year = int(complete["year"].max())
    ly = complete[complete["year"] == last_year]
    c1, c2, c3, c4 = st.columns(4)
    kpi(c1, f"Average daily peak ({last_year})", f"{ly['peak_demand_mw'].mean():,.0f} MW")
    kpi(c2, f"Average carbon intensity ({last_year})", f"{ly['avg_intensity'].mean():.0f} g/kWh",
        "Grams of CO2 per kWh of electricity generated.")
    kpi(c3, f"Wind + solar share ({last_year})", f"{ly['avg_wind_solar_pct'].mean():.1f}%")
    kpi(c4, "Days of data", f"{len(daily):,}")

    d = complete.set_index("settlement_date").sort_index()
    fig = go.Figure()
    fig.add_scatter(x=d.index, y=d["peak_demand_mw"], name="Daily peak", line=dict(color="#94A3B8", width=1))
    fig.add_scatter(x=d.index, y=d["peak_demand_mw"].rolling(28, center=True).mean(), name="28-day average",
                    line=dict(color=TEAL, width=3))
    fig.update_layout(title="Daily peak National Demand (MW)", yaxis_title="MW")
    chart(fig)

    fig = go.Figure()
    fig.add_scatter(x=d.index, y=d["avg_intensity"], name="Daily average", line=dict(color="#CBD5E1", width=1))
    fig.add_scatter(x=d.index, y=d["avg_intensity"].rolling(28, center=True).mean(), name="28-day average",
                    line=dict(color=AMBER, width=3))
    fig.update_layout(title="Carbon intensity (gCO2/kWh)", yaxis_title="g/kWh")
    chart(fig)
    if (DATA / "findings.md").exists():
        st.subheader("Key findings")
        text = (DATA / "findings.md").read_text().replace("# Findings", "", 1)
        st.markdown(text.split("## Data quality")[0])

# ---------------------------------------------------------------------------
elif page == "Daily patterns":
    st.title("How demand changes through the day")
    prof = csv("profile_by_time")
    season = st.segmented_control("Season", SEASONS, default="Summer") or "Summer"
    p = prof[prof["season"] == season]
    fig = go.Figure()
    fig.add_scatter(x=p["local_time_label"], y=p["underlying_demand_mw"], name="Underlying demand",
                    line=dict(color=SLATE, dash="dot", width=2))
    fig.add_scatter(x=p["local_time_label"], y=p["national_demand_mw"], name="National Demand (from the grid)",
                    line=dict(color=TEAL, width=3))
    fig.add_bar(x=p["local_time_label"], y=p["embedded_solar_mw"], name="Local solar", marker_color=AMBER, opacity=0.35)
    fig.update_layout(title=f"Average day in {season} (UK local time)", yaxis_title="MW", xaxis_title="")
    chart(fig, 420)
    st.caption("National Demand is what the transmission grid supplies. Solar panels on local networks meet "
               "part of the need directly, so on sunny days the grid sees a midday dip. Underlying demand adds "
               "NESO's estimates of local wind and solar back on.")

    hh = csv("half_hourly", ("settlement_date",))
    hh["month"] = hh["settlement_date"].dt.month
    heat = hh.pivot_table(index="month", columns="local_hour", values="national_demand_mw", aggfunc="mean")
    fig = px.imshow(heat, aspect="auto", color_continuous_scale="Teal",
                    labels=dict(x="Hour of day (local)", y="Month", color="MW"))
    fig.update_layout(title="Average National Demand by month and hour")
    chart(fig, 420)

    complete = daily[daily["is_complete_day"]].copy()
    complete["Day type"] = complete["day_name"].where(~complete["is_bank_holiday_ew"], "Bank holiday")
    order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday", "Bank holiday"]
    fig = px.box(complete, x="Day type", y="demand_gwh", category_orders={"Day type": order},
                 color_discrete_sequence=[TEAL])
    fig.update_layout(title="Daily electricity use by day type (GWh)", yaxis_title="GWh", xaxis_title="")
    chart(fig)

# ---------------------------------------------------------------------------
elif page == "Carbon & renewables":
    st.title("More wind and solar, cleaner electricity")
    hh = csv("half_hourly", ("settlement_date",))
    hh = hh.dropna(subset=["intensity_actual", "wind_solar_pct"])
    sample = hh.sample(min(len(hh), 6000), random_state=1)
    fig = px.scatter(sample, x="wind_solar_pct", y="intensity_actual", opacity=0.25, color_discrete_sequence=[TEAL],
                     labels={"wind_solar_pct": "Wind + solar share of generation (%)", "intensity_actual": "Carbon intensity (g/kWh)"})
    fig.update_layout(title="Each dot is one half hour (random sample of 6,000)")
    chart(fig, 420)
    if findings.get("intensity_by_wind_solar_band"):
        bands = pd.DataFrame(findings["intensity_by_wind_solar_band"])
        c1, c2 = st.columns([2, 3])
        c1.dataframe(bands.rename(columns={"wind_solar_band": "Wind + solar share", "half_hours": "Half hours",
                                           "avg_intensity": "Avg intensity (g/kWh)"}), hide_index=True)
        c2.metric("Correlation: zero-carbon share vs intensity", findings.get("corr_zero_carbon_intensity"))

    hh["month"] = hh["settlement_date"].dt.to_period("M").dt.to_timestamp()
    mix = hh.groupby("month")[["wind_pct", "solar_pct", "nuclear_pct", "gas_pct", "imports_pct"]].mean().reset_index()
    mix = mix.melt("month", var_name="fuel", value_name="share")
    mix["fuel"] = mix["fuel"].str.replace("_pct", "").str.title()
    fig = px.area(mix, x="month", y="share", color="fuel",
                  color_discrete_map={"Wind": TEAL, "Solar": AMBER, "Nuclear": "#6366F1", "Gas": "#64748B", "Imports": "#A3A3A3"})
    fig.update_layout(title="Monthly average generation share (%), main fuels", yaxis_title="% of generation", xaxis_title="")
    chart(fig, 420)

# ---------------------------------------------------------------------------
elif page == "Best time to use power":
    st.title("When is electricity cleanest?")
    st.write("Running a dishwasher or charging a car when carbon intensity is low cuts emissions without using less power.")
    prof = csv("profile_by_time")
    heat = prof.pivot_table(index="season", columns="local_time_label", values="avg_intensity").reindex(SEASONS)
    fig = px.imshow(heat, aspect="auto", color_continuous_scale="RdYlGn_r",
                    labels=dict(x="Time of day (local)", y="", color="g/kWh"))
    fig.update_layout(title="Average carbon intensity by season and time of day")
    chart(fig, 340)
    best = findings.get("best_hours_by_season", {})
    if best:
        cols = st.columns(len(best))
        for col, season in zip(cols, [s for s in SEASONS if s in best]):
            b = best[season]
            col.metric(season, f"Cleanest ~{b['cleanest_hour']:02d}:00",
                       f"{b['cleanest'] - b['dirtiest']:.0f} g/kWh vs ~{b['dirtiest_hour']:02d}:00", delta_color="inverse")

    hh = csv("half_hourly", ("settlement_date", "period_start_local"))
    day = st.date_input("Look at one day", value=hh["settlement_date"].max().date(),
                        min_value=hh["settlement_date"].min().date(), max_value=hh["settlement_date"].max().date())
    one = hh[hh["settlement_date"].dt.date == day]
    if not one.empty and one["intensity_actual"].notna().any():
        low = one.loc[one["intensity_actual"].idxmin()]
        fig = px.line(one, x="period_start_local", y="intensity_actual", color_discrete_sequence=[TEAL],
                      labels={"period_start_local": "", "intensity_actual": "g/kWh"})
        fig.add_scatter(x=[low["period_start_local"]], y=[low["intensity_actual"]], mode="markers",
                        marker=dict(size=12, color=AMBER), name=f"Cleanest: {low['local_time_label']}")
        fig.update_layout(title=f"Carbon intensity on {day:%A %d %B %Y}")
        chart(fig, 340)

# ---------------------------------------------------------------------------
elif page == "Regions":
    st.title("Cleanest and most carbon-intensive regions")
    reg = csv("regional_daily", ("local_date",))
    if reg.empty:
        st.info("No regional data exported yet.")
        st.stop()
    dno = reg[reg["region_type"] == "DNO area"]
    avg = dno.groupby("region_name", as_index=False)[["avg_intensity", "avg_zero_carbon_pct", "avg_wind_pct"]].mean()
    avg = avg.sort_values("avg_intensity")
    fig = px.bar(avg, x="avg_intensity", y="region_name", orientation="h", color="avg_intensity",
                 color_continuous_scale="RdYlGn_r", labels={"avg_intensity": "Average forecast intensity (g/kWh)", "region_name": ""})
    fig.update_layout(title=f"Average carbon intensity, {reg['local_date'].min():%b %Y} to {reg['local_date'].max():%b %Y}",
                      coloraxis_showscale=False)
    chart(fig, 480)
    pick = st.multiselect("Compare regions over time", sorted(dno["region_name"].unique()),
                          default=[avg.iloc[0]["region_name"], avg.iloc[-1]["region_name"]])
    if pick:
        sub = dno[dno["region_name"].isin(pick)].copy()
        sub["week"] = sub["local_date"].dt.to_period("W").dt.start_time
        weekly = sub.groupby(["week", "region_name"], as_index=False)["avg_intensity"].mean()
        fig = px.line(weekly, x="week", y="avg_intensity", color="region_name",
                      labels={"week": "", "avg_intensity": "Weekly average (g/kWh)", "region_name": ""})
        chart(fig)
    st.caption("Regional values are the Carbon Intensity API's regional forecasts (actual values are only published nationally).")

# ---------------------------------------------------------------------------
elif page == "Forecast":
    st.title("Forecasting tomorrow's peak demand")
    summary = js("forecast_summary.json")
    metrics = csv("forecast_metrics")
    preds = csv("forecast_test_predictions", ("date",))
    if not summary:
        st.info("Run the forecast step to see results.")
        st.stop()
    chosen = summary["chosen_model"]
    c1, c2, c3 = st.columns(3)
    c1.metric("Chosen model (lowest validation error)", chosen)
    c2.metric("Test error (MAE)", f"{summary['chosen_test']['mae_mw']:,.0f} MW",
              f"{summary['chosen_test']['mape_pct']:.1f}% average error", delta_color="off")
    c3.metric("Better than 'same day last week' by", f"{summary['mae_improvement_vs_last_week_mw']:,.0f} MW",
              f"95% CI {summary['mae_improvement_95ci_mw'][0]:,.0f} to {summary['mae_improvement_95ci_mw'][1]:,.0f} MW",
              delta_color="off")
    fig = go.Figure()
    fig.add_scatter(x=preds["date"], y=preds["actual_peak_mw"], name="Actual", line=dict(color=SLATE, width=2))
    fig.add_scatter(x=preds["date"], y=preds[chosen], name=f"Forecast ({chosen})", line=dict(color=TEAL, width=2))
    fig.add_scatter(x=preds["date"], y=preds["naive_last_week"], name="Same day last week",
                    line=dict(color="#CBD5E1", width=1, dash="dot"))
    fig.update_layout(title=f"Test period {summary['test_period'][0]} to {summary['test_period'][1]}", yaxis_title="MW")
    chart(fig, 420)
    st.dataframe(metrics.pivot_table(index="model", columns="split", values="mae_mw").round(0)
                 .rename(columns={"validation": "Validation MAE (MW)", "test": "Test MAE (MW)"}))
    st.caption("Models were trained before 1 July 2025, chosen on July-December 2025 and scored once on 2026. "
               "Temperature for the forecast day uses observed weather in place of a weather forecast, so the "
               "weather models' error is a best case; 'gbm_no_weather' shows the result without it.")

# ---------------------------------------------------------------------------
elif page == "Data quality":
    st.title("Data quality and pipeline health")
    q = js("dbt_test_summary.json")
    if q:
        by = q.get("by_status", {})
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("dbt tests run", q.get("tests", 0))
        c2.metric("Passed", by.get("pass", 0))
        c3.metric("Warnings", by.get("warn", 0))
        c4.metric("Failed", by.get("fail", 0) + by.get("error", 0))
        if q.get("warnings"):
            st.write("**Warnings (reviewed, not blocking):**")
            st.dataframe(pd.DataFrame(q["warnings"]), hide_index=True)
    dq = findings.get("data_quality", {})
    if dq:
        st.subheader("What the pipeline fixed")
        st.markdown(
            f"- **{dq['repeated_rows_removed']:,}** repeated demand rows removed\n"
            f"- **{dq['unparsed_dates']:,}** dates that could not be parsed\n"
            f"- **{dq['forecast_rows_excluded']:,}** forecast rows excluded (only actuals kept)\n"
            f"- Date formats found: " + ", ".join(f"{r['format']} ({r['rows']:,})" for r in dq["date_formats"]))
    st.subheader("Clock-change days")
    st.write("Settlement periods count from UK midnight, so the day the clocks go forward has 46 half hours "
             "and the day they go back has 50. A dbt test checks every day has the right number.")
    st.dataframe(csv("clock_change_days"), hide_index=True)
    lr = js("load_report.json")
    if lr:
        st.subheader("Rows loaded per source")
        st.dataframe(pd.DataFrame(lr["rows"].items(), columns=["Raw table", "Rows"]), hide_index=True)

# ---------------------------------------------------------------------------
else:
    st.title("About this project")
    st.markdown("""
**What it is:** an end-to-end data pipeline on public UK energy data, built to show data engineering and
analytics practice - automated extraction, a tested dbt model, documentation and a dashboard.

**Pipeline:** Python extracts four sources into monthly raw files → DuckDB → dbt staging, intermediate and
mart models (star schema) with tests → analysis, a next-day peak demand forecast and this dashboard.
GitHub Actions runs the tests on every change and refreshes the data every week.

**Sources and licences**
- [NESO Data Portal](https://www.neso.energy/data-portal) - Historic Demand Data (NESO Open Data Licence)
- [Carbon Intensity API](https://carbonintensity.org.uk) - national and regional intensity and mix (CC BY 4.0)
- [Open-Meteo](https://open-meteo.com) - historical weather (CC BY 4.0)
- [GOV.UK bank holidays](https://www.gov.uk/bank-holidays) (Open Government Licence v3.0)

**Code:** [github.com/ayushszode/uk-energy-data-pipeline](https://github.com/ayushszode/uk-energy-data-pipeline)
""")
