"""
metrics.py — Backtesting Performance Metrics v2
===================================================
Computes comprehensive trading performance metrics from backtest results.

Metrics:
  - Total Return %
  - CAGR % (annualised compound growth rate)
  - Win Rate %
  - Sharpe Ratio  (annualised, excess over risk-free)
  - Sortino Ratio (annualised, downside deviation only)
  - Max Drawdown %
  - Max Drawdown Duration (trading days)
  - Portfolio Turnover %
  - Trade Expectancy (avg profit per unit risked)
  - Number of trades, average trade P&L, transaction costs

Usage:
    from app.backtesting.metrics import compute_metrics
    metrics = compute_metrics(equity_curve, trades, initial_capital)
"""

from __future__ import annotations

import logging
import math

import numpy as np

logger = logging.getLogger(__name__)


def _clean_num(val: float | None, decimals: int = 2) -> float:
    if val is None:
        return 0.0
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return 0.0
        return round(f, decimals)
    except (ValueError, TypeError):
        return 0.0



def compute_metrics(
    equity_curve: list[dict],
    trades: list[dict],
    initial_capital: float,
) -> dict:
    """
    Compute comprehensive trading performance metrics.

    Args:
        equity_curve: List of {date, portfolio_value, cash, shares_value}.
        trades:       List of {date, action, price, shares, value, costs, pnl?}.
        initial_capital: Starting capital amount.

    Returns:
        dict with all computed metrics.
    """
    portfolio_values = [e["portfolio_value"] for e in equity_curve]
    final_value = portfolio_values[-1] if portfolio_values else initial_capital
    n_days = len(portfolio_values)

    # ── Total Return ─────────────────────────────────────────────────
    total_return_pct = ((final_value - initial_capital) / initial_capital) * 100

    # ── CAGR (Compound Annual Growth Rate) ────────────────────────────
    cagr_pct = _compute_cagr(initial_capital, final_value, n_days)

    # ── Annualised Volatility ─────────────────────────────────────────
    annual_vol_pct = _compute_annual_volatility(portfolio_values)

    # ── Trade Analysis ────────────────────────────────────────────────
    sell_trades = [t for t in trades if t["action"] == "SELL"]
    total_trades = len(sell_trades)

    pnls = [t.get("pnl", 0) for t in sell_trades]
    winning_trades = len([p for p in pnls if p > 0])
    losing_trades = len([p for p in pnls if p <= 0])

    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0
    avg_pnl = float(np.mean(pnls)) if pnls else 0.0
    transaction_costs = sum(t.get("costs", 0) for t in trades)

    # ── Sharpe Ratio (annualised) ─────────────────────────────────────
    sharpe_ratio = _compute_sharpe_ratio(portfolio_values)

    # ── Sortino Ratio (annualised) ────────────────────────────────────
    sortino_ratio = _compute_sortino_ratio(portfolio_values)

    # ── Max Drawdown ─────────────────────────────────────────────────
    max_drawdown_pct = _compute_max_drawdown(portfolio_values)

    # ── Max Drawdown Duration (trading days) ──────────────────────────
    max_dd_duration = _compute_max_drawdown_duration(portfolio_values)

    # ── Portfolio Turnover % ──────────────────────────────────────────
    turnover_pct = _compute_turnover(trades, equity_curve, initial_capital)

    # ── Trade Expectancy ──────────────────────────────────────────────
    trade_expectancy = _compute_expectancy(sell_trades)

    # ── Profit Factor ─────────────────────────────────────────────────
    gross_profit = sum(p for p in pnls if p > 0)
    gross_loss = abs(sum(p for p in pnls if p < 0))
    if gross_loss > 0:
        profit_factor = round(gross_profit / gross_loss, 3)
    elif gross_profit > 0:
        profit_factor = None  # None indicates infinite/undefined for valid JSON serialization
    else:
        profit_factor = 0.0

    metrics = {
        "total_return_pct": _clean_num(total_return_pct, 2),
        "cagr_pct": _clean_num(cagr_pct, 2),
        "annual_volatility_pct": _clean_num(annual_vol_pct, 2),
        "final_value": _clean_num(final_value, 2),
        "total_trades": total_trades,
        "winning_trades": winning_trades,
        "losing_trades": losing_trades,
        "win_rate": _clean_num(win_rate, 2),
        "sharpe_ratio": _clean_num(sharpe_ratio, 3),
        "sortino_ratio": _clean_num(sortino_ratio, 3),
        "max_drawdown_pct": _clean_num(max_drawdown_pct, 2),
        "max_drawdown_duration_days": int(max_dd_duration or 0),
        "avg_trade_pnl": _clean_num(avg_pnl, 2),
        "trade_expectancy": _clean_num(trade_expectancy, 4),
        "profit_factor": profit_factor,
        "turnover_pct": _clean_num(turnover_pct, 2),
        "transaction_costs": _clean_num(transaction_costs, 2),
    }

    return metrics


# -----------------------------------------------------------------------
# Individual metric computations
# -----------------------------------------------------------------------

def _compute_cagr(
    initial: float,
    final: float,
    n_days: int,
    trading_days: int = 252,
) -> float:
    """Compound Annual Growth Rate as a percentage."""
    if n_days < 2 or initial <= 0:
        return 0.0
    years = n_days / trading_days
    if years <= 0:
        return 0.0
    return ((final / initial) ** (1 / years) - 1) * 100


def _compute_annual_volatility(
    portfolio_values: list[float],
    trading_days: int = 252,
) -> float:
    """Annualised portfolio volatility as a percentage."""
    if len(portfolio_values) < 2:
        return 0.0
    values = np.array(portfolio_values, dtype=float)
    daily_returns = np.diff(values) / values[:-1]
    if len(daily_returns) == 0:
        return 0.0
    return float(np.std(daily_returns, ddof=1) * np.sqrt(trading_days) * 100)


def _compute_sharpe_ratio(
    portfolio_values: list[float],
    risk_free_rate: float = 0.05,
    trading_days: int = 252,
) -> float:
    """
    Annualised Sharpe Ratio.

    Sharpe = (mean_daily_return − risk_free_daily) / std(daily_returns) × √252
    """
    if len(portfolio_values) < 2:
        return 0.0

    values = np.array(portfolio_values, dtype=float)
    daily_returns = np.diff(values) / values[:-1]

    if len(daily_returns) == 0 or np.std(daily_returns, ddof=1) == 0:
        return 0.0

    daily_rf = (1 + risk_free_rate) ** (1 / trading_days) - 1
    excess = daily_returns - daily_rf
    return float(np.mean(excess) / np.std(excess, ddof=1) * np.sqrt(trading_days))


def _compute_sortino_ratio(
    portfolio_values: list[float],
    risk_free_rate: float = 0.05,
    trading_days: int = 252,
) -> float:
    """
    Annualised Sortino Ratio.

    Like Sharpe but uses only downside (negative) deviation.
    """
    if len(portfolio_values) < 2:
        return 0.0

    values = np.array(portfolio_values, dtype=float)
    daily_returns = np.diff(values) / values[:-1]
    daily_rf = (1 + risk_free_rate) ** (1 / trading_days) - 1
    excess = daily_returns - daily_rf

    downside = excess[excess < 0]
    if len(downside) == 0:
        # No negative returns — ratio is "infinite" (positive)
        return float(np.mean(excess) * np.sqrt(trading_days) * 100) if np.mean(excess) > 0 else 0.0

    downside_std = np.std(downside, ddof=1)
    if downside_std == 0:
        return 0.0

    return float(np.mean(excess) / downside_std * np.sqrt(trading_days))


def _compute_max_drawdown(portfolio_values: list[float]) -> float:
    """Maximum drawdown as a positive percentage."""
    if len(portfolio_values) < 2:
        return 0.0

    values = np.array(portfolio_values, dtype=float)
    peak = values[0]
    max_dd = 0.0

    for value in values:
        if value > peak:
            peak = value
        dd = (peak - value) / peak * 100
        if dd > max_dd:
            max_dd = dd

    return float(max_dd)


def _compute_max_drawdown_duration(portfolio_values: list[float]) -> int:
    """
    Maximum drawdown duration in trading days.

    Measures the longest consecutive period from a peak until a new peak
    is established.
    """
    if len(portfolio_values) < 2:
        return 0

    values = np.array(portfolio_values, dtype=float)
    peak = values[0]
    dd_start = 0
    max_duration = 0
    current_duration = 0

    for i, value in enumerate(values):
        if value >= peak:
            peak = value
            if current_duration > max_duration:
                max_duration = current_duration
            current_duration = 0
        else:
            current_duration += 1

    # Handle case where drawdown extends to the end
    if current_duration > max_duration:
        max_duration = current_duration

    return max_duration


def _compute_turnover(
    trades: list[dict],
    equity_curve: list[dict],
    initial_capital: float,
) -> float:
    """
    Portfolio turnover as a percentage.

    Turnover = total traded value / average portfolio value × 100.
    """
    if not equity_curve:
        return 0.0

    total_traded = sum(t.get("value", 0) for t in trades)
    avg_portfolio = np.mean([e["portfolio_value"] for e in equity_curve])

    if avg_portfolio == 0:
        return 0.0

    return float(total_traded / avg_portfolio * 100)


def _compute_expectancy(sell_trades: list[dict]) -> float:
    """
    Trade expectancy = (win_rate × avg_win) − (loss_rate × avg_loss).

    Expressed as a ratio per unit risked (i.e. per dollar of avg trade value).
    """
    if not sell_trades:
        return 0.0

    pnls = [t.get("pnl", 0) for t in sell_trades]
    wins = [p for p in pnls if p > 0]
    losses = [abs(p) for p in pnls if p <= 0]

    n = len(pnls)
    win_rate = len(wins) / n
    loss_rate = len(losses) / n

    avg_win = float(np.mean(wins)) if wins else 0.0
    avg_loss = float(np.mean(losses)) if losses else 0.0

    # Normalise by average trade value
    avg_trade_value = np.mean([t.get("value", 1) for t in sell_trades])
    if avg_trade_value == 0:
        return 0.0

    expectancy = (win_rate * avg_win - loss_rate * avg_loss) / avg_trade_value
    return float(expectancy)
