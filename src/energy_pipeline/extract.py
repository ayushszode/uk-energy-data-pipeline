"""Extract: download raw data from four public sources into monthly CSV files.

    python -m energy_pipeline.extract                 # fill any missing months
    python -m energy_pipeline.extract --refresh-recent 2   # also re-download the last 2 months
    python -m energy_pipeline.extract --sources carbon,weather

Raw values are written exactly as received (as text), one file per source and
month: data/raw/<source>/YYYY-MM.csv.gz. Cleaning happens later, in dbt, so
the raw layer always shows what the source really sent.
"""
from __future__ import annotations

import argparse
import io
import json
import re
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from . import config
from .http import HttpError, get
from .periods import Month, current_month, iso_minute, last_complete_month, month_range, windows

SOURCES = ["demand", "carbon_national", "generation_mix", "carbon_regional", "weather", "bank_holidays"]
MONTHS_ABBR = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]


# ---------------------------------------------------------------------------
# Writing helpers
# ---------------------------------------------------------------------------
def write_month(df: pd.DataFrame, source: str, month: Month) -> Path | None:
    if df is None or df.empty:
        print(f"[extract] {source} {month.label}: no rows returned - nothing written")
        return None
    folder = config.RAW_DIR / source
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{month.label}.csv.gz"
    # mtime=0 keeps the gzip bytes identical when the data has not changed,
    # so unchanged months do not show up as git changes after a refresh.
    df.to_csv(path, index=False, compression={"method": "gzip", "mtime": 0})
    return path


def month_exists(source: str, month: Month) -> bool:
    return (config.RAW_DIR / source / f"{month.label}.csv.gz").exists()


# ---------------------------------------------------------------------------
# NESO historic demand (one CSV per year on the NESO Data Portal)
# ---------------------------------------------------------------------------
def pick_year_resources(package: dict, years: set[int]) -> dict[int, str]:
    """Find the download URL of each yearly demand CSV in a CKAN package_show reply."""
    found: dict[int, str] = {}
    for res in package.get("result", {}).get("resources", []):
        url = res.get("url") or ""
        name = f"{res.get('name', '')} {url.rsplit('/', 1)[-1]}"
        if (res.get("format") or "").upper() not in ("CSV", "") and not url.lower().endswith(".csv"):
            continue
        m = re.search(r"demanddata[_-]?(20\d{2})", name, flags=re.I) or re.search(r"\b(20\d{2})\b", name)
        if m and int(m.group(1)) in years:
            found.setdefault(int(m.group(1)), url)
    return found


def parse_settlement_date(text: str) -> date | None:
    """NESO files have used several date formats over the years; accept them all."""
    s = str(text).strip()
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.match(r"^(\d{1,2})-([A-Za-z]{3})-(\d{4})$", s)
    if m and m.group(2).upper() in MONTHS_ABBR:
        return date(int(m.group(3)), MONTHS_ABBR.index(m.group(2).upper()) + 1, int(m.group(1)))
    m = re.match(r"^(\d{1,2})-([A-Za-z]{3})-(\d{2})$", s)  # 2023 file: 01-Jan-23
    if m and m.group(2).upper() in MONTHS_ABBR:
        return date(2000 + int(m.group(3)), MONTHS_ABBR.index(m.group(2).upper()) + 1, int(m.group(1)))
    m = re.match(r"^(\d{2})/(\d{2})/(\d{4})$", s)
    if m:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    return None


def split_neso_csv(text: str) -> tuple[dict[str, pd.DataFrame], list[str]]:
    """Split one yearly NESO CSV into months. Values stay as raw text."""
    df = pd.read_csv(io.StringIO(text), dtype=str, keep_default_na=False)
    df.columns = [c.strip().upper() for c in df.columns]
    seen = list(df.columns)
    for col in config.NESO_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    df = df[config.NESO_COLUMNS]
    parsed = df["SETTLEMENT_DATE"].map(parse_settlement_date)
    labels = parsed.map(lambda d: f"{d.year:04d}-{d.month:02d}" if d else "unparsed")
    return {label: part.reset_index(drop=True) for label, part in df.groupby(labels)}, seen


def extract_demand(months: list[Month], report: dict) -> None:
    years = {m.year for m in months}
    package = get(config.NESO_PACKAGE_URL).json()
    urls = pick_year_resources(package, years)
    report["demand"] = {"years_found": sorted(urls), "columns_seen": {}, "months": {}}
    wanted = {m.label for m in months}
    for year, url in sorted(urls.items()):
        text = get(url).text
        parts, seen = split_neso_csv(text)
        report["demand"]["columns_seen"][str(year)] = seen
        if "unparsed" in parts:
            bad = parts.pop("unparsed")
            report["demand"].setdefault("unparsed_rows", 0)
            report["demand"]["unparsed_rows"] += len(bad)
            report["demand"].setdefault("unparsed_examples", {})[str(year)] = bad["SETTLEMENT_DATE"].head(3).tolist()
        for label, part in parts.items():
            if label in wanted:
                write_month(part, "demand", Month.parse(label))
                report["demand"]["months"][label] = len(part)
    missing = sorted(wanted - set(report["demand"]["months"]))
    if missing:
        report["demand"]["missing_months"] = missing


# ---------------------------------------------------------------------------
# Carbon Intensity API (national intensity, national mix, regional)
# ---------------------------------------------------------------------------
def flatten_intensity(payload: dict) -> list[dict]:
    rows = []
    for item in payload.get("data", []):
        inten = item.get("intensity") or {}
        rows.append({
            "from": item.get("from"), "to": item.get("to"),
            "forecast": inten.get("forecast"), "actual": inten.get("actual"), "index": inten.get("index"),
        })
    return rows


def _mix_columns(mix: list[dict] | None) -> dict:
    out = {f"{f}_perc": None for f in config.FUELS}
    for entry in mix or []:
        fuel = str(entry.get("fuel", "")).lower()
        if fuel in config.FUELS:
            out[f"{fuel}_perc"] = entry.get("perc")
    return out


def flatten_generation(payload: dict) -> list[dict]:
    data = payload.get("data", [])
    if isinstance(data, dict):  # single-period replies use an object, not a list
        data = [data]
    return [{"from": d.get("from"), "to": d.get("to"), **_mix_columns(d.get("generationmix"))} for d in data]


def flatten_regional(payload: dict) -> list[dict]:
    data = payload.get("data", [])
    if isinstance(data, dict):
        data = data.get("data", [data])
    rows = []
    for period in data:
        for reg in period.get("regions", []):
            inten = reg.get("intensity") or {}
            rows.append({
                "from": period.get("from"), "to": period.get("to"),
                "regionid": reg.get("regionid"), "shortname": reg.get("shortname"), "dnoregion": reg.get("dnoregion"),
                "forecast": inten.get("forecast"), "index": inten.get("index"),
                **_mix_columns(reg.get("generationmix")),
            })
    return rows


def _year_segments(start: date, end: date) -> list[tuple[date, date]]:
    """Split [start, end) at 1 January. The /generation and /regional endpoints
    return incomplete data for requests that cross a year boundary."""
    out, s = [], start
    while s < end:
        e = min(date(s.year + 1, 1, 1), end)
        out.append((s, e))
        s = e
    return out


def _fetch_windowed(path: str, flatten, start: date, end: date) -> list[dict]:
    """Call a {from}/{to} endpoint in 14-day windows, halving the window if refused."""
    rows: list[dict] = []
    all_windows = [w for seg in _year_segments(start, end) for w in windows(*seg, config.CARBON_WINDOW_DAYS)]
    for s, e in all_windows:
        stack = [(s, e)]
        while stack:
            a, b = stack.pop()
            try:
                payload = get(f"{config.CARBON_API}{path}/{iso_minute(a)}/{iso_minute(b)}").json()
                rows.extend(flatten(payload))
            except HttpError as exc:
                if exc.status == 400 and (b - a).days > 1:
                    mid = a + timedelta(days=max(1, (b - a).days // 2))
                    stack.extend([(mid, b), (a, mid)])
                else:
                    raise
    return rows


def _keep_month(rows: list[dict], month: Month, keys: list[str]) -> pd.DataFrame:
    """Keep periods that start inside the month and drop exact repeats at window edges."""
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    start = pd.Timestamp(month.start, tz="UTC")
    end = pd.Timestamp(month.end, tz="UTC")
    ts = pd.to_datetime(df["from"], utc=True, errors="coerce")
    now = pd.Timestamp.now(tz="UTC")
    # Keep this month's periods only, and nothing in the future (those are forecasts).
    df = df[(ts >= start) & (ts < end) & (ts < now)]
    return df.drop_duplicates(subset=keys, keep="last").reset_index(drop=True)


def _missing_days(df: pd.DataFrame, month: Month) -> list[date]:
    """UTC days in the month (up to yesterday) with fewer than 48 half hours."""
    today = datetime.now(timezone.utc).date()
    last = min(month.end, today)
    days = [month.start + timedelta(days=i) for i in range((last - month.start).days)]
    if df.empty:
        return days
    have = pd.to_datetime(df["from"], utc=True).drop_duplicates().dt.date.value_counts()
    return [d for d in days if have.get(d, 0) < 48]


def _fetch_month(path: str, flatten, month: Month, keys: list[str]) -> tuple[pd.DataFrame, int]:
    """Fetch a month in windows, then re-ask day by day for any day that came back short."""
    # Ask for one extra day either side, then keep only this month's periods.
    # This avoids losing the first or last half hour at month edges.
    rows = _fetch_windowed(path, flatten, month.start - timedelta(days=1), month.end + timedelta(days=1))
    df = _keep_month(rows, month, keys)
    refetched = 0
    for d in _missing_days(df, month)[:31]:
        try:
            rows.extend(_fetch_windowed(path, flatten, d, d + timedelta(days=1)))
            refetched += 1
        except Exception as exc:  # a real outage at the source: keep what we have
            print(f"[extract] {path} {d}: day re-fetch failed ({exc})")
    if refetched:
        df = _keep_month(rows, month, keys)
    return df, refetched


def extract_carbon(months: list[Month], report: dict) -> None:
    jobs = [
        ("carbon_national", "/intensity", flatten_intensity, ["from"]),
        ("generation_mix", "/generation", flatten_generation, ["from"]),
    ]
    for source, path, flatten, keys in jobs:
        report[source] = {"months": {}, "days_refetched": {}}
        for m in months:
            df, refetched = _fetch_month(path, flatten, m, keys)
            write_month(df, source, m)
            report[source]["months"][m.label] = len(df)
            if refetched:
                report[source]["days_refetched"][m.label] = refetched


def extract_regional(months: list[Month], report: dict) -> None:
    first = Month.parse(config.REGIONAL_START_MONTH)
    report["carbon_regional"] = {"months": {}, "days_refetched": {}}
    for m in months:
        if m < first:
            continue
        df, refetched = _fetch_month("/regional/intensity", flatten_regional, m, ["from", "regionid"])
        write_month(df, "carbon_regional", m)
        report["carbon_regional"]["months"][m.label] = len(df)
        if refetched:
            report["carbon_regional"]["days_refetched"][m.label] = refetched


# ---------------------------------------------------------------------------
# Open-Meteo historical weather
# ---------------------------------------------------------------------------
def flatten_open_meteo(payload: dict, city: str) -> pd.DataFrame:
    hourly = payload.get("hourly", {})
    df = pd.DataFrame(hourly)
    if df.empty:
        return df
    df.insert(1, "city", city)
    return df


def extract_weather(months: list[Month], report: dict) -> None:
    if not months:
        return
    latest_available = datetime.now(timezone.utc).date() - timedelta(days=6)
    start = months[0].start
    end = min(months[-1].end - timedelta(days=1), latest_available)
    frames = []
    for name, lat, lon, _w in config.CITIES:
        payload = get(config.OPEN_METEO_ARCHIVE, params={
            "latitude": lat, "longitude": lon,
            "start_date": start.isoformat(), "end_date": end.isoformat(),
            "hourly": ",".join(config.WEATHER_HOURLY), "timezone": "GMT",
        }).json()
        frames.append(flatten_open_meteo(payload, name))
    df = pd.concat(frames, ignore_index=True)
    df = df.dropna(subset=["temperature_2m"])
    labels = df["time"].str.slice(0, 7)
    report["weather"] = {"months": {}, "end_date": end.isoformat()}
    wanted = {m.label for m in months}
    for label, part in df.groupby(labels):
        if label in wanted:
            write_month(part.reset_index(drop=True), "weather", Month.parse(label))
            report["weather"]["months"][label] = len(part)


# ---------------------------------------------------------------------------
# GOV.UK bank holidays
# ---------------------------------------------------------------------------
def flatten_bank_holidays(payload: dict) -> pd.DataFrame:
    rows = []
    for division, block in payload.items():
        for ev in block.get("events", []):
            rows.append({"division": division, "date": ev.get("date"), "title": ev.get("title"),
                         "notes": ev.get("notes", "")})
    return pd.DataFrame(rows)


def extract_bank_holidays(report: dict) -> None:
    df = flatten_bank_holidays(get(config.BANK_HOLIDAYS_URL).json())
    folder = config.RAW_DIR / "bank_holidays"
    folder.mkdir(parents=True, exist_ok=True)
    df.to_csv(folder / "bank_holidays.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})
    report["bank_holidays"] = {"rows": len(df), "first": df["date"].min(), "last": df["date"].max()}


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------
def months_to_fetch(source: str, all_months: list[Month], refresh_recent: int, force: bool) -> list[Month]:
    recent = {m.label for m in all_months[-refresh_recent:]} if refresh_recent else set()
    return [m for m in all_months if force or m.label in recent or not month_exists(source, m)]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sources", default="all", help="comma list of: " + ", ".join(SOURCES))
    ap.add_argument("--start", default=config.START_MONTH)
    ap.add_argument("--end", default=None, help="YYYY-MM, or 'current' for the month in progress")
    ap.add_argument("--refresh-recent", type=int, default=0, help="re-download the last N months")
    ap.add_argument("--force", action="store_true", help="re-download every month")
    args = ap.parse_args(argv)

    end = current_month() if args.end == "current" else (Month.parse(args.end) if args.end else last_complete_month())
    all_months = month_range(Month.parse(args.start), end)
    chosen = SOURCES if args.sources == "all" else [s.strip() for s in args.sources.split(",")]

    report: dict = {"run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "start": args.start, "end": end.label, "errors": {}}
    steps = {
        "demand": lambda ms: extract_demand(ms, report),
        "carbon_national": None,  # handled together with generation_mix
        "generation_mix": None,
        "carbon_regional": lambda ms: extract_regional(ms, report),
        "weather": lambda ms: extract_weather(ms, report),
    }
    for source in chosen:
        try:
            if source == "bank_holidays":
                extract_bank_holidays(report)
            elif source in ("carbon_national", "generation_mix"):
                if "carbon" in report.get("_done", []):
                    continue
                need = sorted({*months_to_fetch("carbon_national", all_months, args.refresh_recent, args.force),
                               *months_to_fetch("generation_mix", all_months, args.refresh_recent, args.force)},
                              key=lambda m: (m.year, m.month))
                extract_carbon(need, report)
                report.setdefault("_done", []).append("carbon")
            else:
                steps[source](months_to_fetch(source, all_months, args.refresh_recent, args.force))
        except Exception as exc:  # keep going, but record the failure
            report["errors"][source] = f"{type(exc).__name__}: {exc}"
            print(f"[extract] {source} failed: {exc}")
        else:
            print(f"[extract] {source} done")
    report.pop("_done", None)

    config.REPORTS_DIR.mkdir(exist_ok=True)
    (config.REPORTS_DIR / "extract_report.json").write_text(json.dumps(report, indent=2, default=str))
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
