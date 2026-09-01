#!/usr/bin/env python3
"""Download and persist Coinbase BTC-USD daily candles."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from btc_forecast.data_source import fetch_coinbase_daily


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2020-01-01")
    parser.add_argument("--end", default=datetime.now(timezone.utc).date().isoformat())
    parser.add_argument("--output", type=Path, default=Path("data/btc_usd_daily.csv"))
    parser.add_argument("--metadata", type=Path, default=Path("artifacts/data_provenance.json"))
    args = parser.parse_args()

    frame = fetch_coinbase_daily(args.start, args.end)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.metadata.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(args.output, index=False)
    metadata = {
        "source": "Coinbase Exchange API",
        "product": "BTC-USD",
        "endpoint": "https://api.exchange.coinbase.com/products/BTC-USD/candles",
        "granularity_seconds": 86400,
        "requested_start": args.start,
        "requested_end": args.end,
        "observed_start": frame["date"].min().isoformat(),
        "observed_end": frame["date"].max().isoformat(),
        "candles": len(frame),
        "downloaded_at": datetime.now(timezone.utc).isoformat(),
    }
    args.metadata.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
