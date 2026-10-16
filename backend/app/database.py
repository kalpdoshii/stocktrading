"""
database.py — MySQL Database Connection
=========================================
Sets up SQLAlchemy engine and session factory for MySQL.
All modules import `get_db()` or `SessionLocal` from here.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import DATABASE_URL

# Create the SQLAlchemy engine
# - pool_recycle=3600: reconnect after 1 hour (avoids MySQL timeout)
# - echo=False: set to True for SQL debug logging
engine = create_engine(
    DATABASE_URL,
    pool_recycle=3600,
    echo=False,
)

# Session factory — each call to SessionLocal() gives a new DB session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for ORM models
Base = declarative_base()


def get_db():
    """
    Dependency for FastAPI routes — yields a DB session and
    ensures it's closed after the request finishes.

    Usage in a route:
        @router.get("/example")
        def example(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Create all tables defined in models.py.
    Called once at startup if tables don't exist yet.
    """
    # Import models so they register with Base.metadata
    import app.models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    sync_stock_metadata()


def sync_stock_metadata():
    """Insert or update metadata for the configured Indian stock universe."""
    from app.models import StockMetadata
    from app.stock_universe import NIFTY_50

    db = SessionLocal()
    try:
        for stock in NIFTY_50:
            record = db.get(StockMetadata, stock["ticker"])
            values = {
                "name": stock["name"],
                "sector": stock["sector"],
                "index_name": stock["index"],
                "exchange": "NSE",
                "currency": "INR",
                "is_active": 1,
            }
            if record is None:
                db.add(StockMetadata(ticker=stock["ticker"], **values))
            else:
                for key, value in values.items():
                    setattr(record, key, value)
        db.commit()
    finally:
        db.close()
