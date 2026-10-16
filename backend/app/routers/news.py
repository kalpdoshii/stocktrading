"""News headline API endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import TICKERS
from app.database import get_db
from app.models import NewsHeadline, StockMetadata

router = APIRouter(tags=["News"])


@router.get("/market-news")
def get_market_news(limit: int = 12, db: Session = Depends(get_db)):
    """Return the latest stored headlines for configured Indian stocks."""
    safe_limit = max(1, min(limit, 50))
    headlines = (
        db.query(NewsHeadline)
        .filter(NewsHeadline.ticker.in_(TICKERS))
        .order_by(NewsHeadline.published_at.desc())
        .limit(safe_limit)
        .all()
    )

    items = []
    for headline in headlines:
        metadata = db.get(StockMetadata, headline.ticker)
        items.append({
            "ticker": headline.ticker,
            "name": metadata.name if metadata else headline.ticker,
            "sector": metadata.sector if metadata else None,
            "headline": headline.headline,
            "source": headline.source,
            "url": headline.url,
            "published_at": headline.published_at.isoformat() if headline.published_at else None,
        })

    return {"count": len(items), "items": items}
