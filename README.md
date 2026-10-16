# AI Trading Assistant with Reasoning

A full-stack stock trend prediction system that combines **price data**, **news sentiment**, and **social media analysis** to predict next-day stock movements, then explains each prediction in plain English using an **LLM reasoning layer**.

Built as a final-year academic project (SGP).

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────┐
│                React Dashboard (Vite)            │
│  Price Chart │ Sentiment Gauge │ LLM Explanation │
└──────────────┬───────────────────────────────────┘
               │ REST API (JSON)
┌──────────────▼───────────────────────────────────┐
│              FastAPI Backend (Python)             │
│  Routers → ML Predict → Reasoning → Backtest     │
└──────────────┬───────────────────────────────────┘
               │
┌──────────────▼───────────────────────────────────┐
│                    MySQL 8.0                      │
│  price_data │ news │ reddit │ sentiment │ cache   │
└──────────────────────────────────────────────────┘
```

## ✨ Features

- **Data Pipeline**: Automated collection from Yahoo Finance, NewsAPI, and Reddit
- **Technical Analysis**: SMA, EMA, RSI, MACD, Bollinger Bands, volatility
- **XGBoost Models**: Baseline (price-only) and sentiment-augmented versions
- **FinBERT Sentiment**: NLP analysis of financial news and Reddit discussions
- **LLM Explanations**: Gemini-powered plain-English prediction reasoning
- **Backtesting Engine**: Simulated trading with Sharpe ratio, win rate, returns
- **Live Dashboard**: Dark-themed React UI with interactive charts

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **MySQL 8.0** (or Docker)

### 1. Clone and Setup

```bash
git clone <your-repo-url>
cd SGP
```

### 2. Start MySQL

**Option A — Docker (recommended):**
```bash
docker-compose up -d
```

**Option B — Local MySQL:**
```bash
# Create database and user
mysql -u root -p
CREATE DATABASE trading_assistant;
CREATE USER 'trading_user'@'localhost' IDENTIFIED BY 'trading_password';
GRANT ALL PRIVILEGES ON trading_assistant.* TO 'trading_user'@'localhost';
FLUSH PRIVILEGES;

# Run schema
mysql -u trading_user -p trading_assistant < backend/scripts/init_db.sql
```

### 3. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env.example .env
# Edit .env with your API keys (NewsAPI, Reddit, Gemini)
```

### 4. Run the Data Pipeline

```bash
# Initialize DB tables and fetch all data
python -m scripts.run_pipeline --init-db

# Or fetch individually:
python -m scripts.run_pipeline --prices-only
python -m scripts.run_pipeline --news-only
python -m scripts.run_pipeline --reddit-only
```

### 5. Train Models

```bash
# Train baseline model (price + technical features)
python -m scripts.train_model --mode baseline

# Train sentiment model (after running sentiment pipeline)
python -m scripts.train_model --mode sentiment

# Train both and compare
python -m scripts.train_model --mode both
```

### 6. Run Backtest

```bash
python -m scripts.run_backtest --ticker AAPL
python -m scripts.run_backtest --all    # all tickers
```

### 7. Start the Backend API

```bash
uvicorn app.main:app --reload --port 8000
```

API docs available at: http://localhost:8000/docs

### 8. Start the Frontend

```bash
cd ../frontend
npm install
npm run dev
```

Dashboard available at: http://localhost:5173

---

## 🔑 API Keys Required

| Service | Purpose | Get Key |
|---------|---------|---------|
| NewsAPI | Financial news headlines | [newsapi.org/register](https://newsapi.org/register) |
| Reddit (PRAW) | Social media posts | [reddit.com/prefs/apps](https://www.reddit.com/prefs/apps) |
| Google Gemini | LLM explanations | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) |

> **Note:** yfinance (price data) does NOT require an API key.

---

## 📁 Project Structure

```
SGP/
├── backend/
│   ├── app/
│   │   ├── data_pipeline/    # yfinance, NewsAPI, Reddit fetchers
│   │   ├── features/         # technical indicators, feature builder
│   │   ├── sentiment/        # FinBERT analyzer & aggregator
│   │   ├── ml/               # XGBoost training, prediction, evaluation
│   │   ├── reasoning/        # LLM prompt template, client, cache
│   │   ├── backtesting/      # trade simulation, performance metrics
│   │   └── routers/          # FastAPI API endpoints
│   ├── scripts/              # CLI entry points
│   ├── trained_models/       # saved .joblib files
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/       # React UI components
│   │   ├── hooks/            # Custom React hooks
│   │   ├── services/         # API client
│   │   └── App.jsx           # Main dashboard layout
│   └── package.json
└── docker-compose.yml
```

---

## 📊 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/tickers` | GET | List available tickers |
| `/api/price/{ticker}` | GET | OHLCV data + indicators |
| `/api/predict/{ticker}` | GET | Latest UP/DOWN prediction |
| `/api/sentiment/{ticker}` | GET | Sentiment scores |
| `/api/explain/{ticker}` | GET | LLM explanation |
| `/api/backtest/{ticker}` | GET | Backtest results |
| `/api/metrics/compare` | GET | Model comparison |

---

## 🧪 Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11, FastAPI |
| Frontend | React (Vite), Recharts |
| Database | MySQL 8.0 |
| ML Model | XGBoost |
| Sentiment | FinBERT (HuggingFace) |
| LLM | Google Gemini |
| Data | yfinance, NewsAPI, PRAW |

---

## ⚠️ Disclaimer

This is an academic project for educational purposes only. The predictions generated by this system should NOT be used for actual trading or investment decisions. Past performance does not guarantee future results.
