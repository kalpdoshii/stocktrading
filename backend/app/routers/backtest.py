"""
backtest.py — Backtest API Endpoints
========================================
GET /api/backtest/{ticker}  → backtest results for a ticker
"""

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import TICKERS
from app.models import BacktestResult

router = APIRouter(tags=["Backtest"])


@router.get("/backtest/{ticker}")
def get_backtest(
    ticker: str,
    model_version: str = "sentiment_v1",
    db: Session = Depends(get_db),
):
    """
    Get backtest results for a ticker.

    Returns performance metrics and equity curve data for charting.
    Falls back to running a live backtest if no stored results exist.
    """
    ticker = ticker.upper()

    if ticker not in TICKERS:
        raise HTTPException(status_code=404, detail=f"Ticker '{ticker}' not configured")

    # Try stored results first
    result = (
        db.query(BacktestResult)
        .filter(
            BacktestResult.ticker == ticker,
            BacktestResult.model_version == model_version,
        )
        .order_by(BacktestResult.created_at.desc())
        .first()
    )

    if result:
        equity_curve = result.equity_curve_json
        if isinstance(equity_curve, str):
            equity_curve = json.loads(equity_curve)

        return {
            "ticker": ticker,
            "model_version": result.model_version,
            "start_date": str(result.start_date) if result.start_date else None,
            "end_date": str(result.end_date) if result.end_date else None,
            "metrics": {
                "total_return_pct": result.total_return_pct,
                "win_rate": result.win_rate,
                "sharpe_ratio": result.sharpe_ratio,
                "transaction_costs": result.transaction_costs,
                "benchmark_return_pct": result.benchmark_return_pct,
                "excess_return_pct": result.excess_return_pct,
                "total_trades": result.total_trades,
                "winning_trades": result.winning_trades,
                "losing_trades": result.losing_trades,
            },
            "equity_curve": equity_curve,
        }

    # No stored results — try running live backtest
    try:
        from app.backtesting.engine import run_backtest
        bt_result = run_backtest(ticker, model_version)

        return {
            "ticker": ticker,
            "model_version": model_version,
            "start_date": bt_result["start_date"],
            "end_date": bt_result["end_date"],
            "metrics": bt_result["metrics"],
            "equity_curve": bt_result["equity_curve"],
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Backtest failed: {str(e)}"
        )
