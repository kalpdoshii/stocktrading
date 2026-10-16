"""
refresh.py — Daily Data Refresh Orchestrator
===============================================
Runs all three data fetchers in sequence:
  1. Price data (yfinance)
  2. News headlines (NewsAPI)
  3. Reddit posts (PRAW)

Designed to be called once daily. Safe to re-run — all fetchers
handle duplicates gracefully.

Usage:
    from app.data_pipeline.refresh import run_full_refresh
    run_full_refresh()
"""

import logging
from datetime import datetime

from app.data_pipeline.price_fetcher import fetch_prices
from app.data_pipeline.news_fetcher import fetch_news
from app.data_pipeline.reddit_fetcher import fetch_reddit

logger = logging.getLogger(__name__)


def run_full_refresh(tickers: list[str] | None = None) -> dict:
    """
    Execute the full data pipeline: prices → news → reddit.

    Args:
        tickers: Optional list of tickers to fetch. Uses config defaults if None.

    Returns:
        dict: Combined results from all three fetchers.
    """
    start_time = datetime.now()
    logger.info("=" * 60)
    logger.info(f"Starting full data refresh at {start_time}")
    logger.info("=" * 60)

    all_results = {}

    # Step 1: Fetch price data (always works, no API key needed)
    logger.info("\n--- Step 1/3: Fetching price data ---")
    try:
        price_results = fetch_prices(tickers)
        all_results["prices"] = price_results
    except Exception as e:
        logger.error(f"Price fetch failed: {e}")
        all_results["prices"] = {"error": str(e)}

    # Step 2: Fetch news headlines
    logger.info("\n--- Step 2/3: Fetching news headlines ---")
    try:
        news_results = fetch_news(tickers)
        all_results["news"] = news_results
    except Exception as e:
        logger.error(f"News fetch failed: {e}")
        all_results["news"] = {"error": str(e)}

    # Step 3: Fetch Reddit posts
    logger.info("\n--- Step 3/3: Fetching Reddit posts ---")
    try:
        reddit_results = fetch_reddit(tickers)
        all_results["reddit"] = reddit_results
    except Exception as e:
        logger.error(f"Reddit fetch failed: {e}")
        all_results["reddit"] = {"error": str(e)}

    # Summary
    elapsed = datetime.now() - start_time
    logger.info("=" * 60)
    logger.info(f"Full refresh complete in {elapsed.total_seconds():.1f}s")
    logger.info(f"Results: {all_results}")
    logger.info("=" * 60)

    return all_results
