import numpy as np

from btc_forecast.features import FEATURE_COLUMNS, build_features


def test_feature_matrix_is_finite_and_complete(market_frame):
    featured = build_features(market_frame)
    assert len(featured) > 400
    assert set(FEATURE_COLUMNS).issubset(featured.columns)
    assert np.isfinite(featured[FEATURE_COLUMNS].to_numpy()).all()


def test_target_is_exactly_next_daily_close(market_frame):
    featured = build_features(market_frame)
    first = featured.iloc[0]
    source_index = market_frame.index[market_frame["date"] == first["date"]][0]
    assert first["target_close"] == market_frame.iloc[source_index + 1]["close"]
    assert first["target_date"] == market_frame.iloc[source_index + 1]["date"]


def test_last_feature_row_is_available_for_live_forecast(market_frame):
    featured = build_features(market_frame)
    assert featured.iloc[-1]["date"] == market_frame.iloc[-1]["date"]
    assert np.isnan(featured.iloc[-1]["target_close"])


def test_past_feature_values_do_not_change_when_future_is_modified(market_frame):
    original = build_features(market_frame)
    changed = market_frame.copy()
    changed.loc[changed.index[-20:], "close"] *= 1.5
    changed.loc[changed.index[-20:], "high"] = changed.loc[changed.index[-20:], ["open", "close", "high"]].max(axis=1) * 1.01
    rebuilt = build_features(changed)
    cutoff = original.iloc[-30]["date"]
    left = original[original["date"] <= cutoff][FEATURE_COLUMNS].reset_index(drop=True)
    right = rebuilt[rebuilt["date"] <= cutoff][FEATURE_COLUMNS].reset_index(drop=True)
    assert np.allclose(left, right)
