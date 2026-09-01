#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="$PROJECT_DIR/.venv/bin/python"

if [[ ! -x "$PYTHON" ]]; then
  echo "Missing .venv. Run: ./scripts/setup.sh"
  exit 1
fi

echo "[1/3] Refreshing Coinbase BTC-USD daily candles..."
"$PYTHON" "$PROJECT_DIR/scripts/download_data.py" \
  --output "$PROJECT_DIR/data/btc_usd_daily.csv" \
  --metadata "$PROJECT_DIR/artifacts/data_provenance.json"
echo "[2/3] Training models and running chronological backtest..."
"$PYTHON" "$PROJECT_DIR/scripts/train.py" \
  --data "$PROJECT_DIR/data/btc_usd_daily.csv" \
  --output-dir "$PROJECT_DIR/artifacts"
echo "[3/3] Running data, model, and API tests..."
"$PYTHON" -m pytest "$PROJECT_DIR/tests" -q
echo "Reproduction complete. Forecasts are research output, not financial advice."
