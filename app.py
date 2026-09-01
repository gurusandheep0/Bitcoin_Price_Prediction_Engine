"""FastAPI serving layer for the Bitcoin Forecast Lab."""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


ROOT = Path(__file__).resolve().parent
ARTIFACTS = ROOT / "artifacts"


def load_runtime() -> None:
    paths = {
        "bundle": ARTIFACTS / "forecast_bundle.joblib",
        "metrics": ARTIFACTS / "metrics.json",
        "history": ROOT / "data" / "btc_usd_daily.csv",
        "backtest": ARTIFACTS / "backtest_predictions.csv",
        "importance": ARTIFACTS / "feature_importance.csv",
    }
    app.state.ready = all(path.exists() for path in paths.values())
    if not app.state.ready:
        return
    app.state.bundle = joblib.load(paths["bundle"])
    app.state.metrics = json.loads(paths["metrics"].read_text(encoding="utf-8"))
    app.state.history = pd.read_csv(paths["history"], parse_dates=["date"])
    app.state.backtest = pd.read_csv(paths["backtest"], parse_dates=["date", "target_date"])
    app.state.importance = pd.read_csv(paths["importance"])


@asynccontextmanager
async def lifespan(_: FastAPI):
    load_runtime()
    yield


app = FastAPI(
    title="Bitcoin Price Prediction Engine",
    version="1.0.0",
    description="Leakage-aware BTC-USD forecasting, backtesting, and model evidence APIs",
    lifespan=lifespan,
)
app.mount("/static", StaticFiles(directory=ROOT / "web"), name="static")


def require_ready() -> None:
    if not getattr(app.state, "ready", False):
        raise HTTPException(status_code=503, detail="Artifacts unavailable; run ./scripts/reproduce.sh")


def records(frame: pd.DataFrame) -> list[dict]:
    clean = frame.copy()
    for column in clean.select_dtypes(include=["datetime", "datetimetz"]).columns:
        clean[column] = clean[column].dt.strftime("%Y-%m-%d")
    return clean.replace({np.nan: None}).to_dict(orient="records")


@app.get("/", include_in_schema=False)
async def dashboard() -> FileResponse:
    return FileResponse(ROOT / "web" / "index.html")


@app.get("/api/health")
async def health() -> dict:
    ready = bool(getattr(app.state, "ready", False))
    return {"status": "ready" if ready else "setup_required", "model_loaded": ready, "version": app.version}


@app.get("/api/summary")
async def summary() -> dict:
    require_ready()
    history = app.state.history
    recent = history.tail(31)
    last_close = float(recent.iloc[-1]["close"])
    first_close = float(recent.iloc[0]["close"])
    returns = recent["close"].pct_change().dropna()
    running_max = recent["close"].cummax()
    drawdown = recent["close"] / running_max - 1
    return {
        **app.state.metrics,
        "market_30d": {
            "return_percent": round((last_close / first_close - 1) * 100, 2),
            "realized_volatility_percent": round(float(returns.std() * np.sqrt(365) * 100), 2),
            "max_drawdown_percent": round(float(drawdown.min() * 100), 2),
            "average_volume_btc": round(float(recent["volume"].mean()), 2),
        },
    }


@app.get("/api/history")
async def history(days: int = Query(365, ge=30, le=2500)) -> dict:
    require_ready()
    frame = app.state.history.tail(days)
    return {"count": len(frame), "candles": records(frame)}


@app.get("/api/backtest")
async def backtest(days: int = Query(180, ge=30, le=1000)) -> dict:
    require_ready()
    frame = app.state.backtest.tail(days)
    return {"count": len(frame), "rows": records(frame)}


@app.get("/api/forecast")
async def forecast() -> dict:
    require_ready()
    return {
        **app.state.metrics["latest_forecast"],
        "model": app.state.metrics["selected_model"],
        "deployment_status": app.state.metrics["deployment_status"],
        "risk_notice": app.state.metrics["risk_notice"],
    }


@app.get("/api/models")
async def models() -> dict:
    require_ready()
    return {"selected_model": app.state.metrics["selected_model"], "models": app.state.metrics["leaderboard"]}


@app.get("/api/features")
async def features(limit: int = Query(12, ge=3, le=30)) -> dict:
    require_ready()
    frame = app.state.importance.head(limit)
    return {"features": records(frame)}
