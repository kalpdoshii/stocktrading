"""
news_fetcher.py — News Headlines via NewsAPI
==============================================
Fetches recent news headlines for each ticker using the NewsAPI.
Stores results in the `news_headlines` MySQL table.

Note: The free tier of NewsAPI limits to 100 requests/day and
only returns articles from the last 30 days.

Usage:
    from app.data_pipeline.news_fetcher import fetch_news
    fetch_news(["AAPL", "GOOGL"])
    fetch_news()  # all configured tickers
"""

import logging
from datetime import datetime, timedelta

from newsapi import NewsApiClient
from sqlalchemy.orm import Session

from app.config import NEWSAPI_KEY, TICKERS
from app.database import SessionLocal
from app.models import NewsHeadline
from app.stock_universe import TICKER_METADATA

logger = logging.getLogger(__name__)

# Legacy aliases kept for non-Indian symbols supplied explicitly.
TICKER_TO_COMPANY = {
    "AAPL": "Apple",
    "GOOGL": "Google OR Alphabet",
    "MSFT": "Microsoft",
    "TSLA": "Tesla",
    "AMZN": "Amazon",
    "META": "Meta OR Facebook",
    "NVDA": "NVIDIA",
    "JPM": "JPMorgan",
}


def build_news_query(ticker: str) -> str:
    """Build a company-focused query for NewsAPI."""
    metadata = TICKER_METADATA.get(ticker)
    if metadata:
        # Include India to reduce unrelated international company results.
        return f'"{metadata["name"]}" AND India'
    return TICKER_TO_COMPANY.get(ticker, ticker.removesuffix(".NS"))


def fetch_news(tickers: list[str] | None = None, days_back: int = 30) -> dict:
    """
    Fetch news headlines for each ticker and store in MySQL.

    Args:
        tickers: List of stock symbols. Defaults to config.TICKERS.
        days_back: How many days of news to fetch (max 30 on free tier).

    Returns:
        dict: {ticker: number_of_headlines_stored} summary.
    """
    if not NEWSAPI_KEY:
        logger.error("NEWSAPI_KEY not set in .env — skipping news fetch")
        return {}

    tickers = tickers or TICKERS
    newsapi = NewsApiClient(api_key=NEWSAPI_KEY)

    # Free tier only goes back 30 days
    from_date = (datetime.now() - timedelta(days=min(days_back, 30))).strftime("%Y-%m-%d")
    to_date = datetime.now().strftime("%Y-%m-%d")

    logger.info(
        f"Fetching news for {len(tickers)} tickers "
        f"from {from_date} to {to_date}"
    )

    results = {}
    db: Session = SessionLocal()

    try:
        for ticker in tickers:
            try:
                # Use company name for search if available, else ticker symbol
                query = build_news_query(ticker)

                logger.info(f"  Searching news for {ticker} (query: '{query}')...")

                # Fetch articles from NewsAPI
                response = newsapi.get_everything(
                    q=query,
                    from_param=from_date,
                    to=to_date,
                    language="en",
                    sort_by="publishedAt",
                    page_size=50,  # max per request
                )

                articles = response.get("articles", [])
                headlines_stored = 0

                for article in articles:
                    headline_text = article.get("title", "")

                    # Skip empty or "[Removed]" headlines
                    if not headline_text or headline_text == "[Removed]":
                        continue

                    # Parse the published date
                    published_str = article.get("publishedAt", "")
                    published_at = None
                    if published_str:
                        try:
                            published_at = datetime.fromisoformat(
                                published_str.replace("Z", "+00:00")
                            )
                        except ValueError:
                            pass

                    # Check if this headline already exists (avoid duplicates)
                    existing = db.query(NewsHeadline).filter(
                        NewsHeadline.ticker == ticker,
                        NewsHeadline.headline == headline_text,
                        NewsHeadline.published_at == published_at,
                    ).first()

                    if existing:
                        continue

                    # Insert new headline
                    headline = NewsHeadline(
                        ticker=ticker,
                        headline=headline_text,
                        source=article.get("source", {}).get("name", "Unknown"),
                        url=article.get("url", ""),
                        published_at=published_at,
                    )
                    db.add(headline)
                    headlines_stored += 1

                db.commit()
                results[ticker] = headlines_stored
                logger.info(f"  {ticker}: {headlines_stored} new headlines stored")

            except Exception as e:
                logger.error(f"  Error fetching news for {ticker}: {e}")
                db.rollback()
                results[ticker] = 0

    finally:
        db.close()

    logger.info(f"News fetch complete. Summary: {results}")
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    fetch_news()
