-- ============================================================
-- AI Trading Assistant — MySQL Schema Initialization
-- ============================================================
-- This script runs automatically on first Docker Compose start.
-- It can also be run manually: mysql -u trading_user -p trading_assistant < init_db.sql
-- ============================================================

USE trading_assistant;

-- ----- Table 0: Stock reference metadata -----
CREATE TABLE IF NOT EXISTS stock_metadata (
    ticker      VARCHAR(20) PRIMARY KEY,
    name        VARCHAR(150) NOT NULL,
    sector      VARCHAR(100),
    index_name  VARCHAR(50),
    exchange    VARCHAR(10) NOT NULL DEFAULT 'NSE',
    currency    VARCHAR(3)  NOT NULL DEFAULT 'INR',
    is_active   TINYINT(1)  NOT NULL DEFAULT 1,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ----- Table 1: Historical OHLCV price data -----
CREATE TABLE IF NOT EXISTS price_data (
    id          INT AUTO_INCREMENT PRIMARY KEY,
        ticker      VARCHAR(20)    NOT NULL,
    date        DATE           NOT NULL,
    open        DECIMAL(12,4),
    high        DECIMAL(12,4),
    low         DECIMAL(12,4),
    close       DECIMAL(12,4),
    adj_close   DECIMAL(12,4),
    volume      BIGINT,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE KEY uq_ticker_date (ticker, date),
    INDEX idx_ticker (ticker),
    INDEX idx_date (date)
) ENGINE=InnoDB;

-- ----- Table 2: News headlines per ticker -----
CREATE TABLE IF NOT EXISTS news_headlines (
    id              INT AUTO_INCREMENT PRIMARY KEY,
        ticker          VARCHAR(20)    NOT NULL,
    headline        TEXT           NOT NULL,
    source          VARCHAR(100),
    url             VARCHAR(500),
    published_at    DATETIME,
    fetched_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_ticker (ticker),
    INDEX idx_published (published_at)
) ENGINE=InnoDB;

-- ----- Table 3: Reddit posts/comments mentioning tickers -----
CREATE TABLE IF NOT EXISTS reddit_posts (
    id              INT AUTO_INCREMENT PRIMARY KEY,
        ticker          VARCHAR(20)    NOT NULL,
    post_id         VARCHAR(20)    NOT NULL,
    subreddit       VARCHAR(50),
    title           TEXT,
    body            TEXT,
    score           INT DEFAULT 0,
    num_comments    INT DEFAULT 0,
    post_type       ENUM('post', 'comment') DEFAULT 'post',
    created_utc     DATETIME,
    fetched_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE KEY uq_post (post_id, ticker),
    INDEX idx_ticker (ticker),
    INDEX idx_created (created_utc)
) ENGINE=InnoDB;

-- ----- Table 4: Daily aggregated sentiment scores -----
CREATE TABLE IF NOT EXISTS sentiment_scores (
    id              INT AUTO_INCREMENT PRIMARY KEY,
        ticker          VARCHAR(20)    NOT NULL,
    date            DATE           NOT NULL,
    source_type     ENUM('news', 'reddit', 'combined') NOT NULL,
    positive_score  FLOAT,
    negative_score  FLOAT,
    neutral_score   FLOAT,
    compound_score  FLOAT,        -- single aggregated score (-1 to +1)
    sample_count    INT,          -- how many texts were scored
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE KEY uq_ticker_date_src (ticker, date, source_type),
    INDEX idx_ticker_date (ticker, date)
) ENGINE=InnoDB;

-- ----- Table 5: Model predictions -----
CREATE TABLE IF NOT EXISTS predictions (
    id              INT AUTO_INCREMENT PRIMARY KEY,
        ticker          VARCHAR(20)    NOT NULL,
    date            DATE           NOT NULL,
    model_version   VARCHAR(50)    NOT NULL,
    signal_dir      ENUM('UP', 'DOWN') NOT NULL,
    confidence      FLOAT,
    features_json   JSON,          -- snapshot of top contributing features
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE KEY uq_pred (ticker, date, model_version),
    INDEX idx_ticker_date (ticker, date)
) ENGINE=InnoDB;

-- ----- Table 6: LLM response cache -----
CREATE TABLE IF NOT EXISTS llm_cache (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    prompt_hash     CHAR(64)       NOT NULL,   -- SHA-256 hex digest
    prompt_text     TEXT,
    response_text   TEXT           NOT NULL,
    model_used      VARCHAR(50),
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE KEY uq_hash (prompt_hash)
) ENGINE=InnoDB;

-- ----- Table 7: Backtest results -----
CREATE TABLE IF NOT EXISTS backtest_results (
    id                INT AUTO_INCREMENT PRIMARY KEY,
        ticker            VARCHAR(20)    NOT NULL,
    model_version     VARCHAR(50)    NOT NULL,
    start_date        DATE,
    end_date          DATE,
    total_trades      INT,
    winning_trades    INT,
    losing_trades     INT,
    total_return_pct  FLOAT,
    transaction_costs FLOAT,
    benchmark_return_pct FLOAT,
    excess_return_pct FLOAT,
    win_rate          FLOAT,
    sharpe_ratio      FLOAT,
    equity_curve_json JSON,         -- array of {date, portfolio_value}
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_ticker_model (ticker, model_version)
) ENGINE=InnoDB;

-- ----- Table 8: Model training metrics -----
CREATE TABLE IF NOT EXISTS model_metrics (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    model_version   VARCHAR(50)    NOT NULL,
        ticker          VARCHAR(20),              -- NULL = all tickers combined
    accuracy        FLOAT,
    precision_score FLOAT,
    recall_score    FLOAT,
    f1_score        FLOAT,
    roc_auc         FLOAT,
    train_date      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_model (model_version)
) ENGINE=InnoDB;
