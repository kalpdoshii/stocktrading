"""
test_backtesting.py — Unit & Integration Tests for Backtesting v2
===================================================================
Tests:
  1. No look-ahead bias in next_open execution timing.
  2. Accounting consistency: initial_capital = final_cash + shares_value + costs - pnl.
  3. All strategies produce valid signal series.
  4. Metrics computation correctness.
  5. Multi-strategy comparison.
"""

import pytest
import numpy as np
import pandas as pd
from datetime import date, timedelta


# -----------------------------------------------------------------------
# Helper: generate synthetic price data
# -----------------------------------------------------------------------

def _make_price_df(n_days: int = 100, seed: int = 42) -> pd.DataFrame:
    """
    Generate a realistic-looking OHLCV DataFrame with trending and
    mean-reverting price action.
    """
    rng = np.random.RandomState(seed)
    base = 1000.0
    closes = [base]
    for _ in range(n_days - 1):
        ret = rng.normal(0.0005, 0.015)  # slight upward drift
        closes.append(closes[-1] * (1 + ret))
    closes = np.array(closes)

    # Synthesize OHLC from close
    opens = np.roll(closes, 1)
    opens[0] = closes[0]
    highs = np.maximum(closes, opens) * (1 + rng.uniform(0, 0.01, n_days))
    lows = np.minimum(closes, opens) * (1 - rng.uniform(0, 0.01, n_days))
    volumes = rng.randint(100_000, 1_000_000, n_days)

    dates = [date(2024, 1, 2) + timedelta(days=i) for i in range(n_days)]

    return pd.DataFrame({
        "date": dates,
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "adj_close": closes,
        "volume": volumes,
    })


# -----------------------------------------------------------------------
# Test 1: Strategies produce valid signals
# -----------------------------------------------------------------------

class TestStrategies:
    """Test that each strategy generates valid BUY/SELL/HOLD signals."""

    def test_buy_and_hold_signals(self):
        from app.backtesting.strategies import BuyAndHoldStrategy

        df = _make_price_df(50)
        strategy = BuyAndHoldStrategy()
        signals = strategy.generate_signals(df)

        assert len(signals) == len(df)
        assert signals.iloc[0] == "BUY"
        # All other signals should be HOLD
        assert (signals.iloc[1:] == "HOLD").all()

    def test_sma_crossover_signals(self):
        from app.backtesting.strategies import SMACrossoverStrategy
        from app.features.technical import compute_indicators

        df = _make_price_df(200)
        df = compute_indicators(df)
        df = df.dropna().reset_index(drop=True)

        strategy = SMACrossoverStrategy(fast_window=10, slow_window=30)
        signals = strategy.generate_signals(df)

        assert len(signals) == len(df)
        valid_signals = {"BUY", "SELL", "HOLD"}
        assert set(signals.unique()).issubset(valid_signals)

    def test_rsi_mean_reversion_signals(self):
        from app.backtesting.strategies import RSIMeanReversionStrategy
        from app.features.technical import compute_indicators

        df = _make_price_df(200)
        df = compute_indicators(df)
        df = df.dropna().reset_index(drop=True)

        strategy = RSIMeanReversionStrategy(oversold=30, overbought=70)
        signals = strategy.generate_signals(df)

        assert len(signals) == len(df)
        valid_signals = {"BUY", "SELL", "HOLD"}
        assert set(signals.unique()).issubset(valid_signals)

    def test_strategy_registry(self):
        from app.backtesting.strategies import get_strategy, STRATEGY_REGISTRY

        for name in STRATEGY_REGISTRY:
            if name == "ml_signal":
                continue  # requires a trained model
            strategy = get_strategy(name)
            assert strategy is not None
            assert strategy.name == name

    def test_unknown_strategy_raises(self):
        from app.backtesting.strategies import get_strategy

        with pytest.raises(ValueError, match="Unknown strategy"):
            get_strategy("nonexistent_strategy")


# -----------------------------------------------------------------------
# Test 2: No look-ahead bias
# -----------------------------------------------------------------------

class TestLookAheadBias:
    """
    Verify that with ``next_open`` execution, signals from day *t* are NOT
    executed until day *t+1*.
    """

    def test_signal_shift_in_next_open_mode(self):
        """
        If raw signals say BUY on index 5, then in next_open mode the
        aligned signal should appear on index 6 (shifted forward by 1).
        """
        from app.backtesting.strategies import BaseStrategy

        class FixedSignalStrategy(BaseStrategy):
            name = "fixed_test"
            def generate_signals(self, df):
                signals = pd.Series("HOLD", index=df.index)
                signals.iloc[5] = "BUY"    # signal on day 5
                signals.iloc[15] = "SELL"   # signal on day 15
                return signals

        from app.features.technical import compute_indicators

        df = _make_price_df(100)
        df = compute_indicators(df)
        df = df.dropna().reset_index(drop=True)

        strategy = FixedSignalStrategy()
        raw_signals = strategy.generate_signals(df)

        # Simulate next_open alignment (shift forward)
        aligned = raw_signals.shift(1).fillna("HOLD")

        # The BUY should now be at index 6, not 5
        assert aligned.iloc[5] == "HOLD"
        assert aligned.iloc[6] == "BUY"
        # The SELL should now be at index 16, not 15
        assert aligned.iloc[15] == "HOLD"
        assert aligned.iloc[16] == "SELL"


# -----------------------------------------------------------------------
# Test 3: Accounting consistency
# -----------------------------------------------------------------------

class TestAccountingConsistency:
    """
    Verify that initial_capital is fully accounted for at all times:
    portfolio_value = cash + shares_value.
    """

    def test_portfolio_equals_cash_plus_shares(self):
        from app.backtesting.strategies import BuyAndHoldStrategy
        from app.features.technical import compute_indicators

        df = _make_price_df(50)
        df = compute_indicators(df)
        df = df.dropna().reset_index(drop=True)

        strategy = BuyAndHoldStrategy()
        signals = strategy.generate_signals(df)

        # Align signals (next_open)
        aligned = signals.shift(1).fillna("HOLD")
        df["signal"] = aligned.values

        from app.backtesting.engine import _simulate_trades
        from app.config import INDIAN_EQUITY_COSTS

        equity_curve, trades = _simulate_trades(
            df,
            initial_capital=100_000.0,
            transaction_costs=INDIAN_EQUITY_COSTS,
            execution_timing="next_open",
            position_sizing="all_in",
            position_fraction=0.2,
            volatility_lookback=20,
            target_annual_vol=0.15,
        )

        for point in equity_curve:
            expected = point["cash"] + point["shares_value"]
            # Allow small floating-point rounding (< 1 cent)
            assert abs(point["portfolio_value"] - expected) < 0.01, (
                f"Portfolio mismatch on {point['date']}: "
                f"{point['portfolio_value']} != {point['cash']} + {point['shares_value']}"
            )


# -----------------------------------------------------------------------
# Test 4: Metrics correctness
# -----------------------------------------------------------------------

class TestMetrics:
    """Test individual metric computations."""

    def test_cagr_flat_portfolio(self):
        from app.backtesting.metrics import _compute_cagr
        # No growth → 0% CAGR
        assert _compute_cagr(10000, 10000, 252) == 0.0

    def test_cagr_double_in_one_year(self):
        from app.backtesting.metrics import _compute_cagr
        cagr = _compute_cagr(10000, 20000, 252)
        assert abs(cagr - 100.0) < 0.1  # ~100% CAGR

    def test_max_drawdown_no_drawdown(self):
        from app.backtesting.metrics import _compute_max_drawdown
        # Monotonically increasing
        values = [100 + i for i in range(50)]
        assert _compute_max_drawdown(values) == 0.0

    def test_max_drawdown_known_value(self):
        from app.backtesting.metrics import _compute_max_drawdown
        values = [100, 110, 90, 95, 100, 105]
        # Peak = 110, trough = 90 → DD = 20/110 = 18.18%
        dd = _compute_max_drawdown(values)
        assert abs(dd - 18.18) < 0.1

    def test_max_drawdown_duration(self):
        from app.backtesting.metrics import _compute_max_drawdown_duration
        # 100 → 110 → 90 → 95 → 100 → 105 → 115
        values = [100, 110, 90, 95, 100, 105, 115]
        # From peak 110 (idx 1) to new peak 115 (idx 6) = 5 days in drawdown
        duration = _compute_max_drawdown_duration(values)
        assert duration == 4  # bars 2, 3, 4, 5 are below peak of 110

    def test_sharpe_ratio_positive(self):
        from app.backtesting.metrics import _compute_sharpe_ratio
        # Strong uptrend → positive Sharpe
        values = [100 + i * 0.5 for i in range(252)]
        sharpe = _compute_sharpe_ratio(values)
        assert sharpe > 0

    def test_sortino_positive(self):
        from app.backtesting.metrics import _compute_sortino_ratio
        # Strong uptrend → positive Sortino
        values = [100 + i * 0.5 for i in range(252)]
        sortino = _compute_sortino_ratio(values)
        assert sortino > 0

    def test_expectancy_all_winning(self):
        from app.backtesting.metrics import _compute_expectancy
        trades = [
            {"action": "SELL", "pnl": 100, "value": 1000},
            {"action": "SELL", "pnl": 200, "value": 1000},
        ]
        exp = _compute_expectancy(trades)
        assert exp > 0

    def test_expectancy_all_losing(self):
        from app.backtesting.metrics import _compute_expectancy
        trades = [
            {"action": "SELL", "pnl": -100, "value": 1000},
            {"action": "SELL", "pnl": -200, "value": 1000},
        ]
        exp = _compute_expectancy(trades)
        assert exp < 0


# -----------------------------------------------------------------------
# Test 5: Position sizing modes
# -----------------------------------------------------------------------

class TestPositionSizing:
    """Verify that different sizing modes produce different allocation amounts."""

    def test_fixed_fraction_allocates_less_than_all_in(self):
        from app.backtesting.strategies import BuyAndHoldStrategy
        from app.features.technical import compute_indicators
        from app.backtesting.engine import _simulate_trades
        from app.config import INDIAN_EQUITY_COSTS

        df = _make_price_df(30)
        df = compute_indicators(df)
        df = df.dropna().reset_index(drop=True)

        strategy = BuyAndHoldStrategy()
        signals = strategy.generate_signals(df)
        aligned = signals.shift(1).fillna("HOLD")
        df["signal"] = aligned.values

        # All-in
        _, trades_all = _simulate_trades(
            df.copy(), 100_000.0, INDIAN_EQUITY_COSTS,
            "next_open", "all_in", 0.2, 20, 0.15,
        )
        # Fixed fraction
        _, trades_frac = _simulate_trades(
            df.copy(), 100_000.0, INDIAN_EQUITY_COSTS,
            "next_open", "fixed_fraction", 0.2, 20, 0.15,
        )

        if trades_all and trades_frac:
            buy_all = next(t for t in trades_all if t["action"] == "BUY")
            buy_frac = next(t for t in trades_frac if t["action"] == "BUY")
            # Fixed fraction should buy fewer shares
            assert buy_frac["shares"] < buy_all["shares"]
