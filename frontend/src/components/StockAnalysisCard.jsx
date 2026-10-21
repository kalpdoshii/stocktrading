/**
 * StockAnalysisCard.jsx — Module 3: Stock Analysis
 * ================================================
 * Matches Card 3 from the executive fintech design mockup.
 */

import React, { useState } from 'react';
import { useApi } from '../hooks/useApi';
import { getPriceData, getPrediction, getTickers } from '../services/api';
import {
  ResponsiveContainer,
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts';

const TIMEFRAMES = ['1D', '1W', '1M', '3M', '6M', '1Y', '5Y'];

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  const p = payload[0];
  return (
    <div className="custom-chart-tooltip">
      <div className="tooltip-date">{label}</div>
      <div className="tooltip-price">₹{Number(p.value).toFixed(2)}</div>
    </div>
  );
}

export default function StockAnalysisCard({ ticker, onSelectTicker, watchlist = [], onToggleWatchlist }) {
  const [activeTimeframe, setActiveTimeframe] = useState('6M');
  const [showIndicators, setShowIndicators] = useState(false);
  const [indicatorMode, setIndicatorMode] = useState('none'); // 'sma', 'ema', 'macd', 'none'

  const { data: priceData, loading: priceLoading } = useApi(getPriceData, ticker, 365);
  const { data: prediction } = useApi(getPrediction, ticker);
  const { data: tickersData } = useApi(getTickers);

  const rawCandles = priceData?.data || [];
  const latestCandle = rawCandles[rawCandles.length - 1] || {};
  const prevCandle = rawCandles[rawCandles.length - 2] || {};

  const currentPrice = latestCandle.close || 1243.20;
  const priceChange = latestCandle.close && prevCandle.close
    ? latestCandle.close - prevCandle.close
    : -38.25;
  const priceChangePct = latestCandle.close && prevCandle.close
    ? ((latestCandle.close - prevCandle.close) / prevCandle.close) * 100
    : -2.98;

  // Filter candle count based on timeframe
  const candleCount = activeTimeframe === '1D' ? 1 :
                      activeTimeframe === '1W' ? 7 :
                      activeTimeframe === '1M' ? 22 :
                      activeTimeframe === '3M' ? 66 :
                      activeTimeframe === '6M' ? 130 :
                      activeTimeframe === '1Y' ? 250 : 365;

  const chartSlice = rawCandles.slice(-candleCount);

  // Compute 52W high and low
  const closes = rawCandles.map(c => c.close).filter(Boolean);
  const high52W = closes.length ? Math.max(...closes) : 1608.90;
  const low52W = closes.length ? Math.min(...closes) : 1142.25;

  const chartData = chartSlice.map((d) => ({
    date: d.date,
    dateLabel: new Date(d.date).toLocaleDateString('en-US', { month: 'short' }),
    price: d.close,
    ema: d.ema_12 || d.close,
    sma: d.sma_20 || d.close,
  }));

  // Company Name lookup
  const companyName = tickersData?.tickers?.find((t) => t.ticker === ticker)?.name || 'Reliance Industries';
  const isInWatchlist = watchlist.includes(ticker);

  const isPositive = priceChange >= 0;

  return (
    <div className="module-card module-card--analysis" id="analysis">
      {/* Background Metallic Blue Bull Watermark */}
      <div className="bull-watermark-bg" />

      {/* Header */}
      <div className="module-card__header analysis-header">
        <div>
          <h2 className="module-card__title">Stock Analysis</h2>
          <p className="module-card__subtitle">AI-powered insights, technical indicators and predictions</p>
        </div>

        {/* Ticker Selector Dropdown */}
        <div className="stock-selector-wrap">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <select
            className="stock-select-input"
            value={ticker}
            onChange={(e) => onSelectTicker(e.target.value)}
          >
            {tickersData?.tickers?.map((t) => (
              <option key={t.ticker} value={t.ticker}>
                {t.name} ({t.ticker})
              </option>
            )) || (
              <option value="RELIANCE.NS">Reliance Industries (RELIANCE.NS)</option>
            )}
          </select>
        </div>
      </div>

      {/* Stock Identity Row */}
      <div className="stock-identity-bar">
        <div className="stock-identity-left">
          <div className="stock-gold-avatar">
            {companyName.charAt(0)}
          </div>
          <div className="stock-name-col">
            <h3 className="stock-full-name">{companyName}</h3>
            <span className="stock-ticker-code">{ticker}</span>
          </div>
        </div>

        <div className="stock-identity-center">
          <div className="stock-current-price">
            ₹{currentPrice.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
          <div className={`stock-price-change ${isPositive ? 'text-up' : 'text-down'}`}>
            {isPositive ? '+' : ''}{priceChange.toFixed(2)} ({isPositive ? '+' : ''}{priceChangePct.toFixed(2)}%)
          </div>
        </div>

        <div className="stock-identity-right">
          <button
            className={`btn-watchlist ${isInWatchlist ? 'btn-watchlist--active' : ''}`}
            onClick={() => onToggleWatchlist && onToggleWatchlist(ticker)}
          >
            {isInWatchlist ? '✓ In Watchlist' : '+ Add to Watchlist'}
          </button>
        </div>
      </div>

      {/* Timeframe & Indicators Row */}
      <div className="chart-controls-bar">
        <div className="timeframe-pills">
          {TIMEFRAMES.map((tf) => (
            <button
              key={tf}
              className={`timeframe-pill ${activeTimeframe === tf ? 'timeframe-pill--active' : ''}`}
              onClick={() => setActiveTimeframe(tf)}
            >
              {tf}
            </button>
          ))}
        </div>

        <div className="indicators-dropdown-wrap">
          <button
            className="btn-indicators"
            onClick={() => setShowIndicators(!showIndicators)}
          >
            <span>Indicators</span>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="6 9 12 15 18 9" />
            </svg>
          </button>
          {showIndicators && (
            <div className="indicators-menu">
              <button onClick={() => { setIndicatorMode('none'); setShowIndicators(false); }}>None</button>
              <button onClick={() => { setIndicatorMode('ema'); setShowIndicators(false); }}>EMA (12-day)</button>
              <button onClick={() => { setIndicatorMode('sma'); setShowIndicators(false); }}>SMA (20-day)</button>
            </div>
          )}
        </div>
      </div>

      {/* Main Interactive Candlestick / Area Chart */}
      <div className="analysis-chart-container">
        <ResponsiveContainer width="100%" height={380}>
          <ComposedChart data={chartData} margin={{ top: 15, right: 10, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="bullAreaGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#10b981" stopOpacity={0.25} />
                <stop offset="60%" stopColor="#10b981" stopOpacity={0.05} />
                <stop offset="100%" stopColor="#ef4444" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" vertical={false} />
            <XAxis
              dataKey="dateLabel"
              stroke="#64748b"
              fontSize={11}
              tickLine={false}
              axisLine={false}
              interval={Math.max(1, Math.floor(chartData.length / 7))}
            />
            <YAxis
              stroke="#64748b"
              fontSize={11}
              domain={['auto', 'auto']}
              tickLine={false}
              axisLine={false}
              tickFormatter={(v) => Math.round(v)}
            />
            <Tooltip content={<CustomTooltip />} />
            <Area
              type="monotone"
              dataKey="price"
              stroke="#10b981"
              strokeWidth={2}
              fill="url(#bullAreaGrad)"
            />
            {indicatorMode === 'ema' && (
              <Line type="monotone" dataKey="ema" stroke="#f59e0b" strokeWidth={1.5} dot={false} />
            )}
            {indicatorMode === 'sma' && (
              <Line type="monotone" dataKey="sma" stroke="#38bdf8" strokeWidth={1.5} dot={false} />
            )}
          </ComposedChart>
        </ResponsiveContainer>

        {/* Current price floating badge marker */}
        <div className="current-price-badge">
          ₹{currentPrice.toFixed(2)}
        </div>
      </div>

      {/* 6 Key Stats Grid */}
      <div className="stock-stats-grid">
        <div className="stock-stat-box">
          <div className="stat-box-title">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/></svg>
            Market Cap
          </div>
          <div className="stat-box-value">₹16.8L Cr</div>
        </div>

        <div className="stock-stat-box">
          <div className="stat-box-title">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
            P/E Ratio
          </div>
          <div className="stat-box-value">24.6</div>
        </div>

        <div className="stock-stat-box">
          <div className="stat-box-title text-up">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="18 15 12 9 6 15"/></svg>
            52W High
          </div>
          <div className="stat-box-value">₹{high52W.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</div>
        </div>

        <div className="stock-stat-box">
          <div className="stat-box-title text-down">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="6 9 12 15 18 9"/></svg>
            52W Low
          </div>
          <div className="stat-box-value">₹{low52W.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</div>
        </div>

        <div className="stock-stat-box">
          <div className="stat-box-title">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 20V10"/><path d="M18 20V4"/><path d="M6 20v-4"/></svg>
            Volume
          </div>
          <div className="stat-box-value">1.2 Cr</div>
        </div>

        <div className="stock-stat-box">
          <div className="stat-box-title">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><path d="m15 9-6 6"/><circle cx="9" cy="9" r="1"/><circle cx="15" cy="15" r="1"/></svg>
            Dividend Yield
          </div>
          <div className="stat-box-value">0.68%</div>
        </div>
      </div>
    </div>
  );
}
