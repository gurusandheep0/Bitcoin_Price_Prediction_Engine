import numpy as np

from btc_forecast.modeling import regression_metrics, train_and_evaluate


def test_regression_metrics_contract():
    metrics = regression_metrics(
        np.array([101.0, 98.0, 105.0]),
        np.array([100.0, 99.0, 104.0]),
        np.array([100.0, 100.0, 100.0]),
    )
    assert metrics["mae_usd"] == 1.0
    assert 0 <= metrics["directional_accuracy_percent"] <= 100


def test_training_returns_chronological_evidence(market_frame):
    bundle, metrics, backtest, importance = train_and_evaluate(market_frame, seed=9)
    assert bundle.model_name in {"elastic_net", "random_forest", "hist_gradient_boosting"}
    assert metrics["status"] == "passed"
    assert metrics["data"]["holdout_rows"] == len(backtest)
    assert len(metrics["leaderboard"]) == 4
    assert backtest["target_date"].is_monotonic_increasing
    assert metrics["latest_forecast"]["predicted_close_usd"] > 0
    assert np.isclose(importance["importance"].sum(), 1.0) or importance["importance"].sum() == 0
