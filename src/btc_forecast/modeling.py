"""Chronological model comparison, backtesting, and next-day forecast creation."""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Callable

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.inspection import permutation_importance
from sklearn.linear_model import ElasticNet
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import RobustScaler

from .features import FEATURE_COLUMNS, build_features


MODEL_FACTORIES: dict[str, Callable[[int], object]] = {
    "elastic_net": lambda seed: Pipeline(
        [("scale", RobustScaler()), ("model", ElasticNet(alpha=0.00008, l1_ratio=0.25, max_iter=20_000))]
    ),
    "random_forest": lambda seed: RandomForestRegressor(
        n_estimators=220,
        max_depth=10,
        min_samples_leaf=4,
        max_features=0.75,
        random_state=seed,
        n_jobs=-1,
    ),
    "hist_gradient_boosting": lambda seed: HistGradientBoostingRegressor(
        learning_rate=0.045,
        max_iter=240,
        max_leaf_nodes=18,
        l2_regularization=1.0,
        random_state=seed,
    ),
}


@dataclass
class ForecastBundle:
    model: object
    model_name: str
    feature_columns: list[str]
    interval_radius: float
    trained_through: str
    data_source: str


def _prices(current_close: np.ndarray, predicted_returns: np.ndarray) -> np.ndarray:
    return current_close * np.exp(np.clip(predicted_returns, -0.35, 0.35))


def regression_metrics(actual: np.ndarray, predicted: np.ndarray, current: np.ndarray) -> dict:
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    current = np.asarray(current, dtype=float)
    actual_direction = np.sign(actual - current)
    predicted_direction = np.sign(predicted - current)
    return {
        "mae_usd": round(float(mean_absolute_error(actual, predicted)), 2),
        "rmse_usd": round(float(sqrt(mean_squared_error(actual, predicted))), 2),
        "mape_percent": round(float(np.mean(np.abs((actual - predicted) / actual)) * 100), 4),
        "r2": round(float(r2_score(actual, predicted)), 6),
        "directional_accuracy_percent": round(float(np.mean(actual_direction == predicted_direction) * 100), 2),
    }


def _cross_validated_mae(model: object, frame: pd.DataFrame, splits: int = 5) -> float:
    splitter = TimeSeriesSplit(n_splits=splits)
    errors: list[float] = []
    X = frame[FEATURE_COLUMNS]
    y = frame["target_log_return"]
    for train_index, valid_index in splitter.split(X):
        fold = clone(model)
        fold.fit(X.iloc[train_index], y.iloc[train_index])
        prediction = _prices(
            frame.iloc[valid_index]["close"].to_numpy(), fold.predict(X.iloc[valid_index])
        )
        errors.append(mean_absolute_error(frame.iloc[valid_index]["target_close"], prediction))
    return float(np.mean(errors))


def train_and_evaluate(
    ohlcv: pd.DataFrame,
    holdout_fraction: float = 0.20,
    seed: int = 42,
) -> tuple[ForecastBundle, dict, pd.DataFrame, pd.DataFrame]:
    """Train candidate models and return bundle, metrics, backtest, and feature importance."""
    featured = build_features(ohlcv)
    labelled = featured.dropna(subset=["target_close", "target_log_return"]).copy()
    if len(labelled) < 240:
        raise ValueError("At least 240 feature-complete daily candles are required")
    split_at = int(len(labelled) * (1 - holdout_fraction))
    split_at = min(max(split_at, 180), len(labelled) - 60)
    train, test = labelled.iloc[:split_at], labelled.iloc[split_at:]
    X_train, y_train = train[FEATURE_COLUMNS], train["target_log_return"]
    X_test, y_test = test[FEATURE_COLUMNS], test["target_log_return"]

    leaderboard: list[dict] = []
    fitted: dict[str, object] = {}
    predictions: dict[str, np.ndarray] = {}
    baseline_prediction = test["close"].to_numpy()
    baseline_metrics = regression_metrics(
        test["target_close"].to_numpy(), baseline_prediction, test["close"].to_numpy()
    )
    leaderboard.append(
        {"model": "persistence_baseline", "cv_mae_usd": None, **baseline_metrics, "is_baseline": True}
    )

    for name, factory in MODEL_FACTORIES.items():
        model = factory(seed)
        cv_mae = _cross_validated_mae(model, train)
        model.fit(X_train, y_train)
        predicted_price = _prices(test["close"].to_numpy(), model.predict(X_test))
        fitted[name] = model
        predictions[name] = predicted_price
        leaderboard.append(
            {
                "model": name,
                "cv_mae_usd": round(cv_mae, 2),
                **regression_metrics(
                    test["target_close"].to_numpy(), predicted_price, test["close"].to_numpy()
                ),
                "is_baseline": False,
            }
        )

    candidate_rows = [row for row in leaderboard if not row["is_baseline"]]
    selected_row = min(candidate_rows, key=lambda row: row["cv_mae_usd"])
    selected_name = str(selected_row["model"])
    selected_model = fitted[selected_name]
    selected_prediction = predictions[selected_name]
    residuals = test["target_close"].to_numpy() - selected_prediction
    interval_radius = float(np.quantile(np.abs(residuals), 0.90))
    interval_coverage = float(
        np.mean(
            (test["target_close"].to_numpy() >= selected_prediction - interval_radius)
            & (test["target_close"].to_numpy() <= selected_prediction + interval_radius)
        )
    )

    backtest = test[["date", "target_date", "close", "target_close"]].copy()
    backtest["predicted_close"] = selected_prediction
    backtest["baseline_close"] = baseline_prediction
    backtest["interval_low"] = np.maximum(0, selected_prediction - interval_radius)
    backtest["interval_high"] = selected_prediction + interval_radius
    backtest["absolute_error"] = np.abs(backtest["target_close"] - backtest["predicted_close"])

    importance_result = permutation_importance(
        selected_model,
        X_test,
        y_test,
        n_repeats=8,
        random_state=seed,
        scoring="neg_mean_absolute_error",
    )
    importance = pd.DataFrame(
        {"feature": FEATURE_COLUMNS, "importance": np.maximum(importance_result.importances_mean, 0)}
    ).sort_values("importance", ascending=False)
    total_importance = float(importance["importance"].sum())
    if total_importance > 0:
        importance["importance"] /= total_importance

    final_model = MODEL_FACTORIES[selected_name](seed)
    final_model.fit(labelled[FEATURE_COLUMNS], labelled["target_log_return"])
    live_row = featured.iloc[[-1]]
    forecast_return = float(final_model.predict(live_row[FEATURE_COLUMNS])[0])
    forecast_price = float(_prices(live_row["close"].to_numpy(), np.array([forecast_return]))[0])
    latest_date = pd.Timestamp(live_row.iloc[0]["date"])
    next_date = latest_date + pd.Timedelta(days=1)
    baseline_mae = float(baseline_metrics["mae_usd"])
    selected_mae = float(selected_row["mae_usd"])
    improvement = (baseline_mae - selected_mae) / baseline_mae * 100 if baseline_mae else 0.0
    deployment_status = "challenger_beats_baseline" if improvement > 0 else "research_only_baseline_leads"

    metrics = {
        "status": "passed",
        "evidence_type": "historical_backtest",
        "data": {
            "source": "Coinbase Exchange public BTC-USD daily candles",
            "start": pd.Timestamp(ohlcv["date"].min()).date().isoformat(),
            "end": pd.Timestamp(ohlcv["date"].max()).date().isoformat(),
            "candles": int(len(ohlcv)),
            "feature_complete_rows": int(len(labelled)),
            "holdout_rows": int(len(test)),
        },
        "target": "next daily close derived from predicted next-day log return",
        "validation": "expanding-window TimeSeriesSplit for selection; final chronological holdout for reporting",
        "selected_model": selected_name,
        "deployment_status": deployment_status,
        "baseline_improvement_percent": round(improvement, 3),
        "leaderboard": sorted(leaderboard, key=lambda row: row["mae_usd"]),
        "holdout": {
            "start": pd.Timestamp(test["target_date"].min()).date().isoformat(),
            "end": pd.Timestamp(test["target_date"].max()).date().isoformat(),
            "interval_nominal_percent": 90,
            "interval_empirical_coverage_percent": round(interval_coverage * 100, 2),
            "interval_radius_usd": round(interval_radius, 2),
        },
        "latest_forecast": {
            "as_of": latest_date.date().isoformat(),
            "forecast_for": next_date.date().isoformat(),
            "last_close_usd": round(float(live_row.iloc[0]["close"]), 2),
            "predicted_close_usd": round(forecast_price, 2),
            "predicted_change_percent": round((np.exp(forecast_return) - 1) * 100, 4),
            "interval_low_usd": round(max(0, forecast_price - interval_radius), 2),
            "interval_high_usd": round(forecast_price + interval_radius, 2),
        },
        "risk_notice": "Research demonstration only. Forecasts are uncertain and are not financial advice.",
    }
    bundle = ForecastBundle(
        model=final_model,
        model_name=selected_name,
        feature_columns=list(FEATURE_COLUMNS),
        interval_radius=interval_radius,
        trained_through=latest_date.date().isoformat(),
        data_source=metrics["data"]["source"],
    )
    return bundle, metrics, backtest, importance.reset_index(drop=True)
