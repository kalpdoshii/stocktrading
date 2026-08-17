# Prompt for Google Antigravity

Copy the whole block below and paste it as your first task in Antigravity. It's written so the agent produces a task list + implementation plan first (for you to review) before writing any code, matching how Antigravity's Manager Surface expects work to be structured.

You can also split it phase by phase into separate agent tasks if you want to run things in parallel or review each phase before moving on — the phases are already broken out below for that.

---

```
ROLE
You are an expert full-stack + ML engineer helping me build a final-year
academic project called "AI Trading Assistant with Reasoning" — a system
that predicts stock trend direction using price data + news + social
sentiment, and explains each prediction in plain English using an LLM
reasoning layer, all shown on a live dashboard.

TECH STACK
- Python 3.11 backend, FastAPI
- Frontend: Streamlit (or React if you think it's cleaner — your call)
- Data: yfinance (price history), newsapi (headlines), praw (Reddit)
- Sentiment: FinBERT
- Prediction model: XGBoost baseline, optionally LSTM as a stretch goal
- Reasoning: LLM API call with a structured prompt template
- Storage: SQLite
- Backtesting: custom engine computing returns, win rate, Sharpe ratio

BEFORE WRITING ANY CODE
Produce a full task list and implementation plan covering: folder
structure, modules, data flow between them, and the SQLite schema.
Wait for my review and approval before starting implementation.

BUILD IN THESE PHASES (implementation plan → code → short walkthrough
of what was built and how to run/verify it, for each phase):

PHASE 1 — Data pipeline
- Script to pull historical OHLCV data via yfinance for a configurable
  list of tickers
- Script to pull news headlines per ticker via newsapi
- Script to pull Reddit posts/comments mentioning each ticker via praw
- Store all raw data in SQLite with a clean, documented schema
- Add a simple refresh script that can be re-run daily

PHASE 2 — Feature engineering + baseline model
- Compute technical indicators: moving averages, RSI, MACD, volatility
- Train an XGBoost model predicting next-day up/down movement using
  price + technical features only
- Evaluate accuracy, precision, recall — save as baseline metrics

PHASE 3 — Sentiment integration
- Run FinBERT over news headlines and Reddit text
- Generate a daily aggregated sentiment score per ticker
- Merge sentiment features with price features, retrain the model
- Save a comparison of metrics vs. the baseline (chart + numbers)

PHASE 4 — LLM reasoning layer
- Prompt template that takes: the prediction, top contributing
  features, and recent sentiment/news context
- Returns a plain-English explanation of the prediction
- Add caching so identical predictions don't re-trigger API calls

PHASE 5 — Backtesting
- Simulate trades using model signals over historical data
- Calculate returns, win rate, Sharpe ratio
- Output a results chart and summary stats table

PHASE 6 — Dashboard
- Ticker selector, price chart with predicted signal overlay
- Sentiment gauge/indicator
- A panel showing the LLM's plain-English explanation for the latest
  prediction
- Wire it to the backend so it reflects the latest data

PHASE 7 — Testing + polish
- Basic error handling for API failures (rate limits, missing data)
- README with setup instructions
- requirements.txt
- Clean up the UI for a simple, uncluttered look

CONSTRAINTS
- Keep everything runnable locally without paid infra beyond API keys
  I provide
- Comment code clearly, this needs to be explainable in a viva
- Don't over-engineer — this is a student project, not production SaaS
```
