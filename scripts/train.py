#!/usr/bin/env python3
"""Train, compare, evaluate, and persist Bitcoin forecasting models."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import pandas as pd

from btc_forecast.modeling import train_and_evaluate


def write_json(path: Path, payload: dict | list) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=Path("data/btc_usd_daily.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts"))
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    ohlcv = pd.read_csv(args.data)
    bundle, metrics, backtest, importance = train_and_evaluate(ohlcv, seed=args.seed)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, args.output_dir / "forecast_bundle.joblib", compress=3)
    write_json(args.output_dir / "metrics.json", metrics)
    write_json(
        args.output_dir / "model_card.json",
        {
            "model": bundle.model_name,
            "intended_use": "Educational next-day BTC-USD forecasting and time-series evaluation",
            "not_intended_for": ["autonomous trading", "investment advice", "guaranteed returns"],
            "target": metrics["target"],
            "validation": metrics["validation"],
            "trained_through": bundle.trained_through,
            "limitations": [
                "Historical relationships may not persist",
                "Daily OHLCV omits order-book, macroeconomic, and on-chain information",
                "The uncertainty interval is empirical and not a guarantee",
                "Exchange data can contain gaps or revisions",
            ],
        },
    )
    backtest.to_csv(args.output_dir / "backtest_predictions.csv", index=False)
    importance.to_csv(args.output_dir / "feature_importance.csv", index=False)
    pd.DataFrame(metrics["leaderboard"]).to_csv(args.output_dir / "model_leaderboard.csv", index=False)
    print(
        json.dumps(
            {
                "status": metrics["status"],
                "data": metrics["data"],
                "selected_model": metrics["selected_model"],
                "deployment_status": metrics["deployment_status"],
                "latest_forecast": metrics["latest_forecast"],
                "artifacts": str(args.output_dir.resolve()),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
