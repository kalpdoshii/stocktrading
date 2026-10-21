/**
 * IndianMarketOverview.jsx — Module 1: Indian Market Overview
 * ==========================================================
 * Matches Card 1 from the executive fintech design mockup.
 */

import React from 'react';
import { useApi } from '../hooks/useApi';
import { getMarketOverview } from '../services/api';

function MiniSparkline({ positive = true }) {
  const points = positive
    ? '0,18 8,14 16,16 24,10 32,12 40,6 48,2'
    : '0,2 8,6 16,5 24,11 32,9 40,15 48,18';
  const color = positive ? '#10b981' : '#ef4444';

  return (
    <svg width="48" height="20" viewBox="0 0 48 20" fill="none">
      <polyline
        points={points}
        stroke={color}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function ProgressRing({ progress = 98 }) {
  const radius = 18;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (progress / 100) * circumference;

  return (
    <svg width="46" height="46" viewBox="0 0 46 46">
      <circle
        cx="23"
        cy="23"
        r={radius}
        stroke="rgba(255, 255, 255, 0.1)"
        strokeWidth="3.5"
        fill="transparent"
      />
      <circle
        cx="23"
        cy="23"
        r={radius}
        stroke="#38bdf8"
        strokeWidth="3.5"
        strokeDasharray={circumference}
        strokeDashoffset={strokeDashoffset}
        strokeLinecap="round"
        fill="transparent"
        transform="rotate(-90 23 23)"
      />
    </svg>
  );
}

const SECTOR_ICONS = {
  'Information Technology': (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
  ),
  'Construction Materials': (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="1" y="4" width="22" height="16" rx="2"/><line x1="1" y1="10" x2="23" y2="10"/></svg>
  ),
  'Telecommunications': (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M5 12.55a11 11 0 0 1 14.08 0"/><path d="M1.42 9a16 16 0 0 1 21.16 0"/><path d="M8.53 16.11a6 6 0 0 1 6.95 0"/><line x1="12" y1="20" x2="12.01" y2="20"/></svg>
  ),
  'Oil and Gas': (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 2v7c0 1.1.9 2 2 2h4a2 2 0 0 0 2-2V2"/><path d="M7 2v20"/><path d="M21 15V2v0a5 5 0 0 0-5 5v6c0 1.1.9 2 2 2h3Zm0 0v7"/></svg>
  ),
  'Healthcare': (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
  ),
  'Utilities': (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
  ),
  'Consumer Goods': (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"/><line x1="3" y1="6" x2="21" y2="6"/><path d="M16 10a4 4 0 0 1-8 0"/></svg>
  ),
};

export default function IndianMarketOverview({ onSelectTicker }) {
  const { data, loading } = useApi(getMarketOverview);

  const nifty = data?.nifty50 || { value: 22811.35, change_pct: -0.34 };
  const coverage = data?.coverage || { available: 49, configured: 50 };

  // Sample or API gainers
  const gainers = (data?.top_gainers?.length ? data.top_gainers.slice(0, 5) : [
    { ticker: 'WIPRO.NS', name: 'Wipro', price: 412.35, change_pct: 3.86 },
    { ticker: 'INFY.NS', name: 'Infosys', price: 1578.20, change_pct: 3.30 },
    { ticker: 'HCLTECH.NS', name: 'HCL Technologies', price: 1622.10, change_pct: 3.21 },
    { ticker: 'TECHM.NS', name: 'Tech Mahindra', price: 1452.35, change_pct: 3.13 },
    { ticker: 'TCS.NS', name: 'TCS', price: 3684.75, change_pct: 2.77 },
  ]);

  // Sample or API losers
  const losers = (data?.top_losers?.length ? data.top_losers.slice(0, 5) : [
    { ticker: 'BAJFINANCE.NS', name: 'Bajaj Finance', price: 7112.30, change_pct: -3.27 },
    { ticker: 'EICHERMOT.NS', name: 'Eicher Motors', price: 5438.65, change_pct: -2.43 },
    { ticker: 'TRENT.NS', name: 'Trent', price: 6102.15, change_pct: -2.41 },
    { ticker: 'MARUTI.NS', name: 'Maruti Suzuki', price: 11284.20, change_pct: -2.40 },
    { ticker: 'ADANIENT.NS', name: 'Adani Enterprises', price: 2815.40, change_pct: -2.37 },
  ]);

  // Sectors
  const sectors = (data?.sector_performance?.length ? data.sector_performance : [
    { sector: 'Information Technology', change_pct: 3.25 },
    { sector: 'Construction Materials', change_pct: 1.87 },
    { sector: 'Telecommunications', change_pct: 0.88 },
    { sector: 'Oil and Gas', change_pct: 0.43 },
    { sector: 'Healthcare', change_pct: -0.60 },
    { sector: 'Utilities', change_pct: -0.61 },
    { sector: 'Consumer Goods', change_pct: -0.66 },
  ]);

  return (
    <div className="module-card module-card--overview" id="overview">
      {/* Module Header */}
      <div className="module-card__header">
        <div>
          <h2 className="module-card__title">Indian Market Overview</h2>
          <p className="module-card__subtitle">Live view of NIFTY 50 and market performance</p>
        </div>
        <div className="module-card__live-indicator">
          <span className="live-pulse" />
          <span className="live-text">Live</span>
          <span className="live-date">21 Oct, 2026 03:30 PM</span>
        </div>
      </div>

      {/* Hero Skyline Banner */}
      <div className="overview-hero">
        <div className="overview-hero__bg" />
        <div className="overview-hero__widgets">
          {/* NIFTY 50 Widget */}
          <div className="overview-widget overview-widget--nifty">
            <div className="nifty-header">
              <span className="india-flag-badge">🇮🇳</span>
              <span className="nifty-name">NIFTY 50</span>
              <span className="nifty-live-pill">LIVE</span>
            </div>
            <div className="nifty-price">
              {nifty.value.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
            <div className="nifty-change-row">
              <span className={`nifty-change ${nifty.change_pct >= 0 ? 'text-up' : 'text-down'}`}>
                {nifty.change_pct >= 0 ? '+' : ''}-78.40 ({nifty.change_pct.toFixed(2)}%)
              </span>
              <MiniSparkline positive={nifty.change_pct >= 0} />
            </div>
          </div>

          {/* Price Coverage Widget */}
          <div className="overview-widget overview-widget--stat">
            <div className="stat-label">PRICE COVERAGE</div>
            <div className="stat-flex">
              <span className="stat-value">{coverage.available} / {coverage.configured}</span>
              <ProgressRing progress={Math.round((coverage.available / coverage.configured) * 100)} />
            </div>
          </div>

          {/* Stocks Available Widget */}
          <div className="overview-widget overview-widget--stat">
            <div className="stat-label">STOCKS AVAILABLE</div>
            <div className="stat-value-large">{coverage.configured}</div>
          </div>

          {/* Market Status Widget */}
          <div className="overview-widget overview-widget--stat">
            <div className="stat-label">MARKET STATUS</div>
            <div className="market-status-badge">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="#10b981" stroke="#10b981">
                <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" />
              </svg>
              <span>Open</span>
            </div>
          </div>
        </div>
      </div>

      {/* 3-Column Movers Section */}
      <div className="overview-columns">
        {/* Top 5 Gainers */}
        <div className="overview-col">
          <div className="overview-col__header text-up">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <line x1="7" y1="17" x2="17" y2="7" />
              <polyline points="7 7 17 7 17 17" />
            </svg>
            <span>Top 5 Gainers</span>
          </div>
          <div className="overview-list">
            {gainers.map((stock, i) => (
              <div
                key={stock.ticker}
                className="mover-row"
                onClick={() => onSelectTicker && onSelectTicker(stock.ticker)}
                title={`Click to analyze ${stock.name}`}
              >
                <span className="mover-rank">{i + 1}</span>
                <div className="mover-avatar">
                  {stock.name.charAt(0)}
                </div>
                <div className="mover-info">
                  <div className="mover-name">{stock.name}</div>
                  <div className="mover-price">₹{Number(stock.price).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</div>
                </div>
                <MiniSparkline positive={true} />
                <span className="mover-badge mover-badge--up">
                  +{Math.abs(stock.change_pct).toFixed(2)}%
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Top 5 Losers */}
        <div className="overview-col">
          <div className="overview-col__header text-down">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <line x1="7" y1="7" x2="17" y2="17" />
              <polyline points="17 7 17 17 7 17" />
            </svg>
            <span>Top 5 Losers</span>
          </div>
          <div className="overview-list">
            {losers.map((stock, i) => (
              <div
                key={stock.ticker}
                className="mover-row"
                onClick={() => onSelectTicker && onSelectTicker(stock.ticker)}
                title={`Click to analyze ${stock.name}`}
              >
                <span className="mover-rank">{i + 1}</span>
                <div className="mover-avatar mover-avatar--down">
                  {stock.name.charAt(0)}
                </div>
                <div className="mover-info">
                  <div className="mover-name">{stock.name}</div>
                  <div className="mover-price">₹{Number(stock.price).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</div>
                </div>
                <span className="mover-badge mover-badge--down">
                  -{Math.abs(stock.change_pct).toFixed(2)}%
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Sector Performance */}
        <div className="overview-col">
          <div className="overview-col__header text-cyan">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 20V10" />
              <path d="M18 20V4" />
              <path d="M6 20v-4" />
            </svg>
            <span>Sector Performance</span>
          </div>
          <div className="overview-list">
            {sectors.map((sec) => {
              const isPositive = sec.change_pct >= 0;
              return (
                <div key={sec.sector} className="sector-row">
                  <div className="sector-icon">
                    {SECTOR_ICONS[sec.sector] || (
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <circle cx="12" cy="12" r="10" />
                      </svg>
                    )}
                  </div>
                  <span className="sector-name">{sec.sector}</span>
                  <span className={`sector-change ${isPositive ? 'text-up' : 'text-down'}`}>
                    {isPositive ? '+' : ''}{sec.change_pct.toFixed(2)}%
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
