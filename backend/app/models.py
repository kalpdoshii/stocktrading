"""
models.py — SQLAlchemy ORM Models
====================================
Defines all 8 database tables as Python classes.
Each class maps directly to a MySQL table from init_db.sql.
"""

from sqlalchemy import (
    Column, Integer, String, Float, Text, Date, DateTime,
    Enum, BigInteger, TIMESTAMP, JSON, UniqueConstraint,
)
from sqlalchemy.sql import func

from app.database import Base


class StockMetadata(Base):
    """Reference metadata for configured stocks."""
    __tablename__ = "stock_metadata"

    ticker    = Column(String(20), primary_key=True)
    name      = Column(String(150), nullable=False)
    sector    = Column(String(100))
    index_name = Column(String(50))
    exchange  = Column(String(10), nullable=False, default="NSE")
    currency  = Column(String(3), nullable=False, default="INR")
    is_active = Column(Integer, nullable=False, default=1)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())


class PriceData(Base):
    """Daily OHLCV price data for each ticker (from yfinance)."""
    __tablename__ = "price_data"

    id        = Column(Integer, primary_key=True, autoincrement=True)
    ticker    = Column(String(20), nullable=False, index=True)
    date      = Column(Date, nullable=False, index=True)
    open      = Column(Float)
    high      = Column(Float)
    low       = Column(Float)
    close     = Column(Float)
    adj_close = Column(Float)
    volume    = Column(BigInteger)
    created_at = Column(TIMESTAMP, server_default=func.now())

    # Composite unique constraint: one row per ticker per day
    __table_args__ = (
        UniqueConstraint("ticker", "date", name="uq_ticker_date"),
        {"mysql_engine": "InnoDB"},
    )


class NewsHeadline(Base):
    """News headlines fetched per ticker (from NewsAPI)."""
    __tablename__ = "news_headlines"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    ticker       = Column(String(20), nullable=False, index=True)
    headline     = Column(Text, nullable=False)
    source       = Column(String(100))
    url          = Column(String(500))
    published_at = Column(DateTime, index=True)
    fetched_at   = Column(TIMESTAMP, server_default=func.now())


class RedditPost(Base):
    """Reddit posts/comments mentioning a ticker (from PRAW)."""
    __tablename__ = "reddit_posts"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    ticker       = Column(String(20), nullable=False, index=True)
    post_id      = Column(String(20), nullable=False)
    subreddit    = Column(String(50))
    title        = Column(Text)
    body         = Column(Text)
    score        = Column(Integer, default=0)
    num_comments = Column(Integer, default=0)
    post_type    = Column(Enum("post", "comment"), default="post")
    created_utc  = Column(DateTime, index=True)
    fetched_at   = Column(TIMESTAMP, server_default=func.now())


class SentimentScore(Base):
    """Daily aggregated sentiment scores from FinBERT analysis."""
    __tablename__ = "sentiment_scores"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    ticker         = Column(String(20), nullable=False)
    date           = Column(Date, nullable=False)
    source_type    = Column(Enum("news", "reddit", "combined"), nullable=False)
    positive_score = Column(Float)
    negative_score = Column(Float)
    neutral_score  = Column(Float)
    compound_score = Column(Float)   # single score from -1 to +1
    sample_count   = Column(Integer)
    created_at     = Column(TIMESTAMP, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("ticker", "date", "source_type", name="uq_ticker_date_src"),
        {"mysql_engine": "InnoDB"},
    )


class Prediction(Base):
    """Model predictions (UP/DOWN/HOLD) for each ticker/date."""
    __tablename__ = "predictions"

    id                    = Column(Integer, primary_key=True, autoincrement=True)
    ticker                = Column(String(20), nullable=False)
    date                  = Column(Date, nullable=False)
    model_version         = Column(String(50), nullable=False)
    signal_dir            = Column(Enum("UP", "DOWN", "HOLD"), nullable=False, default="HOLD")
    confidence            = Column(Float)
    raw_confidence        = Column(Float)
    calibrated_confidence = Column(Float)
    is_calibrated         = Column(Integer, default=0)
    features_json         = Column(JSON)   # top feature values snapshot
    shap_values_json      = Column(JSON)   # SHAP feature attributions
    created_at            = Column(TIMESTAMP, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("ticker", "date", "model_version", name="uq_pred"),
        {"mysql_engine": "InnoDB"},
    )


class LLMCache(Base):
    """Cache for LLM explanations to avoid redundant API calls."""
    __tablename__ = "llm_cache"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    prompt_hash   = Column(String(64), nullable=False, unique=True)
    prompt_text   = Column(Text)
    response_text = Column(Text, nullable=False)
    model_used    = Column(String(50))
    created_at    = Column(TIMESTAMP, server_default=func.now())


class BacktestResult(Base):
    """Results from backtesting a model on historical data."""
    __tablename__ = "backtest_results"

    id                = Column(Integer, primary_key=True, autoincrement=True)
    ticker            = Column(String(20), nullable=False)
    model_version     = Column(String(50), nullable=False)
    start_date        = Column(Date)
    end_date          = Column(Date)
    total_trades      = Column(Integer)
    winning_trades    = Column(Integer)
    losing_trades     = Column(Integer)
    total_return_pct  = Column(Float)
    transaction_costs = Column(Float)
    benchmark_return_pct = Column(Float)
    excess_return_pct = Column(Float)
    win_rate          = Column(Float)
    sharpe_ratio      = Column(Float)
    equity_curve_json = Column(JSON)   # [{date, portfolio_value}, ...]
    created_at        = Column(TIMESTAMP, server_default=func.now())


class ModelMetric(Base):
    """Training evaluation metrics for model comparison."""
    __tablename__ = "model_metrics"

    id                         = Column(Integer, primary_key=True, autoincrement=True)
    model_version              = Column(String(50), nullable=False, index=True)
    ticker                     = Column(String(20))   # NULL = all tickers combined
    accuracy                   = Column(Float)
    precision_score            = Column(Float)
    recall_score               = Column(Float)
    f1_score                   = Column(Float)
    roc_auc                    = Column(Float)
    dataset_start              = Column(Date)
    dataset_end                = Column(Date)
    test_start                 = Column(Date)
    test_end                   = Column(Date)
    train_samples              = Column(Integer)
    test_samples               = Column(Integer)
    majority_baseline_accuracy = Column(Float)
    simple_baseline_accuracy   = Column(Float)
    brier_score                = Column(Float)
    pr_auc                     = Column(Float)
    class_balance_json         = Column(JSON)
    calibration_metrics_json   = Column(JSON)
    feature_importances_json   = Column(JSON)
    validation_type            = Column(String(50), default="holdout")
    train_date                 = Column(TIMESTAMP, server_default=func.now())


class ExperimentRecord(Base):
    """Detailed experiment tracking log for quantitative research."""
    __tablename__ = "experiment_records"

    id                    = Column(Integer, primary_key=True, autoincrement=True)
    experiment_id         = Column(String(64), nullable=False, unique=True)
    model_name            = Column(String(50), nullable=False)
    model_version         = Column(String(50), nullable=False, index=True)
    ticker                = Column(String(20), index=True)
    validation_strategy   = Column(String(50), nullable=False)
    dataset_start         = Column(Date)
    dataset_end           = Column(Date)
    parameters_json       = Column(JSON)
    feature_names_json    = Column(JSON)
    metrics_json          = Column(JSON)
    baseline_metrics_json = Column(JSON)
    artifact_path         = Column(String(255))
    created_at            = Column(TIMESTAMP, server_default=func.now())
