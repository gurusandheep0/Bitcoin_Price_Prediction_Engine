import pandas as pd
import pytest

from btc_forecast.data_source import MarketDataError, validate_ohlcv


def test_valid_market_frame_is_sorted_and_deduplicated(market_frame):
    duplicate = pd.concat([market_frame.iloc[::-1], market_frame.iloc[[0]]], ignore_index=True)
    clean = validate_ohlcv(duplicate)
    assert len(clean) == len(market_frame)
    assert clean["date"].is_monotonic_increasing


def test_missing_ohlcv_column_is_rejected(market_frame):
    with pytest.raises(MarketDataError, match="Missing OHLCV"):
        validate_ohlcv(market_frame.drop(columns="volume"))


def test_negative_price_is_rejected(market_frame):
    market_frame.loc[2, "close"] = -1
    with pytest.raises(MarketDataError, match="positive"):
        validate_ohlcv(market_frame)


def test_inconsistent_high_is_rejected(market_frame):
    market_frame.loc[3, "high"] = market_frame.loc[3, "low"]
    with pytest.raises(MarketDataError, match="High price"):
        validate_ohlcv(market_frame)
