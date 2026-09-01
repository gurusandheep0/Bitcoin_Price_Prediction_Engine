#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-/bin/python3.11}"
PIP_CACHE_DIR="${PIP_CACHE_DIR:-/tmp/bitcoin-forecast-pip-cache}"
export PIP_CACHE_DIR

"$PYTHON_BIN" -m venv "$PROJECT_DIR/.venv"
"$PROJECT_DIR/.venv/bin/python" -m pip install --upgrade pip
"$PROJECT_DIR/.venv/bin/python" -m pip install -r "$PROJECT_DIR/requirements.txt"
"$PROJECT_DIR/.venv/bin/python" -m pip install -e "$PROJECT_DIR"
echo "Environment ready. Run ./scripts/reproduce.sh"
