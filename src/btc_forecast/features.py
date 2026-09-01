"""Leakage-safe technical feature engineering for next-day forecasting."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .data_source import validate_ohlcv


FEATURE_COLUMNS = [
    "log_close",
    "log_return_1d",
    "return_lag_1",
    "return_lag_2",
    "return_lag_3",
    "return_lag_7",
    "sma_7_ratio",
    "sma_14_ratio",
    "sma_30_ratio",
    "ema_12_ratio",
    "ema_26_ratio",
    "macd_ratio",
    "volatility_7d",
    "volatility_14d",
    "volatility_30d",
    "rsi_14",
    "intraday_return",
    "high_low_range",
    "volume_change_1d",
    "volume_zscore_30d",
    "day_sin",
    "day_cos",
]


def _rsi(close: pd.Series, window: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(window).mean()
    loss = (-delta.clip(upper=0)).rolling(window).mean()
    relative_strength = gain / loss.replace(0, np.nan)
    return (100 - 100 / (1 + relative_strength)).fillna(50) / 100


def build_features(ohlcv: pd.DataFrame) -> pd.DataFrame:
    """Create features available at each daily close and a one-day-ahead target."""
    frame = validate_ohlcv(ohlcv).copy()
    close = frame["close"]
    log_return = np.log(close / close.shift(1))
    frame["log_close"] = np.log(close)
    frame["log_return_1d"] = log_return
    for lag in [1, 2, 3, 7]:
        frame[f"return_lag_{lag}"] = log_return.shift(lag)
    for window in [7, 14, 30]:
        frame[f"sma_{window}_ratio"] = close / close.rolling(window).mean() - 1
        frame[f"volatility_{window}d"] = log_return.rolling(window).std()
    ema_12 = close.ewm(span=12, adjust=False).mean()
    ema_26 = close.ewm(span=26, adjust=False).mean()
    frame["ema_12_ratio"] = close / ema_12 - 1
    frame["ema_26_ratio"] = close / ema_26 - 1
    frame["macd_ratio"] = (ema_12 - ema_26) / close
    frame["rsi_14"] = _rsi(close)
    frame["intraday_return"] = frame["close"] / frame["open"] - 1
    frame["high_low_range"] = (frame["high"] - frame["low"]) / frame["open"]
    frame["volume_change_1d"] = frame["volume"].pct_change().clip(-5, 5)
    volume_mean = frame["volume"].rolling(30).mean()
    volume_std = frame["volume"].rolling(30).std().replace(0, np.nan)
    frame["volume_zscore_30d"] = (frame["volume"] - volume_mean) / volume_std
    day = frame["date"].dt.dayofweek
    frame["day_sin"] = np.sin(2 * np.pi * day / 7)
    frame["day_cos"] = np.cos(2 * np.pi * day / 7)
    frame["target_date"] = frame["date"].shift(-1)
    frame["target_close"] = close.shift(-1)
    frame["target_log_return"] = np.log(frame["target_close"] / close)
    frame.replace([np.inf, -np.inf], np.nan, inplace=True)
    return frame.dropna(subset=FEATURE_COLUMNS).reset_index(drop=True)
