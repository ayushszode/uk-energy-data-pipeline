"""Forecast tomorrow's peak National Demand from the daily mart table.

    python -m energy_pipeline.forecast

Set-up (decided before looking at test results):
  * target: peak half-hourly National Demand (MW) for day t
  * features known by the evening of day t-1: yesterday's peak, the peak a week
    ago, the 7-day average, weekday, bank holiday, time of year, long-term trend,
    and temperature for day t
  * split by time: train < 2025-07-01, validation 2025-07-01 to 2025-12-31,
    test from 2026-01-01 (never used for choosing)
  * the model with the lowest validation MAE is chosen, refitted on
    train + validation, and scored once on the test period

Caveat: day t's temperature is the observed value, standing in for a weather
forecast. A real day-ahead system would use forecast temperatures, which are
less accurate, so the weather models' test error is a best case. The
"gbm_no_weather" model shows how much the weather features add.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from . import config

VALID_START = pd.Timestamp("2025-07-01")
TEST_START = pd.Timestamp("2026-01-01")
TARGET = "peak_demand_mw"
WEATHER = ["avg_temperature_c", "min_temperature_c", "heating_degree_days"]


def build_features(daily: pd.DataFrame) -> pd.DataFrame:
    """Calendar-aligned lags so a missing day never shifts the features."""
    df = daily.copy()
    df["date"] = pd.to_datetime(df["settlement_date"])
    df = df.set_index("date").sort_index()
    full = df.reindex(pd.date_range(df.index.min(), df.index.max(), freq="D"))
    y = full[TARGET]
    out = pd.DataFrame(index=full.index)
    out[TARGET] = y
    out["lag_1"] = y.shift(1)
    out["lag_7"] = y.shift(7)
    out["mean_7"] = y.shift(1).rolling(7, min_periods=7).mean()
    out["lag_1_minus_lag_8"] = y.shift(1) - y.shift(8)  # recent week-on-week change
    dow = out.index.dayofweek
    for d in range(7):
        out[f"dow_{d}"] = (dow == d).astype(int)
    doy = out.index.dayofyear
    out["doy_sin"] = np.sin(2 * np.pi * doy / 365.25)
    out["doy_cos"] = np.cos(2 * np.pi * doy / 365.25)
    out["trend_years"] = (out.index - out.index.min()).days / 365.25
    out["bank_holiday"] = full["is_bank_holiday_ew"].astype("float")
    out["clock_change"] = full["is_clock_change_day"].astype("float")
    out["is_complete_day"] = full["is_complete_day"]
    for col in WEATHER:
        out[col] = full[col]
    out = out[out["is_complete_day"] == True].drop(columns="is_complete_day")  # noqa: E712
    return out.dropna()


def feature_sets(columns: list[str]) -> dict[str, list[str]]:
    base = [c for c in columns if c != TARGET and c not in WEATHER]
    return {"ridge": base + WEATHER, "gbm": base + WEATHER, "gbm_no_weather": base}


def make_model(name: str):
    if name == "ridge":
        return make_pipeline(StandardScaler(), Ridge(alpha=1.0))
    return HistGradientBoostingRegressor(max_iter=400, learning_rate=0.05, max_leaf_nodes=15,
                                         min_samples_leaf=20, l2_regularization=1.0, random_state=42)


def metrics(y_true: pd.Series, y_pred: np.ndarray) -> dict:
    err = np.asarray(y_true) - np.asarray(y_pred)
    return {"mae_mw": float(np.mean(np.abs(err))),
            "mape_pct": float(np.mean(np.abs(err) / np.asarray(y_true)) * 100),
            "rmse_mw": float(np.sqrt(np.mean(err ** 2))),
            "bias_mw": float(np.mean(-err))}


def paired_bootstrap(abs_a: np.ndarray, abs_b: np.ndarray, n: int = 2000, seed: int = 42) -> tuple[float, float]:
    """95% interval for MAE(a) - MAE(b) by resampling test days."""
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(abs_a), size=(n, len(abs_a)))
    diffs = abs_a[idx].mean(axis=1) - abs_b[idx].mean(axis=1)
    return float(np.percentile(diffs, 2.5)), float(np.percentile(diffs, 97.5))


def run(feats: pd.DataFrame) -> dict:
    train = feats[feats.index < VALID_START]
    valid = feats[(feats.index >= VALID_START) & (feats.index < TEST_START)]
    test = feats[feats.index >= TEST_START]
    sets = feature_sets(list(feats.columns))
    rows, valid_mae = [], {}

    def record(name, split, y, pred):
        m = metrics(y, pred)
        rows.append({"model": name, "split": split, "days": len(y), **{k: round(v, 2) for k, v in m.items()}})
        return m

    # Simple baselines need no fitting.
    for name, col in [("naive_yesterday", "lag_1"), ("naive_last_week", "lag_7")]:
        valid_mae[name] = record(name, "validation", valid[TARGET], valid[col])["mae_mw"]
        record(name, "test", test[TARGET], test[col])

    test_preds = {"naive_yesterday": test["lag_1"].to_numpy(), "naive_last_week": test["lag_7"].to_numpy()}
    for name, cols in sets.items():
        model = make_model(name).fit(train[cols], train[TARGET])
        valid_mae[name] = record(name, "validation", valid[TARGET], model.predict(valid[cols]))["mae_mw"]
        refit = make_model(name).fit(pd.concat([train, valid])[cols], pd.concat([train, valid])[TARGET])
        test_preds[name] = refit.predict(test[cols])
        record(name, "test", test[TARGET], test_preds[name])

    chosen = min(valid_mae, key=valid_mae.get)
    y = test[TARGET].to_numpy()
    abs_best = np.abs(y - test_preds[chosen])
    abs_naive = np.abs(y - test_preds["naive_last_week"])
    lo, hi = paired_bootstrap(abs_naive, abs_best)

    preds = pd.DataFrame({"date": test.index.date, "actual_peak_mw": y})
    for name, p in test_preds.items():
        preds[name] = np.round(p, 0)

    summary = {
        "target": TARGET, "train_days": len(train), "validation_days": len(valid), "test_days": len(test),
        "train_period": [str(train.index.min().date()), str(train.index.max().date())],
        "validation_period": [str(valid.index.min().date()), str(valid.index.max().date())],
        "test_period": [str(test.index.min().date()), str(test.index.max().date())],
        "selection_rule": "lowest validation MAE", "chosen_model": chosen,
        "chosen_test": next(r for r in rows if r["model"] == chosen and r["split"] == "test"),
        "naive_last_week_test": next(r for r in rows if r["model"] == "naive_last_week" and r["split"] == "test"),
        "mae_improvement_vs_last_week_mw": round(float(abs_naive.mean() - abs_best.mean()), 1),
        "mae_improvement_95ci_mw": [round(lo, 1), round(hi, 1)],
    }
    return {"metrics": rows, "predictions": preds, "summary": summary}


def main() -> None:
    import duckdb  # imported here so the modelling code can be tested without a warehouse

    con = duckdb.connect(str(config.WAREHOUSE), read_only=True)
    daily = con.execute("select * from marts.fct_daily_electricity order by settlement_date").df()
    con.close()
    result = run(build_features(daily))
    config.REPORTS_DIR.mkdir(exist_ok=True)
    pd.DataFrame(result["metrics"]).to_csv(config.REPORTS_DIR / "forecast_metrics.csv", index=False)
    result["predictions"].to_csv(config.REPORTS_DIR / "forecast_test_predictions.csv", index=False)
    (config.REPORTS_DIR / "forecast_summary.json").write_text(json.dumps(result["summary"], indent=2))
    print(pd.DataFrame(result["metrics"]).to_string(index=False))
    print(json.dumps(result["summary"], indent=2))


if __name__ == "__main__":
    main()
