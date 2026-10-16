"""
technical.py — Technical Indicator Computation
=================================================
Calculates standard technical indicators from OHLCV price data.
All indicators are computed using the `ta` library for reliability.

Indicators computed:
  - SMA (20-day, 50-day)
  - EMA (12-day, 26-day)
  - RSI (14-day)
  - MACD (line, signal, histogram)
  - Bollinger Bands (upper, middle, lower)
  - 20-day historical volatility
  - Volume change %
  - Daily return %

Usage:
    from app.features.technical import compute_indicators
    df_with_indicators = compute_indicators(price_df)
"""

import logging

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add technical indicators to a DataFrame of OHLCV data.

    Args:
        df: DataFrame with columns: date, open, high, low, close, volume.
            Must be sorted by date ascending.

    Returns:
        DataFrame with all original columns plus technical indicator columns.
        Rows with NaN from indicator warm-up are NOT dropped — the caller
        decides how to handle them.
    """
    df = df.copy()
    df = df.sort_values("date").reset_index(drop=True)

    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]

    # ---- Simple Moving Averages ----
    df["sma_20"] = close.rolling(window=20).mean()
    df["sma_50"] = close.rolling(window=50).mean()

    # ---- Exponential Moving Averages ----
    df["ema_12"] = close.ewm(span=12, adjust=False).mean()
    df["ema_26"] = close.ewm(span=26, adjust=False).mean()

    # ---- RSI (Relative Strength Index, 14-day) ----
    df["rsi_14"] = _compute_rsi(close, period=14)

    # ---- MACD ----
    df["macd_line"] = df["ema_12"] - df["ema_26"]
    df["macd_signal"] = df["macd_line"].ewm(span=9, adjust=False).mean()
    df["macd_histogram"] = df["macd_line"] - df["macd_signal"]

    # ---- Bollinger Bands (20-day, 2 std dev) ----
    bb_middle = close.rolling(window=20).mean()
    bb_std = close.rolling(window=20).std()
    df["bb_upper"] = bb_middle + (2 * bb_std)
    df["bb_middle"] = bb_middle
    df["bb_lower"] = bb_middle - (2 * bb_std)

    # Bollinger Band width (normalized)
    df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / df["bb_middle"]

    # ---- Historical Volatility (20-day) ----
    daily_returns = close.pct_change()
    df["volatility_20"] = daily_returns.rolling(window=20).std() * np.sqrt(252)

    # ---- Volume Change % ----
    df["volume_change_pct"] = volume.pct_change() * 100

    # ---- Daily Return % ----
    df["daily_return_pct"] = daily_returns * 100

    # ---- Price relative to SMA (useful feature for ML) ----
    df["price_to_sma20"] = close / df["sma_20"]
    df["price_to_sma50"] = close / df["sma_50"]

    logger.info(
        f"Computed {len([c for c in df.columns if c not in ['date', 'open', 'high', 'low', 'close', 'adj_close', 'volume', 'ticker']])} "
        f"technical indicators for {len(df)} rows"
    )

    return df


def _compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """
    Compute RSI (Relative Strength Index) manually.

    RSI = 100 - (100 / (1 + RS))
    where RS = average gain / average loss over `period` days.
    """
    delta = series.diff()

    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)

    # Use exponential moving average for smoothing (Wilder's method)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return rsi
