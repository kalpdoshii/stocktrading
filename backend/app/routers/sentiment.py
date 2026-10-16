"""
sentiment.py — Sentiment API Endpoints
==========================================
GET /api/sentiment/{ticker}  → latest sentiment scores for a ticker
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import TICKERS
from app.models import SentimentScore

router = APIRouter(tags=["Sentiment"])


@router.get("/sentiment/{ticker}")
def get_sentiment(ticker: str, days: int = 30, db: Session = Depends(get_db)):
    """
    Get sentiment data for a ticker.

    Returns the latest combined sentiment score and a history
    of daily scores for the chart.

    Args:
        ticker: Stock symbol
        days: How many days of history to return (default 30)
    """
    ticker = ticker.upper()

    if ticker not in TICKERS:
        raise HTTPException(status_code=404, detail=f"Ticker '{ticker}' not configured")

    # Get latest combined sentiment
    latest = (
        db.query(SentimentScore)
        .filter(
            SentimentScore.ticker == ticker,
            SentimentScore.source_type == "combined",
        )
        .order_by(SentimentScore.date.desc())
        .first()
    )

    # Get sentiment history
    history = (
        db.query(SentimentScore)
        .filter(
            SentimentScore.ticker == ticker,
            SentimentScore.source_type == "combined",
        )
        .order_by(SentimentScore.date.desc())
        .limit(days)
        .all()
    )

    latest_data = None
    if latest:
        latest_data = {
            "date": str(latest.date),
            "compound_score": latest.compound_score,
            "positive_score": latest.positive_score,
            "negative_score": latest.negative_score,
            "neutral_score": latest.neutral_score,
            "sample_count": latest.sample_count,
            "interpretation": _interpret_sentiment(latest.compound_score),
        }

    history_data = [{
        "date": str(s.date),
        "compound_score": s.compound_score,
        "positive_score": s.positive_score,
        "negative_score": s.negative_score,
        "sample_count": s.sample_count,
    } for s in reversed(history)]  # reverse to get chronological order

    return {
        "ticker": ticker,
        "latest": latest_data,
        "history": history_data,
    }


def _interpret_sentiment(score: float | None) -> str:
    """Convert compound score to a human-readable interpretation."""
    if score is None:
        return "No data"
    if score > 0.3:
        return "Strongly Positive"
    elif score > 0.1:
        return "Mildly Positive"
    elif score > -0.1:
        return "Neutral"
    elif score > -0.3:
        return "Mildly Negative"
    else:
        return "Strongly Negative"
