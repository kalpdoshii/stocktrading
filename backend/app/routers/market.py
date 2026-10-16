"""Indian market overview API endpoints."""

from datetime import date
from collections import defaultdict

import yfinance as yf
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import TICKERS
from app.database import get_db
from app.models import PriceData, StockMetadata

router = APIRouter(tags=["Market"])


@router.get("/market-overview")
def get_market_overview(db: Session = Depends(get_db)):
    """Return Nifty 50 status, data coverage, and daily movers."""
    movers = []
    available_tickers = {
        ticker
        for (ticker,) in db.query(PriceData.ticker)
        .filter(PriceData.ticker.in_(TICKERS))
        .distinct()
        .all()
    }
    for ticker in TICKERS:
        rows = (
            db.query(PriceData)
            .filter(PriceData.ticker == ticker)
            .order_by(PriceData.date.desc())
            .limit(2)
            .all()
        )
        if len(rows) < 2 or not rows[0].close or not rows[1].close:
            continue

        latest = float(rows[0].close)
        previous = float(rows[1].close)
        change_pct = (latest / previous - 1) * 100
        metadata = db.get(StockMetadata, ticker)
        movers.append({
            "ticker": ticker,
            "name": metadata.name if metadata else ticker,
            "sector": metadata.sector if metadata else None,
            "price": round(latest, 2),
            "change_pct": round(change_pct, 2),
            "date": str(rows[0].date),
        })

    movers.sort(key=lambda item: item["change_pct"], reverse=True)
    sector_values = defaultdict(list)
    for mover in movers:
        if mover["sector"]:
            sector_values[mover["sector"]].append(mover["change_pct"])
    sector_performance = sorted(
        [
            {
                "sector": sector,
                "change_pct": round(sum(values) / len(values), 2),
                "stocks": len(values),
            }
            for sector, values in sector_values.items()
        ],
        key=lambda item: item["change_pct"],
        reverse=True,
    )
    nifty = _get_nifty_status()

    return {
        "as_of": str(date.today()),
        "coverage": {
            "configured": len(TICKERS),
            "available": len(available_tickers),
            "movers": len(movers),
        },
        "nifty50": nifty,
        "top_gainers": movers[:5],
        "top_losers": list(reversed(movers[-5:])),
        "sector_performance": sector_performance,
    }


def _get_nifty_status() -> dict | None:
    """Fetch the latest Nifty 50 index move from Yahoo Finance."""
    try:
        prices = yf.download(
            "^NSEI",
            period="5d",
            progress=False,
            auto_adjust=False,
        )
        if prices.empty:
            return None
        close = prices["Close"]
        if hasattr(close, "iloc") and len(getattr(close, "shape", ())) > 1:
            close = close.iloc[:, 0]
        if len(close) < 2:
            return None
        latest = float(close.iloc[-1])
        previous = float(close.iloc[-2])
        return {
            "value": round(latest, 2),
            "change_pct": round((latest / previous - 1) * 100, 2),
            "date": str(prices.index[-1].date()),
        }
    except Exception:
        return None
