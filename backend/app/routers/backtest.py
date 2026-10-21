"""
backtest.py — Backtest API Endpoints v2
===========================================
GET  /api/backtest/{ticker}       → run or retrieve backtest results
GET  /api/backtest/strategies     → list available strategies
"""

import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import TICKERS
from app.models import BacktestResult

router = APIRouter(tags=["Backtest"])


@router.get("/backtest/strategies")
def list_strategies():
    """
    List all available backtesting strategies and their configurable parameters.
    """
    from app.backtesting.strategies import STRATEGY_REGISTRY

    strategies = []
    for name, cls in STRATEGY_REGISTRY.items():
        strategies.append({
            "name": name,
            "description": (cls.__doc__ or "").strip().split("\n")[0],
        })

    return {
        "strategies": strategies,
        "execution_timing_options": ["next_open", "same_close"],
        "position_sizing_options": ["all_in", "fixed_fraction", "volatility_adjusted"],
    }


@router.get("/backtest/{ticker}")
def get_backtest(
    ticker: str,
    model_version: str = "sentiment_v1",
    strategy_name: str = Query("ml_signal", description="Strategy to backtest"),
    execution_timing: str = Query("next_open", description="next_open or same_close"),
    position_sizing: str = Query("all_in", description="all_in, fixed_fraction, or volatility_adjusted"),
    position_fraction: float = Query(0.20, description="Fraction per trade (for fixed_fraction)"),
    confidence_threshold: Optional[float] = Query(None, description="ML confidence threshold (ml_signal only)"),
    fast_window: Optional[int] = Query(None, description="SMA fast window (sma_crossover only)"),
    slow_window: Optional[int] = Query(None, description="SMA slow window (sma_crossover only)"),
    oversold: Optional[float] = Query(None, description="RSI oversold threshold (rsi_mean_reversion only)"),
    overbought: Optional[float] = Query(None, description="RSI overbought threshold (rsi_mean_reversion only)"),
    db: Session = Depends(get_db),
):
    """
    Run a backtest for a ticker with the specified strategy and parameters.

    Returns performance metrics, equity curve data, trade log, and a disclaimer
    clearly marking these as simulated results.
    """
    ticker = ticker.upper()

    if ticker not in TICKERS:
        raise HTTPException(status_code=404, detail=f"Ticker '{ticker}' not configured")

    # Build strategy-specific params
    strategy_params: dict = {}
    if strategy_name == "ml_signal":
        strategy_params["model_version"] = model_version
        if confidence_threshold is not None:
            strategy_params["confidence_threshold"] = confidence_threshold
    elif strategy_name == "sma_crossover":
        if fast_window is not None:
            strategy_params["fast_window"] = fast_window
        if slow_window is not None:
            strategy_params["slow_window"] = slow_window
    elif strategy_name == "rsi_mean_reversion":
        if oversold is not None:
            strategy_params["oversold"] = oversold
        if overbought is not None:
            strategy_params["overbought"] = overbought

    # Run live backtest with strategy
    try:
        from app.backtesting.engine import run_backtest

        bt_result = run_backtest(
            ticker,
            strategy_name=strategy_name,
            strategy_params=strategy_params,
            model_version=model_version,
            execution_timing=execution_timing,
            position_sizing=position_sizing,
            position_fraction=position_fraction,
        )

        return bt_result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Backtest failed: {str(e)}"
        )
