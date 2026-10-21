"""
run_pipeline.py — CLI Entry Point for the Data Pipeline
=========================================================
Run from the backend directory:
    python -m scripts.run_pipeline              # full refresh (all tickers)
    python -m scripts.run_pipeline --tickers AAPL TSLA
    python -m scripts.run_pipeline --prices-only
    python -m scripts.run_pipeline --news-only
    python -m scripts.run_pipeline --reddit-only
"""

import argparse
import logging
import sys
import os

# Add the backend directory to the Python path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import init_db
from app.data_pipeline.refresh import run_full_refresh
from app.data_pipeline.price_fetcher import fetch_prices
from app.data_pipeline.news_fetcher import fetch_news
from app.data_pipeline.reddit_fetcher import fetch_reddit
from app.sentiment.aggregator import aggregate_sentiment


def main():
    parser = argparse.ArgumentParser(
        description="AI Trading Assistant — Data Pipeline"
    )
    parser.add_argument(
        "--tickers",
        nargs="+",
        help="Specific tickers to fetch (e.g. AAPL TSLA). Default: all configured.",
    )
    parser.add_argument(
        "--prices-only",
        action="store_true",
        help="Only fetch price data (yfinance).",
    )
    parser.add_argument(
        "--news-only",
        action="store_true",
        help="Only fetch news headlines (NewsAPI).",
    )
    parser.add_argument(
        "--reddit-only",
        action="store_true",
        help="Only fetch Reddit posts (PRAW).",
    )
    parser.add_argument(
        "--sentiment-only",
        action="store_true",
        help="Aggregate FinBERT sentiment from stored news and Reddit text.",
    )
    parser.add_argument(
        "--init-db",
        action="store_true",
        help="Initialize database tables before fetching.",
    )

    args = parser.parse_args()

    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Optionally create tables
    if args.init_db:
        logging.info("Initializing database tables...")
        init_db()
        logging.info("Database tables created successfully.")

    tickers = args.tickers if args.tickers else None

    # Run specific pipeline or full refresh
    if args.prices_only:
        fetch_prices(tickers)
    elif args.news_only:
        fetch_news(tickers)
    elif args.reddit_only:
        fetch_reddit(tickers)
    elif args.sentiment_only:
        aggregate_sentiment(tickers)
    else:
        run_full_refresh(tickers)

    print("\n[OK] Pipeline complete!")


if __name__ == "__main__":
    main()
