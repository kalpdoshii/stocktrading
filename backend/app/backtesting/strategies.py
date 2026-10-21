"""
strategies.py — Modular Backtesting Strategies
================================================
Each strategy implements the same interface:

    class SomeStrategy(BaseStrategy):
        name = "some_strategy"
        def generate_signals(self, df: pd.DataFrame) -> pd.Series:
            ...  # Return a Series with values in {"BUY", "SELL", "HOLD"}

Built-in strategies:
  1. BuyAndHoldStrategy    — Buy on day 1, hold until the end.
  2. SMACrossoverStrategy  — Golden/death cross of two simple moving averages.
  3. RSIMeanReversionStrategy — Buy when RSI oversold, sell when overbought.
  4. MLSignalStrategy      — Use trained model predictions with optional
                              calibrated confidence filtering & HOLD abstention.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Base Strategy
# ---------------------------------------------------------------------------

class BaseStrategy(ABC):
    """All strategies must subclass this and implement generate_signals."""

    name: str = "base"

    def __init__(self, **params: Any):
        self.params = params

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        """
        Return a pd.Series aligned with *df.index* whose values are exactly
        one of: ``"BUY"``, ``"SELL"``, ``"HOLD"``.

        The convention is:
          * ``"BUY"``  — open or add to a long position
          * ``"SELL"`` — close the long position
          * ``"HOLD"`` — do nothing / keep current state
        """
        ...

    def __repr__(self) -> str:
        params_str = ", ".join(f"{k}={v!r}" for k, v in self.params.items())
        return f"{self.__class__.__name__}({params_str})"


# ---------------------------------------------------------------------------
# 1. Buy-and-Hold  (benchmark)
# ---------------------------------------------------------------------------

class BuyAndHoldStrategy(BaseStrategy):
    """Buy on the first bar and hold until the last bar."""

    name = "buy_and_hold"

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        signals = pd.Series("HOLD", index=df.index)
        if len(signals) > 0:
            signals.iloc[0] = "BUY"
        return signals


# ---------------------------------------------------------------------------
# 2. SMA Crossover
# ---------------------------------------------------------------------------

class SMACrossoverStrategy(BaseStrategy):
    """
    Golden / death cross between two simple moving averages.

    Parameters:
        fast_window (int): Short SMA window (default 20).
        slow_window (int): Long SMA window (default 50).
    """

    name = "sma_crossover"

    def __init__(self, fast_window: int = 20, slow_window: int = 50, **kw: Any):
        super().__init__(fast_window=fast_window, slow_window=slow_window, **kw)
        self.fast_window = fast_window
        self.slow_window = slow_window

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        close = df["close"].astype(float)
        sma_fast = close.rolling(self.fast_window, min_periods=self.fast_window).mean()
        sma_slow = close.rolling(self.slow_window, min_periods=self.slow_window).mean()

        signals = pd.Series("HOLD", index=df.index)
        # Cross-over detection: fast crosses above slow → BUY
        # fast crosses below slow → SELL
        prev_fast = sma_fast.shift(1)
        prev_slow = sma_slow.shift(1)

        buy_mask = (prev_fast <= prev_slow) & (sma_fast > sma_slow)
        sell_mask = (prev_fast >= prev_slow) & (sma_fast < sma_slow)

        signals[buy_mask] = "BUY"
        signals[sell_mask] = "SELL"

        return signals


# ---------------------------------------------------------------------------
# 3. RSI Mean Reversion
# ---------------------------------------------------------------------------

class RSIMeanReversionStrategy(BaseStrategy):
    """
    Buy when RSI dips below the oversold threshold,
    sell when RSI rises above the overbought threshold.

    Parameters:
        rsi_column (str):  Column name for pre-computed RSI (default ``"rsi_14"``).
        oversold  (float): RSI threshold to trigger buy  (default 30).
        overbought (float): RSI threshold to trigger sell (default 70).
    """

    name = "rsi_mean_reversion"

    def __init__(
        self,
        rsi_column: str = "rsi_14",
        oversold: float = 30.0,
        overbought: float = 70.0,
        **kw: Any,
    ):
        super().__init__(
            rsi_column=rsi_column,
            oversold=oversold,
            overbought=overbought,
            **kw,
        )
        self.rsi_column = rsi_column
        self.oversold = oversold
        self.overbought = overbought

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        if self.rsi_column not in df.columns:
            logger.warning(
                f"RSI column '{self.rsi_column}' not in DataFrame; "
                f"returning all HOLD"
            )
            return pd.Series("HOLD", index=df.index)

        rsi = df[self.rsi_column].astype(float)
        prev_rsi = rsi.shift(1)

        signals = pd.Series("HOLD", index=df.index)

        # Buy: RSI crosses below oversold (enter)
        buy_mask = (prev_rsi >= self.oversold) & (rsi < self.oversold)
        # Sell: RSI crosses above overbought (exit)
        sell_mask = (prev_rsi <= self.overbought) & (rsi > self.overbought)

        signals[buy_mask] = "BUY"
        signals[sell_mask] = "SELL"

        return signals


# ---------------------------------------------------------------------------
# 4. ML Signal Strategy (uses trained model predictions)
# ---------------------------------------------------------------------------

class MLSignalStrategy(BaseStrategy):
    """
    Use a trained ML model to generate signals.

    The strategy loads the model, runs inference on each bar, and maps
    the predicted class to BUY / SELL.  When calibrated confidence is below
    ``confidence_threshold``, the signal is forced to HOLD (abstention).

    Parameters:
        model_version (str):         Model artifact to load (default ``"sentiment_v1"``).
        confidence_threshold (float): Min calibrated probability to act (default 0.55).
    """

    name = "ml_signal"

    def __init__(
        self,
        model_version: str = "sentiment_v1",
        confidence_threshold: float = 0.55,
        **kw: Any,
    ):
        super().__init__(
            model_version=model_version,
            confidence_threshold=confidence_threshold,
            **kw,
        )
        self.model_version = model_version
        self.confidence_threshold = confidence_threshold
        self._model = None
        self._feature_names: list[str] = []
        self._calibrator = None

    def _ensure_model_loaded(self) -> None:
        """Lazy-load model on first use."""
        if self._model is not None:
            return
        from app.ml.predict import load_model_artifact
        self._model, self._feature_names, self._calibrator = load_model_artifact(
            self.model_version,
        )

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        self._ensure_model_loaded()

        # Ensure all required features exist
        for col in self._feature_names:
            if col not in df.columns:
                df = df.copy()
                df[col] = 0.0

        feature_matrix = df[self._feature_names].values
        raw_probs = self._model.predict_proba(feature_matrix)

        # raw_probs shape: (n, 2) — columns [prob_DOWN, prob_UP]
        prob_up = raw_probs[:, 1].astype(float)

        # Attempt calibration
        if self._calibrator is not None:
            try:
                prob_up_cal = np.array([
                    float(self._calibrator.predict_calibrated_proba(
                        self._model, feature_matrix[i : i + 1]
                    )[0])
                    for i in range(len(feature_matrix))
                ])
            except Exception:
                prob_up_cal = prob_up
        else:
            prob_up_cal = prob_up

        # Map to signals with abstention
        threshold = self.confidence_threshold
        signals = []
        for p_cal, p_raw in zip(prob_up_cal, prob_up):
            confidence = max(p_cal, 1 - p_cal)
            if confidence < threshold:
                signals.append("HOLD")
            elif p_cal >= 0.5:
                signals.append("BUY")
            else:
                signals.append("SELL")

        return pd.Series(signals, index=df.index)


# ---------------------------------------------------------------------------
# Strategy Registry — simple name → class mapping
# ---------------------------------------------------------------------------

STRATEGY_REGISTRY: dict[str, type[BaseStrategy]] = {
    "buy_and_hold": BuyAndHoldStrategy,
    "sma_crossover": SMACrossoverStrategy,
    "rsi_mean_reversion": RSIMeanReversionStrategy,
    "ml_signal": MLSignalStrategy,
}


def get_strategy(name: str, **params: Any) -> BaseStrategy:
    """
    Instantiate a strategy by name.

    Args:
        name: One of the keys in ``STRATEGY_REGISTRY``.
        **params: Strategy-specific keyword arguments.

    Returns:
        An initialised ``BaseStrategy`` subclass.

    Raises:
        ValueError: If *name* is not registered.
    """
    cls = STRATEGY_REGISTRY.get(name)
    if cls is None:
        available = ", ".join(sorted(STRATEGY_REGISTRY.keys()))
        raise ValueError(f"Unknown strategy '{name}'. Available: {available}")
    return cls(**params)
