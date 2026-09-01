# Architecture

## Runtime boundaries

The project separates ingestion, research, and serving so that a browser request never retrains a model or silently changes the evidence.

1. `data_source.py` requests bounded Coinbase candle windows, validates the response, and writes a dated CSV plus provenance JSON.
2. `features.py` creates deterministic transformations using the current and earlier candles only. The next-day target is kept separate from the feature list.
3. `modeling.py` splits labelled rows chronologically, performs expanding-window candidate selection, evaluates the selected candidate on the later holdout, calibrates an empirical residual band, and refits the selected estimator for the next saved forecast.
4. `train.py` persists JSON/CSV evidence and a local Joblib bundle.
5. `app.py` loads those immutable artifacts at startup and exposes read-only REST endpoints.
6. `web/` renders the artifacts with dependency-light HTML, CSS, JavaScript, and Canvas charts.

## Artifact flow

| Artifact | Producer | Consumer | Version-control policy |
|---|---|---|---|
| `data/btc_usd_daily.csv` | downloader | trainer, API | committed dated snapshot |
| `artifacts/data_provenance.json` | downloader | audit/documentation | committed |
| `artifacts/metrics.json` | trainer | API/dashboard | committed |
| `artifacts/backtest_predictions.csv` | trainer | API/dashboard | committed |
| `artifacts/feature_importance.csv` | trainer | API/dashboard | committed |
| `artifacts/model_leaderboard.csv` | trainer | audit | committed |
| `artifacts/model_card.json` | trainer | governance | committed |
| `artifacts/forecast_bundle.joblib` | trainer | API | regenerated locally; Git-ignored |

## Failure behavior

- Non-retryable Coinbase client errors raise `MarketDataError` immediately.
- Rate limits, server errors, and temporary network failures use bounded exponential retry.
- Invalid prices, volume, candle order, or columns stop the pipeline.
- Fewer than 240 feature-complete rows stop training.
- Missing runtime artifacts return HTTP 503 and instruct the operator to reproduce them.
- An ML candidate that loses to persistence remains visible but receives a research-only governance state.
