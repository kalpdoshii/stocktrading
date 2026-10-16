"""
aggregator.py — Daily Sentiment Score Aggregation
====================================================
Pulls news headlines and Reddit posts from MySQL, runs FinBERT on them,
and computes daily aggregated sentiment scores per ticker.

Stores three rows per ticker/date:
  - source_type='news'     → sentiment from news headlines only
  - source_type='reddit'   → sentiment from Reddit posts only
  - source_type='combined' → weighted average of both

Usage:
    from app.sentiment.aggregator import aggregate_sentiment
    aggregate_sentiment(["AAPL", "TSLA"])
    aggregate_sentiment()  # all configured tickers
"""

import logging
from collections import defaultdict
from datetime import date

import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy.dialects.mysql import insert as mysql_insert

from app.config import TICKERS
from app.database import SessionLocal
from app.models import NewsHeadline, RedditPost, SentimentScore
from app.sentiment.analyzer import analyze_sentiment

logger = logging.getLogger(__name__)


def aggregate_sentiment(tickers: list[str] | None = None) -> dict:
    """
    Compute daily aggregated sentiment for each ticker.

    Process:
      1. Fetch all news headlines and Reddit posts from DB
      2. Group by (ticker, date)
      3. Run FinBERT on each group
      4. Average the scores to get daily sentiment
      5. Store news, reddit, and combined scores in sentiment_scores table

    Args:
        tickers: List of tickers. Defaults to all configured.

    Returns:
        dict: {ticker: number_of_days_scored}
    """
    tickers = tickers or TICKERS
    results = {}

    db: Session = SessionLocal()
    try:
        for ticker in tickers:
            logger.info(f"Aggregating sentiment for {ticker}...")

            # ---- Collect texts by date ----
            news_by_date = _get_news_by_date(db, ticker)
            reddit_by_date = _get_reddit_by_date(db, ticker)

            # Get all dates that have any data
            all_dates = sorted(
                set(news_by_date.keys()) | set(reddit_by_date.keys())
            )

            if not all_dates:
                logger.warning(f"  No text data found for {ticker}")
                results[ticker] = 0
                continue

            days_scored = 0

            for d in all_dates:
                news_texts = news_by_date.get(d, [])
                reddit_texts = reddit_by_date.get(d, [])

                # ---- Score news headlines ----
                news_scores = None
                if news_texts:
                    sentiments = analyze_sentiment(news_texts)
                    news_scores = _average_scores(sentiments)
                    _upsert_score(db, ticker, d, "news", news_scores, len(news_texts))

                # ---- Score Reddit posts ----
                reddit_scores = None
                if reddit_texts:
                    sentiments = analyze_sentiment(reddit_texts)
                    reddit_scores = _average_scores(sentiments)
                    _upsert_score(db, ticker, d, "reddit", reddit_scores, len(reddit_texts))

                # ---- Combined score (weighted average) ----
                # Weight: 60% news, 40% reddit (news is generally more reliable)
                combined = _combine_scores(news_scores, reddit_scores)
                if combined:
                    total_texts = len(news_texts) + len(reddit_texts)
                    _upsert_score(db, ticker, d, "combined", combined, total_texts)
                    days_scored += 1

            db.commit()
            results[ticker] = days_scored
            logger.info(f"  {ticker}: scored {days_scored} days")

    except Exception as e:
        logger.error(f"Sentiment aggregation error: {e}")
        db.rollback()
    finally:
        db.close()

    logger.info(f"Sentiment aggregation complete: {results}")
    return results


def _get_news_by_date(db: Session, ticker: str) -> dict:
    """Group news headlines by date for a ticker."""
    headlines = (
        db.query(NewsHeadline)
        .filter(NewsHeadline.ticker == ticker)
        .order_by(NewsHeadline.published_at)
        .all()
    )

    by_date = defaultdict(list)
    for h in headlines:
        if h.published_at and h.headline:
            d = h.published_at.date() if hasattr(h.published_at, "date") else h.published_at
            by_date[d].append(h.headline)

    return dict(by_date)


def _get_reddit_by_date(db: Session, ticker: str) -> dict:
    """Group Reddit posts/comments by date for a ticker."""
    posts = (
        db.query(RedditPost)
        .filter(RedditPost.ticker == ticker)
        .order_by(RedditPost.created_utc)
        .all()
    )

    by_date = defaultdict(list)
    for p in posts:
        if p.created_utc:
            d = p.created_utc.date() if hasattr(p.created_utc, "date") else p.created_utc
            # Use title + body for posts, just body for comments
            text = ""
            if p.title:
                text += p.title + ". "
            if p.body:
                text += p.body
            text = text.strip()
            if text:
                by_date[d].append(text[:500])  # truncate for FinBERT's 512 token limit

    return dict(by_date)


def _average_scores(sentiments: list[dict]) -> dict:
    """Average a list of FinBERT sentiment dicts into one score."""
    if not sentiments:
        return None

    return {
        "positive": float(np.mean([s["positive"] for s in sentiments])),
        "negative": float(np.mean([s["negative"] for s in sentiments])),
        "neutral": float(np.mean([s["neutral"] for s in sentiments])),
        "compound": float(np.mean([s["compound"] for s in sentiments])),
    }


def _combine_scores(
    news_scores: dict | None,
    reddit_scores: dict | None,
    news_weight: float = 0.6,
) -> dict | None:
    """
    Weighted combination of news and Reddit sentiment scores.
    If only one source is available, use it entirely.
    """
    if news_scores and reddit_scores:
        reddit_weight = 1 - news_weight
        return {
            key: news_scores[key] * news_weight + reddit_scores[key] * reddit_weight
            for key in ["positive", "negative", "neutral", "compound"]
        }
    elif news_scores:
        return news_scores
    elif reddit_scores:
        return reddit_scores
    return None


def _upsert_score(
    db: Session,
    ticker: str,
    d: date,
    source_type: str,
    scores: dict,
    sample_count: int,
) -> None:
    """Insert or update a sentiment score row."""
    stmt = mysql_insert(SentimentScore).values(
        ticker=ticker,
        date=d,
        source_type=source_type,
        positive_score=scores["positive"],
        negative_score=scores["negative"],
        neutral_score=scores["neutral"],
        compound_score=scores["compound"],
        sample_count=sample_count,
    )
    stmt = stmt.on_duplicate_key_update(
        positive_score=stmt.inserted.positive_score,
        negative_score=stmt.inserted.negative_score,
        neutral_score=stmt.inserted.neutral_score,
        compound_score=stmt.inserted.compound_score,
        sample_count=stmt.inserted.sample_count,
    )
    db.execute(stmt)
