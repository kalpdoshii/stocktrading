"""
main.py — FastAPI Application Entry Point
============================================
Sets up the FastAPI app with CORS, database initialization,
and API router mounting.

Run with:
    uvicorn app.main:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.routers import tickers, predictions, sentiment, reasoning, backtest, market, news, operations
from app.scheduler import start_scheduler, stop_scheduler

# ---- Create FastAPI app ----
app = FastAPI(
    title="AI Trading Assistant",
    description=(
        "Stock trend prediction with sentiment analysis "
        "and LLM-powered explanations."
    ),
    version="1.0.0",
)

# ---- CORS — allow React frontend to call the API ----
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # alternative React port
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---- Startup event — init DB tables ----
@app.on_event("startup")
def on_startup():
    """Create database tables on first run (safe to call multiple times)."""
    init_db()
    start_scheduler()


@app.on_event("shutdown")
def on_shutdown():
    """Stop the optional scheduler during application shutdown."""
    stop_scheduler()


# ---- Health check endpoint ----
@app.get("/api/health")
def health_check():
    """Simple health check to verify the API is running."""
    return {"status": "ok", "message": "AI Trading Assistant API is running"}


# ---- Mount all API routers ----
app.include_router(tickers.router, prefix="/api")
app.include_router(predictions.router, prefix="/api")
app.include_router(sentiment.router, prefix="/api")
app.include_router(reasoning.router, prefix="/api")
app.include_router(backtest.router, prefix="/api")
app.include_router(market.router, prefix="/api")
app.include_router(news.router, prefix="/api")
app.include_router(operations.router, prefix="/api")
