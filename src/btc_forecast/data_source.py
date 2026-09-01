"""Coinbase Exchange daily-candle ingestion and OHLCV validation."""

from __future__ import annotations

import json
import time
from datetime import date, datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd


BASE_URL = "https://api.exchange.coinbase.com"
PRODUCT_ID = "BTC-USD"
GRANULARITY_SECONDS = 86_400
MAX_CANDLES = 300
OHLCV_COLUMNS = ["date", "open", "high", "low", "close", "volume"]


class MarketDataError(RuntimeError):
    """Raised when remote or local market data fails validation."""


def _as_utc(value: str | date | datetime) -> datetime:
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    elif isinstance(value, date) and not isinstance(value, datetime):
        value = datetime.combine(value, datetime.min.time())
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _request_json(url: str, timeout: int = 30, retries: int = 4) -> list:
    request = Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "btc-forecast-lab/1.0"},
    )
    for attempt in range(retries):
        try:
            with urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            if error.code != 429 and error.code < 500:
                raise MarketDataError(f"Coinbase returned HTTP {error.code}") from error
            if attempt == retries - 1:
                raise MarketDataError(f"Coinbase request failed after {retries} attempts") from error
        except (URLError, TimeoutError, json.JSONDecodeError) as error:
            if attempt == retries - 1:
                raise MarketDataError(f"Coinbase request failed: {error}") from error
        time.sleep(0.5 * (2**attempt))
    raise MarketDataError("Coinbase request failed")


def fetch_coinbase_daily(
    start: str | date | datetime,
    end: str | date | datetime,
    product_id: str = PRODUCT_ID,
) -> pd.DataFrame:
    """Fetch daily candles in API-safe windows and return ascending OHLCV data."""
    start_at, end_at = _as_utc(start), _as_utc(end)
    if end_at <= start_at:
        raise ValueError("end must be after start")

    rows: list[list[float]] = []
    cursor = start_at
    window = timedelta(days=MAX_CANDLES - 20)
    while cursor < end_at:
        window_end = min(cursor + window, end_at)
        query = urlencode(
            {
                "start": cursor.isoformat().replace("+00:00", "Z"),
                "end": window_end.isoformat().replace("+00:00", "Z"),
                "granularity": GRANULARITY_SECONDS,
            }
        )
        payload = _request_json(f"{BASE_URL}/products/{product_id}/candles?{query}")
        if not isinstance(payload, list):
            raise MarketDataError("Unexpected Coinbase candle response")
        rows.extend(payload)
        cursor = window_end
        time.sleep(0.12)

    if not rows:
        raise MarketDataError("Coinbase returned no candle data")
    frame = pd.DataFrame(rows, columns=["timestamp", "low", "high", "open", "close", "volume"])
    frame["date"] = pd.to_datetime(frame["timestamp"], unit="s", utc=True)
    frame = frame[(frame["date"] >= start_at) & (frame["date"] <= end_at)]
    return validate_ohlcv(frame[OHLCV_COLUMNS])


def validate_ohlcv(frame: pd.DataFrame) -> pd.DataFrame:
    missing = set(OHLCV_COLUMNS) - set(frame.columns)
    if missing:
        raise MarketDataError("Missing OHLCV columns: " + ", ".join(sorted(missing)))
    clean = frame[OHLCV_COLUMNS].copy()
    clean["date"] = pd.to_datetime(clean["date"], utc=True, errors="raise")
    for column in ["open", "high", "low", "close", "volume"]:
        clean[column] = pd.to_numeric(clean[column], errors="raise")
    clean = clean.drop_duplicates("date", keep="last").sort_values("date").reset_index(drop=True)
    if clean.empty:
        raise MarketDataError("OHLCV data is empty")
    if (clean[["open", "high", "low", "close"]] <= 0).any().any():
        raise MarketDataError("OHLC prices must be positive")
    if (clean["volume"] < 0).any():
        raise MarketDataError("Volume cannot be negative")
    if (clean["high"] < clean[["open", "close", "low"]].max(axis=1)).any():
        raise MarketDataError("High price is inconsistent with candle values")
    if (clean["low"] > clean[["open", "close", "high"]].min(axis=1)).any():
        raise MarketDataError("Low price is inconsistent with candle values")
    return clean
