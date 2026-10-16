"""
tickers.py — Ticker and Price Data API Endpoints
====================================================
GET /api/tickers         → list of available tickers
GET /api/price/{ticker}  → OHLCV data + indicators for a ticker
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import PriceData, StockMetadata
from app.config import TICKERS
from app.features.technical import compute_indicators

import pandas as pd

router = APIRouter(tags=["Tickers"])


@router.get("/tickers")
def list_tickers(db: Session = Depends(get_db)):
    """Return list of configured tickers with data availability info."""
    ticker_info = []
    for ticker in TICKERS:
        # Get date range and count from DB
        stats = db.query(
            func.count(PriceData.id),
            func.min(PriceData.date),
            func.max(PriceData.date),
        ).filter(PriceData.ticker == ticker).first()

        count, min_date, max_date = stats
        metadata = db.get(StockMetadata, ticker)
        ticker_info.append({
            "ticker": ticker,
            "name": metadata.name if metadata else ticker,
            "sector": metadata.sector if metadata else None,
            "index": metadata.index_name if metadata else None,
            "exchange": metadata.exchange if metadata else None,
            "currency": metadata.currency if metadata else None,
            "is_active": bool(metadata.is_active) if metadata else False,
            "status": "available" if count else "unavailable",
            "data_points": count,
            "start_date": str(min_date) if min_date else None,
            "end_date": str(max_date) if max_date else None,
        })

    return {"tickers": ticker_info}


@router.get("/price/{ticker}")
def get_price_data(
    ticker: str,
    limit: int = 365,
    db: Session = Depends(get_db),
):
    """
    Get OHLCV price data with technical indicators for a ticker.

    Args:
        ticker: Stock symbol (e.g. AAPL)
        limit: Max number of data points to return (default 365)
    """
    ticker = ticker.upper()

    if ticker not in TICKERS:
        raise HTTPException(status_code=404, detail=f"Ticker '{ticker}' not configured")

    rows = (
        db.query(PriceData)
        .filter(PriceData.ticker == ticker)
        .order_by(PriceData.date.desc())
        .limit(limit)
        .all()
    )

    if not rows:
        raise HTTPException(status_code=404, detail=f"No price data for {ticker}")

    # Convert to DataFrame for indicator computation
    data = [{
        "date": r.date,
        "open": float(r.open) if r.open else None,
        "high": float(r.high) if r.high else None,
        "low": float(r.low) if r.low else None,
        "close": float(r.close) if r.close else None,
        "adj_close": float(r.adj_close) if r.adj_close else None,
        "volume": int(r.volume) if r.volume else None,
    } for r in rows]

    df = pd.DataFrame(data).sort_values("date")

    # Compute indicators
    df = compute_indicators(df)

    # Convert back to list of dicts, replacing NaN with None
    result = df.astype(object).where(pd.notna(df), None).to_dict(orient="records")

    # Convert dates to strings for JSON serialization
    for r in result:
        r["date"] = str(r["date"])

    return {"ticker": ticker, "data": result, "count": len(result)}
