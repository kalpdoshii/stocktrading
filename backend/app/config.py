"""
config.py — Application Settings
=================================
Loads all configuration from environment variables (.env file).
Central place for API keys, database URL, and ticker list.
"""

import os
from dotenv import load_dotenv

from app.stock_universe import INDIAN_TICKERS

# Load .env file from the backend directory
# (looks in current working dir and parent dirs)
load_dotenv()


# ---- MySQL Database ----
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "trading_user")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "trading_password")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "trading_assistant")

# SQLAlchemy connection string for MySQL via PyMySQL driver
DATABASE_URL = (
    f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}"
    f"@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"
)

# ---- Stock Tickers ----
# Comma-separated in .env, parsed into a list here
TICKERS = [
    t.strip()
    for t in os.getenv("TICKERS", ",".join(INDIAN_TICKERS)).split(",")
]

# ---- yfinance ----
PRICE_HISTORY_YEARS = int(os.getenv("PRICE_HISTORY_YEARS", "2"))

# ---- NewsAPI ----
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "").strip()

# ---- Reddit (PRAW) ----
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID", "").strip()
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "").strip()
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "TradingAssistant/1.0").strip()

# ---- LLM ----
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").strip()  # 'gemini' or 'openai'
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()

# ---- Reddit Subreddits to Search ----
SUBREDDITS = ["wallstreetbets", "stocks", "investing"]

# ---- Backtesting Defaults ----
STARTING_CAPITAL = 10_000.0

# Approximate NSE equity-delivery costs as decimal rates.
INDIAN_EQUITY_COSTS = {
    "brokerage_rate": 0.0003,
    "stt_rate": 0.001,
    "exchange_rate": 0.0000297,
    "gst_rate": 0.18,
    "stamp_duty_rate": 0.00015,
    "slippage_rate": 0.0005,
}

# ---- Automatic Indian Market Refresh ----
AUTO_REFRESH_ENABLED = os.getenv("AUTO_REFRESH_ENABLED", "false").lower() == "true"
AUTO_REFRESH_HOUR = int(os.getenv("AUTO_REFRESH_HOUR", "16"))
AUTO_REFRESH_MINUTE = int(os.getenv("AUTO_REFRESH_MINUTE", "0"))
AUTO_REFRESH_TIMEZONE = os.getenv("AUTO_REFRESH_TIMEZONE", "Asia/Kolkata")
