"""
main.py — FastAPI Application Entry Point
============================================
Sets up the FastAPI app with CORS, database initialization,
and API router mounting.

Run with:
    uvicorn app.main:app --reload --port 8000
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.routers import tickers, predictions, sentiment, reasoning, backtest, market, news, operations
from app.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events: create tables and start background scheduler on startup, stop on shutdown."""
    init_db()
    start_scheduler()
    yield
    stop_scheduler()


# ---- Create FastAPI app ----
app = FastAPI(
    title="StockTrading",
    description=(
        "Stock trend prediction with sentiment analysis "
        "and LLM-powered explanations."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ---- CORS — allow React frontend to call the API ----
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server default
        "http://localhost:5174",  # Vite fallback port
        "http://localhost:5175",
        "http://localhost:3000",  # alternative React port
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---- Health check endpoint ----
@app.get("/api/health")
def health_check():
    """Simple health check to verify the API is running."""
    return {"status": "ok", "message": "StockTrading API is running"}


# ---- Mount all API routers ----
app.include_router(tickers.router, prefix="/api")
app.include_router(predictions.router, prefix="/api")
app.include_router(sentiment.router, prefix="/api")
app.include_router(reasoning.router, prefix="/api")
app.include_router(backtest.router, prefix="/api")
app.include_router(market.router, prefix="/api")
app.include_router(news.router, prefix="/api")
app.include_router(operations.router, prefix="/api")
