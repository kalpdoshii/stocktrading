"""
metrics.py — Backtesting Performance Metrics
================================================
Computes standard trading performance metrics from backtest results.

Metrics:
  - Total Return %
  - Win Rate %
  - Sharpe Ratio (annualized)
  - Max Drawdown %
  - Number of trades
  - Average trade P&L

Usage:
    from app.backtesting.metrics import compute_metrics
    metrics = compute_metrics(equity_curve, trades, initial_capital)
"""

import logging

import numpy as np

logger = logging.getLogger(__name__)


def compute_metrics(
    equity_curve: list[dict],
    trades: list[dict],
    initial_capital: float,
) -> dict:
    """
    Compute comprehensive trading performance metrics.

    Args:
        equity_curve: List of {date, portfolio_value, cash, shares_value}
        trades: List of {date, action, price, shares, value, pnl?}
        initial_capital: Starting capital amount

    Returns:
        dict with all computed metrics
    """
    # ---- Portfolio values ----
    portfolio_values = [e["portfolio_value"] for e in equity_curve]
    final_value = portfolio_values[-1] if portfolio_values else initial_capital

    # ---- Total Return ----
    total_return_pct = ((final_value - initial_capital) / initial_capital) * 100

    # ---- Trade Analysis ----
    sell_trades = [t for t in trades if t["action"] == "SELL"]
    total_trades = len(sell_trades)

    winning_trades = len([t for t in sell_trades if t.get("pnl", 0) > 0])
    losing_trades = len([t for t in sell_trades if t.get("pnl", 0) <= 0])

    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

    # Average P&L per trade
    pnls = [t.get("pnl", 0) for t in sell_trades]
    avg_pnl = float(np.mean(pnls)) if pnls else 0
    transaction_costs = sum(t.get("costs", 0) for t in trades)

    # ---- Sharpe Ratio (annualized) ----
    sharpe_ratio = _compute_sharpe_ratio(portfolio_values)

    # ---- Max Drawdown ----
    max_drawdown_pct = _compute_max_drawdown(portfolio_values)

    metrics = {
        "total_return_pct": round(total_return_pct, 2),
        "final_value": round(final_value, 2),
        "total_trades": total_trades,
        "winning_trades": winning_trades,
        "losing_trades": losing_trades,
        "win_rate": round(win_rate, 2),
        "sharpe_ratio": round(sharpe_ratio, 3),
        "max_drawdown_pct": round(max_drawdown_pct, 2),
        "avg_trade_pnl": round(avg_pnl, 2),
        "transaction_costs": round(transaction_costs, 2),
    }

    return metrics


def _compute_sharpe_ratio(
    portfolio_values: list[float],
    risk_free_rate: float = 0.05,
    trading_days: int = 252,
) -> float:
    """
    Compute annualized Sharpe Ratio.

    Sharpe = (mean_daily_return - risk_free_daily) / std_daily_return * sqrt(252)

    Args:
        portfolio_values: Daily portfolio values
        risk_free_rate: Annual risk-free rate (default 5%)
        trading_days: Trading days per year (default 252)

    Returns:
        Annualized Sharpe Ratio
    """
    if len(portfolio_values) < 2:
        return 0.0

    values = np.array(portfolio_values, dtype=float)
    daily_returns = np.diff(values) / values[:-1]

    if len(daily_returns) == 0 or np.std(daily_returns) == 0:
        return 0.0

    # Convert annual risk-free rate to daily
    daily_rf = (1 + risk_free_rate) ** (1 / trading_days) - 1

    excess_returns = daily_returns - daily_rf
    sharpe = (np.mean(excess_returns) / np.std(excess_returns)) * np.sqrt(trading_days)

    return float(sharpe)


def _compute_max_drawdown(portfolio_values: list[float]) -> float:
    """
    Compute maximum drawdown as a percentage.

    Max Drawdown = max((peak - trough) / peak) * 100

    Returns:
        Maximum drawdown percentage (always positive or zero)
    """
    if len(portfolio_values) < 2:
        return 0.0

    values = np.array(portfolio_values, dtype=float)
    peak = values[0]
    max_dd = 0.0

    for value in values:
        if value > peak:
            peak = value
        drawdown = (peak - value) / peak * 100
        if drawdown > max_dd:
            max_dd = drawdown

    return float(max_dd)
