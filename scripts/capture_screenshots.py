#!/usr/bin/env python3
"""Capture deterministic dashboard evidence for the repository README."""

from __future__ import annotations

import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8560")
    parser.add_argument("--output", type=Path, default=Path("docs/screenshots"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000}, device_scale_factor=1)
        page.goto(args.url, wait_until="networkidle")
        page.locator("#engine-state").wait_for(state="visible")
        page.wait_for_function("document.querySelector('#engine-state').textContent === 'READY'")
        page.screenshot(path=args.output / "market-pulse.png", full_page=True)

        page.get_by_role("button", name="Backtest lab").click()
        page.wait_for_timeout(250)
        page.screenshot(path=args.output / "backtest-lab.png", full_page=True)

        page.get_by_role("button", name="Methodology").click()
        page.wait_for_timeout(250)
        page.screenshot(path=args.output / "methodology.png", full_page=True)
        browser.close()

    print(f"Captured dashboard evidence in {args.output.resolve()}")


if __name__ == "__main__":
    main()
