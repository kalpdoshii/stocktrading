"""
builder.py — Feature Matrix Builder
======================================
Pulls price data from MySQL, computes technical indicators, and
assembles a training-ready feature matrix with a binary target label.

The target label:
  1 = next-day close > today's close (UP)
  0 = next-day close <= today's close (DOWN)

Usage:
    from app.features.builder import build_feature_matrix
    X_train, X_test, y_train, y_test, feature_names = build_feature_matrix("AAPL")
"""

import logging

import pandas as pd
import numpy as np
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import PriceData, SentimentScore
from app.features.technical import compute_indicators

logger = logging.getLogger(__name__)

# Features used for the baseline model (price + technical only)
BASELINE_FEATURES = [
    "sma_20", "sma_50", "ema_12", "ema_26",
    "rsi_14",
    "macd_line", "macd_signal", "macd_histogram",
    "bb_upper", "bb_lower", "bb_width",
    "volatility_20",
    "volume_change_pct",
    "daily_return_pct",
    "price_to_sma20", "price_to_sma50",
]

# Additional features when sentiment is included
SENTIMENT_FEATURES = [
    "sentiment_compound",
    "sentiment_positive",
    "sentiment_negative",
]


def load_price_data(ticker: str) -> pd.DataFrame:
    """
    Load OHLCV price data for a ticker from MySQL.

    Returns:
        DataFrame with columns: date, open, high, low, close, adj_close, volume
    """
    db: Session = SessionLocal()
    try:
        rows = (
            db.query(PriceData)
            .filter(PriceData.ticker == ticker)
            .order_by(PriceData.date)
            .all()
        )

        if not rows:
            logger.warning(f"No price data found for {ticker}")
            return pd.DataFrame()

        data = [{
            "date": r.date,
            "open": float(r.open) if r.open else None,
            "high": float(r.high) if r.high else None,
            "low": float(r.low) if r.low else None,
            "close": float(r.close) if r.close else None,
            "adj_close": float(r.adj_close) if r.adj_close else None,
            "volume": int(r.volume) if r.volume else None,
        } for r in rows]

        df = pd.DataFrame(data)
        logger.info(f"Loaded {len(df)} price rows for {ticker}")
        return df

    finally:
        db.close()


def load_sentiment_data(ticker: str) -> pd.DataFrame:
    """
    Load daily combined sentiment scores for a ticker from MySQL.

    Returns:
        DataFrame with columns: date, sentiment_compound, sentiment_positive,
        sentiment_negative
    """
    db: Session = SessionLocal()
    try:
        rows = (
            db.query(SentimentScore)
            .filter(
                SentimentScore.ticker == ticker,
                SentimentScore.source_type == "combined",
            )
            .order_by(SentimentScore.date)
            .all()
        )

        if not rows:
            logger.warning(f"No sentiment data found for {ticker}")
            return pd.DataFrame()

        data = [{
            "date": r.date,
            "sentiment_compound": r.compound_score,
            "sentiment_positive": r.positive_score,
            "sentiment_negative": r.negative_score,
        } for r in rows]

        return pd.DataFrame(data)

    finally:
        db.close()


def build_feature_matrix(
    ticker: str,
    include_sentiment: bool = False,
    test_ratio: float = 0.2,
) -> tuple:
    """
    Build a complete feature matrix for model training.

    Steps:
      1. Load price data from DB
      2. Compute technical indicators
      3. Optionally merge sentiment scores
      4. Create binary target (next-day UP/DOWN)
      5. Split into train/test (time-based, NOT random)
      6. Return X_train, X_test, y_train, y_test, feature_names

    Args:
        ticker: Stock symbol (e.g. "AAPL")
        include_sentiment: If True, merge sentiment features
        test_ratio: Fraction of data to use as test set (default 20%)

    Returns:
        Tuple of (X_train, X_test, y_train, y_test, feature_names)
    """
    # Step 1: Load price data
    df = load_price_data(ticker)
    if df.empty:
        raise ValueError(f"No price data available for {ticker}")

    # Step 2: Compute technical indicators
    df = compute_indicators(df)

    # Step 3: Optionally merge sentiment
    feature_names = BASELINE_FEATURES.copy()

    if include_sentiment:
        sentiment_df = load_sentiment_data(ticker)
        if not sentiment_df.empty:
            df = df.merge(sentiment_df, on="date", how="left")
            # Forward-fill sentiment on days with no new data
            for col in SENTIMENT_FEATURES:
                if col in df.columns:
                    # Missing history means no observed sentiment, not a missing training row.
                    df[col] = df[col].ffill().fillna(0.0)
            feature_names.extend(SENTIMENT_FEATURES)
            logger.info(f"Merged {len(sentiment_df)} sentiment rows for {ticker}")
        else:
            logger.warning(
                f"No sentiment data for {ticker} — using price features only"
            )

    # Step 4: Create target label
    # 1 if tomorrow's close > today's close, else 0
    df["target"] = (df["close"].shift(-1) > df["close"]).astype(int)

    # Drop the last row (no next-day data for target)
    df = df.iloc[:-1]

    # Step 5: Drop rows with NaN in features or target
    cols_needed = feature_names + ["target"]
    available_features = [f for f in feature_names if f in df.columns]
    cols_needed = available_features + ["target"]

    df_clean = df.dropna(subset=cols_needed)

    if len(df_clean) < 50:
        raise ValueError(
            f"Only {len(df_clean)} clean rows for {ticker} — need at least 50"
        )

    logger.info(
        f"Feature matrix: {len(df_clean)} rows, "
        f"{len(available_features)} features for {ticker}"
    )

    # Step 6: Time-based train/test split (NO random shuffle!)
    # This is critical for time-series — we train on past, test on future
    split_idx = int(len(df_clean) * (1 - test_ratio))

    X = df_clean[available_features].values
    y = df_clean["target"].values

    X_train = X[:split_idx]
    X_test = X[split_idx:]
    y_train = y[:split_idx]
    y_test = y[split_idx:]

    logger.info(
        f"Split: {len(X_train)} train / {len(X_test)} test rows "
        f"(ratio: {test_ratio})"
    )

    return X_train, X_test, y_train, y_test, available_features


def build_feature_dataframe(
    ticker: str,
    include_sentiment: bool = False,
) -> tuple[pd.DataFrame, list[str]]:
    """
    Build a clean DataFrame containing dates, features, and target without splitting.
    Used for chronological walk-forward validation and date-aware training.

    Returns:
        Tuple of (df_clean, feature_names)
    """
    df = load_price_data(ticker)
    if df.empty:
        raise ValueError(f"No price data available for {ticker}")

    df = compute_indicators(df)
    feature_names = BASELINE_FEATURES.copy()

    if include_sentiment:
        sentiment_df = load_sentiment_data(ticker)
        if not sentiment_df.empty:
            df = df.merge(sentiment_df, on="date", how="left")
            for col in SENTIMENT_FEATURES:
                if col in df.columns:
                    df[col] = df[col].ffill().fillna(0.0)
            feature_names.extend(SENTIMENT_FEATURES)

    # Next-day direction target
    df["target"] = (df["close"].shift(-1) > df["close"]).astype(int)
    df = df.iloc[:-1]

    available_features = [f for f in feature_names if f in df.columns]
    cols_needed = ["date", "target"] + available_features

    df_clean = df.dropna(subset=cols_needed).reset_index(drop=True)
    if len(df_clean) < 50:
        raise ValueError(f"Only {len(df_clean)} clean rows for {ticker} — need at least 50")

    return df_clean, available_features


def build_aligned_paired_matrices(
    ticker: str,
    test_ratio: float = 0.2,
) -> dict:
    """
    Build baseline (price-only) and sentiment-augmented feature matrices
    guaranteed to share the EXACT same rows, labels, dates, and test boundaries.

    Returns:
        Dict with keys:
          X_train_base, X_test_base, X_train_sent, X_test_sent,
          y_train, y_test, train_dates, test_dates,
          baseline_features, sentiment_features
    """
    df_sent, sent_features = build_feature_dataframe(ticker, include_sentiment=True)
    base_features = [f for f in BASELINE_FEATURES if f in df_sent.columns]

    split_idx = int(len(df_sent) * (1 - test_ratio))

    y = df_sent["target"].values
    dates = df_sent["date"].values

    return {
        "X_train_base": df_sent[base_features].values[:split_idx],
        "X_test_base": df_sent[base_features].values[split_idx:],
        "X_train_sent": df_sent[sent_features].values[:split_idx],
        "X_test_sent": df_sent[sent_features].values[split_idx:],
        "y_train": y[:split_idx],
        "y_test": y[split_idx:],
        "train_dates": dates[:split_idx],
        "test_dates": dates[split_idx:],
        "baseline_features": base_features,
        "sentiment_features": sent_features,
    }


def build_multi_ticker_matrix(
    tickers: list[str],
    include_sentiment: bool = False,
    test_ratio: float = 0.2,
) -> tuple:
    """
    Build a combined feature matrix across multiple tickers.
    Splits along aligned date boundaries to minimize cross-sectional temporal leakage.

    Returns:
        Tuple of (X_train, X_test, y_train, y_test, feature_names)
    """
    ticker_dfs = []
    feature_names = None

    for ticker in tickers:
        try:
            df, feats = build_feature_dataframe(ticker, include_sentiment=include_sentiment)
            df["ticker"] = ticker
            ticker_dfs.append(df)
            if feature_names is None:
                feature_names = feats
        except ValueError as e:
            logger.warning(f"Skipping {ticker}: {e}")

    if not ticker_dfs:
        raise ValueError("No valid data for any ticker")

    # Determine global split date based on 80th percentile of all dates
    combined_dates = np.concatenate([df["date"].values for df in ticker_dfs])
    global_split_date = pd.Series(combined_dates).quantile(1 - test_ratio)

    all_X_train, all_X_test = [], []
    all_y_train, all_y_test = [], []

    for df in ticker_dfs:
        train_mask = df["date"] < global_split_date
        test_mask = df["date"] >= global_split_date

        if train_mask.sum() > 10 and test_mask.sum() > 5:
            all_X_train.append(df.loc[train_mask, feature_names].values)
            all_X_test.append(df.loc[test_mask, feature_names].values)
            all_y_train.append(df.loc[train_mask, "target"].values)
            all_y_test.append(df.loc[test_mask, "target"].values)

    return (
        np.vstack(all_X_train),
        np.vstack(all_X_test),
        np.concatenate(all_y_train),
        np.concatenate(all_y_test),
        feature_names,
    )

