import httpx
import pytest

import app as app_module


pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


def configure_runtime():
    app_module.load_runtime()
    assert app_module.app.state.ready is True


async def test_health_summary_and_forecast_contracts():
    configure_runtime()
    transport = httpx.ASGITransport(app=app_module.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        health = await client.get("/api/health")
        summary = await client.get("/api/summary")
        forecast = await client.get("/api/forecast")
    assert health.status_code == 200 and health.json()["model_loaded"] is True
    assert summary.status_code == 200 and summary.json()["evidence_type"] == "historical_backtest"
    assert forecast.status_code == 200 and forecast.json()["predicted_close_usd"] > 0


async def test_history_and_backtest_are_chronological():
    configure_runtime()
    transport = httpx.ASGITransport(app=app_module.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        history = (await client.get("/api/history?days=90")).json()["candles"]
        backtest = (await client.get("/api/backtest?days=90")).json()["rows"]
    assert len(history) == 90 and history[0]["date"] < history[-1]["date"]
    assert len(backtest) == 90 and backtest[0]["target_date"] < backtest[-1]["target_date"]


async def test_models_and_features_contracts():
    configure_runtime()
    transport = httpx.ASGITransport(app=app_module.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        models = await client.get("/api/models")
        features = await client.get("/api/features?limit=8")
    assert models.status_code == 200 and len(models.json()["models"]) == 4
    assert features.status_code == 200 and len(features.json()["features"]) == 8
