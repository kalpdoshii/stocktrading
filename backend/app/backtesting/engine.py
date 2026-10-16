"""
engine.py — Backtesting Engine
==================================
Simulates trades based on model signals over historical data.

Strategy: Simple long-only
  - On UP signal → buy (or hold if already long)
  - On DOWN signal → sell (or stay out if not holding)

No short selling or leverage. Indian equity-delivery transaction costs are applied.

Usage:
    from app.backtesting.engine import run_backtest
    results = run_backtest("AAPL", model_version="sentiment_v1")
"""

import logging
from datetime import date, timedelta
from typing import Optional

import numpy as np
import pandas as pd
import yfinance as yf
from sqlalchemy.orm import Session

from app.config import INDIAN_EQUITY_COSTS, STARTING_CAPITAL
from app.database import SessionLocal
from app.features.builder import load_price_data
from app.features.technical import compute_indicators
from app.ml.predict import load_model
from app.features.builder import BASELINE_FEATURES, SENTIMENT_FEATURES, load_sentiment_data

logger = logging.getLogger(__name__)


def run_backtest(
    ticker: str,
    model_version: str = "sentiment_v1",
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    initial_capital: float = STARTING_CAPITAL,
    transaction_costs: Optional[dict] = None,
) -> dict:
    """
    Run a backtest simulation for a ticker using a trained model.

    Steps:
      1. Load price data and compute features
      2. Load the trained model
      3. Generate signals for each historical day
      4. Simulate trades: buy on UP, sell on DOWN
      5. Compute performance metrics
      6. Return results with equity curve

    Args:
        ticker: Stock symbol
        model_version: Which model to backtest
        start_date: Backtest start (default: use all available data)
        end_date: Backtest end (default: latest data)
        initial_capital: Starting cash (default: $10,000)

    Returns:
        dict with keys: ticker, model_version, metrics, equity_curve, trades
    """
    logger.info(f"Running backtest for {ticker} using {model_version}")

    # Step 1: Load data and compute features
    df = load_price_data(ticker)
    if df.empty:
        raise ValueError(f"No price data for {ticker}")

    df = compute_indicators(df)

    # Step 2: Load model
    model, feature_names = load_model(model_version)

    # Merge sentiment data if needed
    if any("sentiment" in f for f in feature_names):
        sentiment_df = load_sentiment_data(ticker)
        if not sentiment_df.empty:
            df = df.merge(sentiment_df, on="date", how="left")
            for col in SENTIMENT_FEATURES:
                if col in df.columns:
                    df[col] = df[col].ffill().fillna(0.0)

    # Ensure all features exist
    for col in feature_names:
        if col not in df.columns:
            df[col] = 0.0

    # Drop NaN rows
    df_clean = df.dropna(subset=feature_names).copy()

    # Apply date filters
    if start_date:
        df_clean = df_clean[df_clean["date"] >= start_date]
    if end_date:
        df_clean = df_clean[df_clean["date"] <= end_date]

    if len(df_clean) < 10:
        raise ValueError(f"Not enough data for backtest ({len(df_clean)} rows)")

    # Step 3: Generate signals
    X = df_clean[feature_names].values
    predictions = model.predict(X)
    probabilities = model.predict_proba(X)

    df_clean = df_clean.reset_index(drop=True)
    df_clean["signal"] = ["UP" if p == 1 else "DOWN" for p in predictions]
    df_clean["confidence"] = [float(probabilities[i][predictions[i]]) for i in range(len(predictions))]

    # Step 4: Simulate trades
    equity_curve, trades = _simulate_trades(
        df_clean,
        initial_capital,
        transaction_costs or INDIAN_EQUITY_COSTS,
    )

    # Step 5: Compute metrics
    from app.backtesting.metrics import compute_metrics
    metrics = compute_metrics(equity_curve, trades, initial_capital)
    benchmark_return = _fetch_nifty_return(
        df_clean["date"].iloc[0],
        df_clean["date"].iloc[-1],
    )
    metrics["benchmark_return_pct"] = benchmark_return
    metrics["excess_return_pct"] = (
        round(metrics["total_return_pct"] - benchmark_return, 2)
        if benchmark_return is not None else None
    )

    result = {
        "ticker": ticker,
        "model_version": model_version,
        "start_date": str(df_clean["date"].iloc[0]),
        "end_date": str(df_clean["date"].iloc[-1]),
        "initial_capital": initial_capital,
        "metrics": metrics,
        "equity_curve": equity_curve,
        "trades": trades,
    }

    # Log summary
    logger.info(f"\nBacktest Results for {ticker}:")
    logger.info(f"  Period: {result['start_date']} to {result['end_date']}")
    logger.info(f"  Total Return: {metrics['total_return_pct']:.2f}%")
    logger.info(f"  Win Rate: {metrics['win_rate']:.2f}%")
    logger.info(f"  Sharpe Ratio: {metrics['sharpe_ratio']:.3f}")
    logger.info(f"  Total Trades: {metrics['total_trades']}")

    return result


def _fetch_nifty_return(start: date, end: date) -> float | None:
    """Return buy-and-hold Nifty 50 performance for the backtest period."""
    try:
        prices = yf.download(
            "^NSEI",
            start=str(start),
            end=str(end + timedelta(days=1)),
            progress=False,
            auto_adjust=False,
        )
        if prices.empty:
            return None
        close = prices["Close"]
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]
        return round((float(close.iloc[-1]) / float(close.iloc[0]) - 1) * 100, 2)
    except Exception as error:
        logger.warning(f"Nifty 50 benchmark unavailable: {error}")
        return None


def _simulate_trades(
    df: pd.DataFrame,
    initial_capital: float,
    transaction_costs: dict,
) -> tuple[list[dict], list[dict]]:
    """
    Simple long-only trade simulation.

    Rules:
      - Start with cash = initial_capital, shares = 0
      - On UP signal (and not holding): buy as many shares as we can afford
      - On DOWN signal (and holding): sell all shares
      - Track portfolio value each day

    Returns:
        Tuple of (equity_curve, trades)
        equity_curve: [{date, portfolio_value, cash, shares_value}]
        trades: [{date, action, price, shares, value}]
    """
    cash = initial_capital
    shares = 0
    entry_value = 0.0
    total_costs = 0.0

    equity_curve = []
    trades = []

    for i, row in df.iterrows():
        price = float(row["close"])
        signal = row["signal"]
        current_date = str(row["date"])

        # ---- Trading Logic ----
        if signal == "UP" and shares == 0:
            # BUY: spend all cash on shares
            buy_price = price * (1 + transaction_costs["slippage_rate"])
            shares = int(cash / buy_price)
            if shares > 0:
                gross_value = shares * buy_price
                brokerage = gross_value * transaction_costs["brokerage_rate"]
                exchange = gross_value * transaction_costs["exchange_rate"]
                gst = (brokerage + exchange) * transaction_costs["gst_rate"]
                stamp_duty = gross_value * transaction_costs["stamp_duty_rate"]
                costs = brokerage + exchange + gst + stamp_duty
                cash -= gross_value + costs
                entry_value = gross_value + costs
                total_costs += costs
                trades.append({
                    "date": current_date,
                    "action": "BUY",
                    "price": round(buy_price, 2),
                    "shares": shares,
                    "value": round(gross_value, 2),
                    "costs": round(costs, 2),
                })

        elif signal == "DOWN" and shares > 0:
            # SELL: sell all shares
            sell_price = price * (1 - transaction_costs["slippage_rate"])
            gross_value = shares * sell_price
            brokerage = gross_value * transaction_costs["brokerage_rate"]
            stt = gross_value * transaction_costs["stt_rate"]
            exchange = gross_value * transaction_costs["exchange_rate"]
            gst = (brokerage + exchange) * transaction_costs["gst_rate"]
            costs = brokerage + stt + exchange + gst
            revenue = gross_value - costs
            cash += revenue
            pnl = revenue - entry_value
            total_costs += costs
            trades.append({
                "date": current_date,
                "action": "SELL",
                "price": round(sell_price, 2),
                "shares": shares,
                "value": round(gross_value, 2),
                "costs": round(costs, 2),
                "pnl": round(pnl, 2),
            })
            shares = 0
            entry_value = 0.0

        # ---- Record equity ----
        shares_value = shares * price
        portfolio_value = cash + shares_value

        equity_curve.append({
            "date": current_date,
            "portfolio_value": round(portfolio_value, 2),
            "cash": round(cash, 2),
            "shares_value": round(shares_value, 2),
            "transaction_costs": round(total_costs, 2),
        })

    return equity_curve, trades
