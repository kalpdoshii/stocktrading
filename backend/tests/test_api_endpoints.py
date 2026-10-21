"""
test_api_endpoints.py — API Integration Tests for ML & Prediction Endpoints
=============================================================================
Tests FastAPI endpoints:
  - GET /api/predict/{ticker}
  - GET /api/metrics/compare
  - GET /api/ml/experiments
  - GET /api/health
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint():
    """Verify health check endpoint returns 200."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_predict_endpoint_contract():
    """Verify prediction contract includes calibration, signal, and SHAP features."""
    response = client.get("/api/predict/RELIANCE.NS?threshold=0.55")
    assert response.status_code == 200
    data = response.json()

    assert data["ticker"] == "RELIANCE.NS"
    assert data["signal"] in ["UP", "DOWN", "HOLD"]
    assert "confidence" in data
    assert "is_calibrated" in data
    assert isinstance(data["top_features"], list)
    if len(data["top_features"]) > 0:
        top_f = data["top_features"][0]
        assert "name" in top_f
        # Must have SHAP attribution values
        assert "shap_value" in top_f or "importance" in top_f


def test_metrics_compare_contract():
    """Verify model comparison contract returns baselines, calibration, and deltas."""
    response = client.get("/api/metrics/compare")
    assert response.status_code == 200
    data = response.json()

    assert "baseline" in data
    assert "sentiment" in data
    assert "deltas" in data

    if data["baseline"]:
        assert "majority_baseline_accuracy" in data["baseline"]
        assert "brier_score" in data["baseline"]
        assert "accuracy" in data["baseline"]


def test_experiments_endpoint():
    """Verify experiment tracking API returns historical experiment runs."""
    response = client.get("/api/ml/experiments?limit=5")
    assert response.status_code == 200
    data = response.json()

    assert "count" in data
    assert "experiments" in data
    assert isinstance(data["experiments"], list)


def test_backtest_strategies_endpoint():
    """Verify strategy registry endpoint returns available strategies and execution options."""
    response = client.get("/api/backtest/strategies")
    assert response.status_code == 200
    data = response.json()

    assert "strategies" in data
    strategy_names = [s["name"] for s in data["strategies"]]
    assert "buy_and_hold" in strategy_names
    assert "sma_crossover" in strategy_names
    assert "rsi_mean_reversion" in strategy_names
    assert "ml_signal" in strategy_names
    assert "execution_timing_options" in data
    assert "next_open" in data["execution_timing_options"]


def test_backtest_run_endpoint():
    """Verify running a backtest via API returns metrics, equity curve, and disclaimer."""
    response = client.get(
        "/api/backtest/RELIANCE.NS?strategy_name=rsi_mean_reversion&execution_timing=next_open"
    )
    assert response.status_code == 200
    data = response.json()

    assert data["ticker"] == "RELIANCE.NS"
    assert "metrics" in data
    assert "cagr_pct" in data["metrics"]
    assert "sharpe_ratio" in data["metrics"]
    assert "sortino_ratio" in data["metrics"]
    assert "max_drawdown_pct" in data["metrics"]
    assert "equity_curve" in data
    assert "disclaimer" in data

