import numpy as np
import pandas as pd

from energy_pipeline import forecast


def synthetic_daily(start="2023-01-01", end="2026-06-30", seed=0):
    rng = np.random.default_rng(seed)
    dates = pd.date_range(start, end, freq="D")
    doy = dates.dayofyear.to_numpy()
    temp = 10 - 7 * np.cos(2 * np.pi * (doy - 15) / 365.25) + rng.normal(0, 2, len(dates))
    weekend = dates.dayofweek >= 5
    peak = 38000 - 600 * temp - 4000 * weekend + rng.normal(0, 600, len(dates))
    return pd.DataFrame({
        "settlement_date": dates.date, "peak_demand_mw": peak, "avg_temperature_c": temp,
        "min_temperature_c": temp - 3, "heating_degree_days": np.maximum(15.5 - temp, 0),
        "is_bank_holiday_ew": False, "is_clock_change_day": False, "is_complete_day": True,
    })


def test_lags_are_calendar_aligned_when_a_day_is_missing():
    daily = synthetic_daily(end="2023-03-01")
    daily = daily[daily["settlement_date"] != pd.Timestamp("2023-02-10").date()]
    feats = forecast.build_features(daily)
    # 11 Feb's "yesterday" is missing, so that row must be dropped, not shifted.
    assert pd.Timestamp("2023-02-11") not in feats.index
    row = feats.loc[pd.Timestamp("2023-02-20")]
    expected = daily.set_index(pd.to_datetime(daily["settlement_date"])).loc["2023-02-13", "peak_demand_mw"]
    assert row["lag_7"] == expected


def test_run_reports_every_model_and_beats_naive_on_easy_data():
    result = forecast.run(forecast.build_features(synthetic_daily()))
    models = {r["model"] for r in result["metrics"]}
    assert {"naive_yesterday", "naive_last_week", "ridge", "gbm", "gbm_no_weather"} <= models
    s = result["summary"]
    assert s["chosen_model"] in models
    assert s["test_period"][0] == "2026-01-01"
    assert s["chosen_test"]["mae_mw"] < s["naive_last_week_test"]["mae_mw"]
