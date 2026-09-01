from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def market_frame() -> pd.DataFrame:
    rng = np.random.default_rng(17)
    rows = 460
    returns = rng.normal(0.0008, 0.028, rows)
    close = 10_000 * np.exp(np.cumsum(returns))
    open_price = np.r_[close[0], close[:-1]] * (1 + rng.normal(0, 0.004, rows))
    high = np.maximum(open_price, close) * (1 + rng.uniform(0.002, 0.025, rows))
    low = np.minimum(open_price, close) * (1 - rng.uniform(0.002, 0.025, rows))
    return pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=rows, freq="D", tz="UTC"),
            "open": open_price,
            "high": high,
            "low": low,
            "close": close,
            "volume": rng.lognormal(8, 0.35, rows),
        }
    )
