"""
price_fetcher.py — Historical Stock Price Data
================================================
Fetches OHLCV data from Yahoo Finance using yfinance.
Stores results in the `price_data` MySQL table.

Usage:
    from app.data_pipeline.price_fetcher import fetch_prices
    fetch_prices(["AAPL", "GOOGL"])  # fetches for specific tickers
    fetch_prices()                    # fetches for all configured tickers
"""

import logging
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.orm import Session

from app.config import TICKERS, PRICE_HISTORY_YEARS
from app.database import SessionLocal
from app.models import PriceData

logger = logging.getLogger(__name__)


def fetch_prices(tickers: list[str] | None = None, years: int | None = None) -> dict:
    """
    Fetch historical OHLCV data for each ticker and store in MySQL.

    Args:
        tickers: List of stock symbols. Defaults to config.TICKERS.
        years: How many years of history to fetch. Defaults to config setting.

    Returns:
        dict: {ticker: number_of_rows_inserted} summary.
    """
    tickers = tickers or TICKERS
    years = years or PRICE_HISTORY_YEARS

    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=years * 365)

    logger.info(
        f"Fetching price data for {len(tickers)} tickers "
        f"from {start_date.date()} to {end_date.date()}"
    )

    results = {}
    db: Session = SessionLocal()

    try:
        for ticker in tickers:
            try:
                logger.info(f"  Downloading {ticker}...")

                # Download OHLCV data from Yahoo Finance
                df = yf.download(
                    ticker,
                    start=start_date.strftime("%Y-%m-%d"),
                    end=end_date.strftime("%Y-%m-%d"),
                    progress=False,  # suppress progress bar
                )

                if df.empty:
                    logger.warning(f"  No data returned for {ticker}")
                    results[ticker] = 0
                    continue

                # Flatten multi-level columns if present (yfinance sometimes returns these)
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)

                # Reset index to get Date as a column
                df = df.reset_index()

                # Prepare rows for insertion
                rows_inserted = 0
                for _, row in df.iterrows():
                    # Use MySQL INSERT ... ON DUPLICATE KEY UPDATE to handle re-runs
                    stmt = mysql_insert(PriceData).values(
                        ticker=ticker,
                        date=row["Date"].date() if hasattr(row["Date"], "date") else row["Date"],
                        open=float(row["Open"]) if pd.notna(row["Open"]) else None,
                        high=float(row["High"]) if pd.notna(row["High"]) else None,
                        low=float(row["Low"]) if pd.notna(row["Low"]) else None,
                        close=float(row["Close"]) if pd.notna(row["Close"]) else None,
                        adj_close=float(row.get("Adj Close", row["Close"])) if pd.notna(row["Close"]) else None,
                        volume=int(row["Volume"]) if pd.notna(row["Volume"]) else None,
                    )
                    # On duplicate (ticker, date), update the price values
                    stmt = stmt.on_duplicate_key_update(
                        open=stmt.inserted.open,
                        high=stmt.inserted.high,
                        low=stmt.inserted.low,
                        close=stmt.inserted.close,
                        adj_close=stmt.inserted.adj_close,
                        volume=stmt.inserted.volume,
                    )
                    db.execute(stmt)
                    rows_inserted += 1

                db.commit()
                results[ticker] = rows_inserted
                logger.info(f"  {ticker}: {rows_inserted} rows stored")

            except Exception as e:
                logger.error(f"  Error fetching {ticker}: {e}")
                db.rollback()
                results[ticker] = 0

    finally:
        db.close()

    logger.info(f"Price fetch complete. Summary: {results}")
    return results


if __name__ == "__main__":
    # Quick test: run directly with `python -m app.data_pipeline.price_fetcher`
    logging.basicConfig(level=logging.INFO)
    fetch_prices()
