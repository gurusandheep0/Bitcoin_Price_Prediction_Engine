#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="$PROJECT_DIR/.venv/bin/python"

if [[ ! -x "$PYTHON" ]]; then
  echo "Missing .venv. Run: ./scripts/setup.sh"
  exit 1
fi
if [[ ! -f "$PROJECT_DIR/artifacts/forecast_bundle.joblib" ]]; then
  echo "Missing model artifact. Run: ./scripts/reproduce.sh"
  exit 1
fi

PORT="${1:-$($PYTHON "$PROJECT_DIR/scripts/find_free_port.py" 8560)}"
echo "Bitcoin Forecast Lab: http://127.0.0.1:$PORT"
cd "$PROJECT_DIR"
exec "$PYTHON" -m uvicorn app:app --host 127.0.0.1 --port "$PORT"
