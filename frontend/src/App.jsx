/**
 * App.jsx — Main Dashboard Application
 * ========================================
 * Root component that assembles all dashboard panels.
 * Manages the selected ticker state and passes it to children.
 */

import { useState } from 'react';
import Navbar from './components/Navbar';
import TickerSelector from './components/TickerSelector';
import PriceChart from './components/PriceChart';
import SentimentGauge from './components/SentimentGauge';
import ExplanationPanel from './components/ExplanationPanel';
import BacktestResults from './components/BacktestResults';
import MarketOverview from './components/MarketOverview';
import MarketNews from './components/MarketNews';
import PredictionHistory from './components/PredictionHistory';
import Watchlist from './components/Watchlist';
import RefreshControl from './components/RefreshControl';

export default function App() {
  const [selectedTicker, setSelectedTicker] = useState('RELIANCE.NS');

  return (
    <div>
      <Navbar />

      <main className="dashboard">
        <section id="overview" className="dashboard__section">
          <MarketOverview />
        </section>

        <section id="market-news" className="dashboard__section">
          <MarketNews />
        </section>

        <section id="analysis" className="dashboard__section">
          <div className="dashboard__header">
            <div>
              <h1 style={{
                fontSize: 'var(--font-size-2xl)',
                fontWeight: 700,
                color: 'var(--text-primary)',
                marginBottom: '0.25rem',
              }}>
                Stock Analysis
              </h1>
              <p style={{
                fontSize: 'var(--font-size-sm)',
                color: 'var(--text-muted)',
              }}>
                AI-powered trend prediction for Indian equities
              </p>
            </div>
            <TickerSelector
              selected={selectedTicker}
              onSelect={setSelectedTicker}
            />
          </div>

          <Watchlist selected={selectedTicker} onSelect={setSelectedTicker} />
          <RefreshControl />

          <div className="dashboard__grid dashboard__grid--full">
            <PriceChart ticker={selectedTicker} />
          </div>

          <div className="dashboard__grid dashboard__grid--full">
            <PredictionHistory ticker={selectedTicker} />
          </div>
        </section>

        <section id="sentiment" className="dashboard__section">
          <div className="dashboard__grid">
            <SentimentGauge ticker={selectedTicker} />
            <ExplanationPanel ticker={selectedTicker} />
          </div>
        </section>

        <section id="backtest" className="dashboard__section">
          <div className="dashboard__grid dashboard__grid--full">
            <BacktestResults ticker={selectedTicker} />
          </div>
        </section>

        {/* Footer */}
        <footer style={{
          textAlign: 'center',
          padding: '1.5rem',
          fontSize: '0.75rem',
          color: 'var(--text-muted)',
          borderTop: '1px solid var(--border-subtle)',
        }}>
          AI Trading Assistant — Final Year Project •
          Built with FastAPI, XGBoost, FinBERT & React
        </footer>
      </main>
    </div>
  );
}
