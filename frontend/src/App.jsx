/**
 * App.jsx — StockTrading Desktop Executive Platform
 * ==================================================
 * Desktop layout featuring a top Header Navbar with screen tab navigation,
 * where each screen block is dedicated to 1 full screen.
 */

import React, { useState } from 'react';
import { useApi } from './hooks/useApi';
import { getTickers } from './services/api';
import Navbar from './components/Navbar';
import IndianMarketOverview from './components/IndianMarketOverview';
import MarketNewsCard from './components/MarketNewsCard';
import StockAnalysisCard from './components/StockAnalysisCard';
import SentimentAnalysisCard from './components/SentimentAnalysisCard';
import BacktestResultsCard from './components/BacktestResultsCard';

export default function App() {
  const [activeTab, setActiveTab] = useState('overview');
  const [selectedTicker, setSelectedTicker] = useState('RELIANCE.NS');
  const [watchlist, setWatchlist] = useState(['RELIANCE.NS', 'TCS.NS', 'INFY.NS']);

  const { data: tickersData } = useApi(getTickers);
  const tickers = tickersData?.tickers || [];

  const toggleWatchlist = (ticker) => {
    setWatchlist((prev) =>
      prev.includes(ticker) ? prev.filter((t) => t !== ticker) : [...prev, ticker]
    );
  };

  const handleSelectTickerAndAnalyze = (ticker) => {
    setSelectedTicker(ticker);
    setActiveTab('analysis');
  };

  return (
    <div className="desktop-app-container">
      {/* Top Header Navbar */}
      <Navbar
        activeTab={activeTab}
        onSelectTab={setActiveTab}
      />

      {/* Main Screen Block (1 screen block contains 1 screen) */}
      <main className="desktop-main-viewport">
        {activeTab === 'overview' && (
          <div className="screen-block fade-in" key="overview">
            <IndianMarketOverview
              onSelectTicker={handleSelectTickerAndAnalyze}
            />
          </div>
        )}

        {activeTab === 'news' && (
          <div className="screen-block fade-in" key="news">
            <MarketNewsCard
              onSelectTicker={handleSelectTickerAndAnalyze}
            />
          </div>
        )}

        {activeTab === 'analysis' && (
          <div className="screen-block fade-in" key="analysis">
            <StockAnalysisCard
              ticker={selectedTicker}
              onSelectTicker={setSelectedTicker}
              watchlist={watchlist}
              onToggleWatchlist={toggleWatchlist}
            />
          </div>
        )}

        {activeTab === 'sentiment' && (
          <div className="screen-block fade-in" key="sentiment">
            <SentimentAnalysisCard
              ticker={selectedTicker}
              onSelectTicker={setSelectedTicker}
              tickers={tickers}
            />
          </div>
        )}

        {activeTab === 'backtest' && (
          <div className="screen-block fade-in" key="backtest">
            <BacktestResultsCard
              ticker={selectedTicker}
              onSelectTicker={setSelectedTicker}
              tickers={tickers}
            />
          </div>
        )}
      </main>
    </div>
  );
}
