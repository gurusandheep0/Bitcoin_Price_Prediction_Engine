# Data contract

## Source

- Provider: Coinbase Exchange public market-data API
- Product: `BTC-USD`
- Endpoint: `GET /products/BTC-USD/candles`
- Granularity: `86400` seconds
- Authentication: not required for this public market-data endpoint
- Time standard: UTC

The downloader uses windows of 280 days, below the documented 300-candle response maximum, and records the request and observed ranges in `artifacts/data_provenance.json`.

## Canonical candle schema

| Column | Type | Constraint |
|---|---|---|
| `date` | UTC datetime | unique after deduplication, ascending |
| `open` | float | greater than zero |
| `high` | float | not below open, low, or close |
| `low` | float | not above open, high, or close |
| `close` | float | greater than zero |
| `volume` | float | zero or greater, BTC units |

## Forecast sample

At date `t`, every feature is computed from a candle at `t` or earlier. The label is the close at `t+1`, represented during training as:

```text
target_log_return[t] = log(close[t+1] / close[t])
```

The predicted return is converted to a price using `close[t] * exp(predicted_return[t])`. `target_close`, `target_date`, and `target_log_return` are never included in the feature columns.

## Reproducibility

The committed snapshot is suitable for offline reproduction. Refreshing data creates a new time-dependent experiment and therefore can legitimately produce different feature rows, metrics, model selection, and forecast values.
