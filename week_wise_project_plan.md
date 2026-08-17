# AI Trading Assistant with Reasoning — 12 Week Plan

**Project:** Stock trend prediction + news/social sentiment + LLM explanation layer, shown on a live dashboard.

---

### Phase 1 — Foundation (Weeks 1–4)

**Week 1 — Scope & setup**
- Finalize stock universe (e.g. Nifty 50 subset or 8–10 popular US stocks)
- Set up GitHub repo, folder structure, virtual env, requirements.txt
- Quick literature/GitHub scan of similar projects so you know what to *not* copy

**Week 2 — Data collection scripts**
- `yfinance` script to pull historical OHLCV price data
- `newsapi` script to pull headlines per stock
- `praw` (Reddit API) script to pull posts/comments mentioning each stock
- Store everything in SQLite with a clean schema

**Week 3 — Cleaning & EDA**
- Handle missing values, align dates across price/news/reddit data
- EDA notebook: price trends, volume spikes, news frequency
- Engineer technical indicators: moving averages, RSI, MACD, volatility

**Week 4 — Baseline model**
- Train XGBoost (or simple LSTM) on price + technical indicators only
- Predict next-day up/down movement
- Log accuracy, precision, recall as your baseline benchmark

---

### Phase 2 — Sentiment + Reasoning (Weeks 5–8)

**Week 5 — Sentiment pipeline**
- Run FinBERT on news headlines and Reddit text
- Generate a daily aggregated sentiment score per stock

**Week 6 — Merge & retrain**
- Combine sentiment score with price/technical features
- Retrain model, compare metrics vs. baseline
- Save a comparison chart — this is a key result for your report

**Week 7 — LLM reasoning layer**
- Write prompt template: feed prediction + top features + recent sentiment/news into an LLM
- Output a plain-English explanation ("bullish because earnings beat + reddit mentions up 30%")
- Add basic caching so you're not re-calling the API for repeat predictions

**Week 8 — Backtesting**
- Build a simple backtest engine: simulate trades based on model signals
- Calculate returns, win rate, Sharpe ratio
- Output results as a chart + summary stats table

---

### Phase 3 — Dashboard & Wrap-up (Weeks 9–12)

**Week 9 — Frontend build**
- Streamlit (fast) or React + FastAPI (more "product" feel) — pick based on your comfort
- Build layout: stock selector, price chart, prediction signal

**Week 10 — Full integration**
- Wire dashboard to backend: live predictions, sentiment gauge, LLM explanation box
- Test full flow end to end multiple times, fix breakages

**Week 11 — Polish & extras**
- Bug fixes, UI cleanup
- If time allows: risk-level toggle, watchlist, portfolio suggestion feature

**Week 12 — Report & defense prep**
- Write report, build slides
- Record a demo video as backup in case live demo breaks during viva
- Practice explaining the reasoning layer clearly — it's your strongest selling point

---

**Tip:** don't fall behind on Week 6–7, that's the core "unique" part of the project (sentiment + reasoning). Everything after that is polish, so protect that window.
